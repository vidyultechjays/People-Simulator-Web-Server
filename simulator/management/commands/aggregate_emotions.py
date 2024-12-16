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
    Persona,
    Category
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
            default=30,
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
    Existing emotion aggregation logic
    """
    try:
        logger.info("Starting aggregation for city: %s, news item: %s, id: %d", city_name, news_item_title, aggregate_emotion_id)
        aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
        personas = Persona.objects.filter(city=city_name)
        logger.info("Found %d personas in city: %s", personas.count(), city_name)

        categories = Category.objects.filter(city=city_name).prefetch_related('subcategories')
        logger.info("Found %d categories in city: %s", categories.count(), city_name)

        # Create a more flexible demographic summary initialization
        demographic_summary = {}
        for category in categories:
            demographic_summary[category.name] = {}
            for subcategory in category.subcategories.filter(city=city_name):  # Filter subcategories by city
                # Use lowercase for consistency
                demographic_summary[category.name][subcategory.name.lower()] = {
                    "positive": 0, 
                    "negative": 0, 
                    "neutral": 0, 
                    "total": 0
                }

        overall_summary = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "total": 0
        }

        emotion_categories = {
            "positive": {"joy", "optimism", "compassion"},
            "negative": {"sadness", "anger", "fear", "disgust", "anxiety", "outrage"},
            "neutral": {"surprise"}
        }

        for persona in personas:
            emotion, intensity, explanation = generate_emotional_response(persona, news_item_title)
            logger.info("Generated response for persona %d: emotion=%s, intensity=%s", persona.id, emotion, intensity)

            emotion_category = next(
                (cat for cat, emotions in emotion_categories.items() if emotion in emotions),
                "neutral"
            )

            overall_summary[emotion_category] += 1
            overall_summary["total"] += 1

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
                    demographic_summary[category_name][subcategory_name][emotion_category] += 1
                    demographic_summary[category_name][subcategory_name]["total"] += 1

        logger.info("Completed processing personas. Calculating percentages...")

        # Calculate percentages for demographic summary
        def calculate_demographic_percentages(category_dict):
            for subcategory, data in category_dict.items():
                if data["total"] > 0:
                    data["positive_percentage"] = round((data["positive"] / data["total"]) * 100, 2)
                    data["negative_percentage"] = round((data["negative"] / data["total"]) * 100, 2)
                    data["neutral_percentage"] = round((data["neutral"] / data["total"]) * 100, 2)

        for category_data in demographic_summary.values():
            calculate_demographic_percentages(category_data)

        def calculate_overall_percentages(summary):
            total = summary["total"]
            if total > 0:
                summary["positive_percentage"] = round((summary["positive"] / total) * 100, 2)
                summary["negative_percentage"] = round((summary["negative"] / total) * 100, 2)
                summary["neutral_percentage"] = round((summary["neutral"] / total) * 100, 2)
            else:
                summary["positive_percentage"] = 0
                summary["negative_percentage"] = 0
                summary["neutral_percentage"] = 0

        calculate_overall_percentages(overall_summary)

        aggregate_emotion.summary = overall_summary
        aggregate_emotion.demographic_summary = demographic_summary
        logger.info("Saving aggregate emotion for %s", aggregate_emotion.city)
        aggregate_emotion.save()

        logger.info("Aggregation completed successfully for city: %s", city_name)
        return "Aggregation completed successfully"

    except Exception as e:
        logger.error("Emotion aggregation failed: %s", str(e))
        try:
            aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
            aggregate_emotion.summary['status'] = 'failed'
            aggregate_emotion.summary['error'] = str(e)
            aggregate_emotion.save()
        except Exception as save_error:
            logger.error("Could not update aggregation status: %s", save_error)

        return f"Aggregation failed: {str(e)}"
