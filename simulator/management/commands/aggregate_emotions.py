"""
This script provides a management command to run emotion aggregation as 
a background process in a Django application. 
"""
import threading
import logging
import time
import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from simulator.models import (
    AggregateEmotion,
    EmotionalResponse,
    NewsItem,
    Persona,
    Category,
    PossibleUserResponses
)
from simulator.utils.impact_assesment_helper import generate_emotional_response

# Logging setup
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Command defining class for emotion aggregation"""
    help = 'Run emotion aggregation as a background process'

    def add_arguments(self, parser):
        # Optional arguments
        parser.add_argument(
            '--city', 
            type=str,
            help='Specify a city to process'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=15,
            help='Interval between processing cycles (in seconds)'
        )

    def handle(self, *args, **options):
        # Retrieve command options
        specified_city = options.get('city')
        interval = options.get('interval')

        def process_pending_aggregations():
            while True:
                try:
                    logger.info("Fetching pending aggregation requests...")
                    # Find pending aggregation requests
                    pending_query = AggregateEmotion.objects.filter(
                        summary__status='Processing'
                    )

                    # Filter by city if specified
                    if specified_city:
                        logger.info("Filtering aggregation requests for city: %s", specified_city)
                        pending_query = pending_query.filter(city=specified_city)

                    if not pending_query.exists():
                        logger.info("No pending aggregation requests found.")
                        time.sleep(interval)
                        continue

                    # Process each pending aggregation
                    for aggregate_emotion in pending_query:
                        logger.info("Processing aggregation for city: %s, news item: %s, id: %d",
                                    aggregate_emotion.city, aggregate_emotion.news_item.title, aggregate_emotion.id)
                        try:
                            # Call the existing emotion aggregation logic
                            aggregate_emotion_task(
                                aggregate_emotion.city,
                                aggregate_emotion.news_item.title,
                                aggregate_emotion.id
                            )
                            logger.info("Successfully processed aggregation for city: %s", aggregate_emotion.city)
                        except Exception as e:
                            logger.error("Error processing aggregation for %s: %s", aggregate_emotion.city, e)

                    # Sleep between processing cycles
                    time.sleep(interval)

                except Exception as e:
                    logger.error(f"Unexpected error in aggregation process: {e}")
                    time.sleep(interval)

        # Set up logging to write to a file in the project directory
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'emotion_aggregation.log')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        # Start the aggregation thread
        aggregation_thread = threading.Thread(
            target=process_pending_aggregations,
            daemon=True
        )
        aggregation_thread.start()

        # Keep the main thread running
        try:
            while aggregation_thread.is_alive():
                aggregation_thread.join(1)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS('Stopping emotion aggregation')
            )
def aggregate_emotion_task(city_name, news_item_title, aggregate_emotion_id):
    """
    Aggregates emotional responses with user response selection and demographic breakdown
    """
    try:
        logger.info("Starting aggregation for city: %s, news item: %s, id: %d", city_name, news_item_title, aggregate_emotion_id)
        
        # Fetch the specific objects
        aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
        news_item = NewsItem.objects.get(title=news_item_title)
        personas = Persona.objects.filter(city=city_name)
        possible_responses = PossibleUserResponses.objects.filter(news_item=news_item)
        categories = Category.objects.filter(city=city_name).prefetch_related('subcategories')

        logger.info("Found %d personas in city: %s", personas.count(), city_name)
        logger.info("Found %d possible responses", possible_responses.count())

        # Initialize demographic summary structure
        demographic_summary = {}
        for category in categories:
            demographic_summary[category.name] = {}
            for subcategory in category.subcategories.filter(city=city_name):
                # Use lowercase for consistency
                demographic_summary[category.name][subcategory.name.lower()] = {
                    response.id: {
                        "response_text": response.response_text,
                        "count": 0,
                        "percentage": 0.0
                    } 
                    for response in possible_responses
                }

        # Initialize response summary
        response_summary = {
            response.id: {
                "response_text": response.response_text, 
                "count": 0, 
                "percentage": 0.0
            } 
            for response in possible_responses
        }

        # Track total processed responses
        total_responses = 0

        # Process each persona
        for persona in personas:
            try:
                # Generate response for this persona
                selected_response, intensity, explanation = generate_emotional_response(persona, news_item)
                
                # Create EmotionalResponse
                emotional_response = EmotionalResponse.objects.create(
                    persona=persona,
                    news_item=news_item,
                    user_response=selected_response,
                    intensity=intensity,
                    explanation=explanation
                )

                # Update overall response summary
                response_summary[selected_response.id]['count'] += 1
                total_responses += 1

                # Update demographic summary
                # Get the persona's subcategories
                subcategory_mappings = persona.subcategory_mappings.select_related('subcategory__category').filter(
                    subcategory__city=city_name  
                )

                for mapping in subcategory_mappings:
                    subcategory = mapping.subcategory
                    category_name = subcategory.category.name
                    # Convert to lowercase for consistent matching
                    subcategory_name = subcategory.name.lower()

                    # Verify the structure exists before updating
                    if (category_name in demographic_summary and
                        subcategory_name in demographic_summary[category_name]):
                        demographic_mapping = demographic_summary[category_name][subcategory_name]
                        
                        # Increment count for this response in this demographic group
                        demographic_mapping[selected_response.id]['count'] += 1

            except Exception as persona_error:
                logger.error(f"Error processing persona {persona.id}: {persona_error}")

        # Calculate percentages for overall response summary
        for response_id, data in response_summary.items():
            if total_responses > 0:
                data['percentage'] = round((data['count'] / total_responses) * 100, 2)

        # Calculate percentages for demographic summary
        for category_name, categories in demographic_summary.items():
            for subcategory_name, responses in categories.items():
                subcategory_total = sum(response['count'] for response in responses.values())
                
                for response_id, response_data in responses.items():
                    if subcategory_total > 0:
                        response_data['percentage'] = round(
                            (response_data['count'] / subcategory_total) * 100, 
                            2
                        )

        # Update aggregate emotion
        aggregate_emotion.summary = {
            "status": "completed",
            "total_responses": total_responses,
            "response_summary": response_summary
        }
        aggregate_emotion.demographic_summary = demographic_summary
        aggregate_emotion.save()

        logger.info("Aggregation completed successfully for city: %s", city_name)
        return "Aggregation completed successfully"

    except Exception as e:
        logger.error("Emotion aggregation failed: %s", str(e))
        # Error handling
        try:
            aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
            aggregate_emotion.summary['status'] = 'failed'
            aggregate_emotion.summary['error'] = str(e)
            aggregate_emotion.save()
        except Exception as save_error:
            logger.error("Could not update aggregation status: %s", save_error)

        return f"Aggregation failed: {str(e)}"
 