"""
This script provides a management command to run emotion aggregation as 
a background process in a Django application. 
"""
import threading
import logging
import time
from django.core.management.base import BaseCommand
from simulator.models import (
    AggregateEmotion,
    Persona,
    Category
)
from simulator.utils.impact_assesment_helper import generate_emotional_response

# Logging setup
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Command defining class"""
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
                    # Find pending aggregation requests
                    pending_query = AggregateEmotion.objects.filter(
                        summary__status='Processing'
                    )

                    # Filter by city if specified
                    if specified_city:
                        pending_query = pending_query.filter(city=specified_city)

                    # Process each pending aggregation
                    for aggregate_emotion in pending_query:
                        try:
                            # Your existing emotion aggregation logic
                            aggregate_emotion_task(
                                aggregate_emotion.city,
                                aggregate_emotion.news_item.title,
                                aggregate_emotion.id
                            )
                        except Exception as e:
                            logger.error("Error processing aggregation for %s: %s", aggregate_emotion.city, e)

                    time.sleep(interval)

                except Exception as e:
                    logger.error(f"Unexpected error in aggregation process: {e}")
                    time.sleep(interval)

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
        aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
        personas = Persona.objects.filter(city=city_name)

        categories = Category.objects.filter(city=city_name).prefetch_related('subcategories')

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
            # Generate emotional response
            emotion, intensity, explanation = generate_emotional_response(persona, news_item_title)

            emotion_category = next(
                (cat for cat, emotions in emotion_categories.items() if emotion in emotions),
                "neutral"
            )

            overall_summary[emotion_category] += 1
            overall_summary["total"] += 1

            # Update subcategories for the persona (with city filtering)
            subcategory_mappings = persona.subcategory_mappings.select_related('subcategory__category').filter(
                subcategory__city=city_name  # Ensure subcategories are filtered by city
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
