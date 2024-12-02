"""
This module contains the Celery tasks for processing emotional aggregation 
based on personas in a given city in response to a specific news item.
"""
import logging
from celery import shared_task
from simulator.models import AggregateEmotion, Persona
from simulator.utils.impact_assesment_helper import generate_emotional_response

logger = logging.getLogger(__name__)

@shared_task
def aggregate_emotion_task(city_name, news_item_title):
    """
    Asynchronously aggregates emotional responses from personas in a given city 
    to a specific news item and updates the corresponding AggregateEmotion object 
    in the database with the calculated emotional summary.
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("Starting task for city: %s, news item: %s", city_name, news_item_title)
        personas = Persona.objects.filter(city=city_name)

        if not personas.exists():
            return "No personas found"

        emotion_categories = {
            "positive": {"joy", "optimism", "compassion"},
            "negative": {"sadness", "anger", "fear", "disgust", "anxiety", "outrage"},
            "neutral": {"surprise"}
        }

        summary = {"positive": 0, "negative": 0, "neutral": 0}
        total_responses = 0

        for persona in personas:
            emotion, intensity, explanation = generate_emotional_response(persona, news_item_title)

            if emotion in emotion_categories["positive"]:
                summary["positive"] += 1
            elif emotion in emotion_categories["negative"]:
                summary["negative"] += 1
            elif emotion in emotion_categories["neutral"]:
                summary["neutral"] += 1

            total_responses += 1

        if total_responses > 0:
            total = summary["positive"] + summary["negative"] + summary["neutral"]
            for key in summary:
                summary[key] = round((summary[key] / total) * 100, 2)
        try:
            aggregate_emotion = AggregateEmotion.objects.get(
                city=city_name,
                news_item__title=news_item_title
            )
            logger.info("Found AggregateEmotion object: %s", aggregate_emotion)

            aggregate_emotion.summary = summary
            aggregate_emotion.save()
            logger.info("Updated summary: %s", summary)

            return "Summary aggregation completed"

        except AggregateEmotion.DoesNotExist:
            logger.error(
                "AggregateEmotion object not found for city: %s, news_item: %s", 
                city_name,
                news_item_title
            )
            return (
                f"Error: AggregateEmotion object not found for city: {city_name}, "
                f"news_item: {news_item_title}"
            )
    except Exception as e:
        logger.exception(f"Error during task execution: {str(e)}")
        return f"Error during task execution: {str(e)}"
