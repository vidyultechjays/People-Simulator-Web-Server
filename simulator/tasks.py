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
def aggregate_emotion_task(city_name, news_item_title, aggregate_emotion_id):
    """
    Detailed emotional aggregation across demographics
    """
    try:
        # Retrieve the AggregateEmotion object
        aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
        
        # Get all personas in the city
        personas = Persona.objects.filter(city=city_name)
        
        # Initialize demographic summary
        demographic_summary = {
            "age_categories": {
                "18-25": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "26-40": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "41-60": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "60+": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            },
            "income_categories": {
                "low": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "medium": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "high": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            },
            "religion_categories": {
                "hindu": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "muslim": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "christian": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
                "others": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            }
        }
        
        # Overall summary
        overall_summary = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "total": 0
        }
        
        # Emotion categorization
        emotion_categories = {
            "positive": {"joy", "optimism", "compassion"},
            "negative": {"sadness", "anger", "fear", "disgust", "anxiety", "outrage"},
            "neutral": {"surprise"}
        }
        
        # Process each persona
        for persona in personas:
            # Generate emotional response
            emotion, intensity, explanation = generate_emotional_response(persona, news_item_title)
            
            # Determine emotion category
            emotion_category = next(
                (cat for cat, emotions in emotion_categories.items() 
                 if emotion in emotions), 
                "neutral"
            )
            
            # Update overall summary
            overall_summary[emotion_category] += 1
            overall_summary["total"] += 1
            
            # Update age category summary
            age_category = persona.age_group
            demographic_summary["age_categories"][age_category][emotion_category] += 1
            demographic_summary["age_categories"][age_category]["total"] += 1
            
            # Update income category summary
            income_category = persona.income_level
            demographic_summary["income_categories"][income_category][emotion_category] += 1
            demographic_summary["income_categories"][income_category]["total"] += 1
            
            # Update religion category summary
            religion_category = persona.religion
            demographic_summary["religion_categories"][religion_category][emotion_category] += 1
            demographic_summary["religion_categories"][religion_category]["total"] += 1
        
        # Calculate percentages
        def calculate_percentages(category_dict):
            for category, data in category_dict.items():
                if data["total"] > 0:
                    data["positive_percentage"] = round((data["positive"] / data["total"]) * 100, 2)
                    data["negative_percentage"] = round((data["negative"] / data["total"]) * 100, 2)
                    data["neutral_percentage"] = round((data["neutral"] / data["total"]) * 100, 2)
        
        calculate_percentages(demographic_summary["age_categories"])
        calculate_percentages(demographic_summary["income_categories"])
        calculate_percentages(demographic_summary["religion_categories"])
        
        # Calculate overall percentages
        if overall_summary["total"] > 0:
            for key in ["positive", "negative", "neutral"]:
                overall_summary[f"{key}_percentage"] = round(
                    (overall_summary[key] / overall_summary["total"]) * 100, 2
                )
        
        # Update AggregateEmotion
        aggregate_emotion.summary = overall_summary
        aggregate_emotion.demographic_summary = demographic_summary
        aggregate_emotion.save()
        
        return "Aggregation completed successfully"
    
    except Exception as e:
        logger.error(f"Emotion aggregation failed: {str(e)}")
        return f"Aggregation failed: {str(e)}"
    
# @shared_task
# def aggregate_emotion_task(city_name, news_item_title):
#     """
#     Asynchronously aggregates emotional responses from personas in a given city 
#     to a specific news item and updates the corresponding AggregateEmotion object 
#     in the database with the calculated emotional summary.
#     """
#     try:
#         logger = logging.getLogger(__name__)
#         logger.info("Starting task for city: %s, news item: %s", city_name, news_item_title)
#         personas = Persona.objects.filter(city=city_name)

#         if not personas.exists():
#             return "No personas found"

#         emotion_categories = {
#             "positive": {"joy", "optimism", "compassion"},
#             "negative": {"sadness", "anger", "fear", "disgust", "anxiety", "outrage"},
#             "neutral": {"surprise"}
#         }

#         summary = {"positive": 0, "negative": 0, "neutral": 0}
#         total_responses = 0

#         for persona in personas:
#             emotion, intensity, explanation = generate_emotional_response(persona, news_item_title)

#             if emotion in emotion_categories["positive"]:
#                 summary["positive"] += 1
#             elif emotion in emotion_categories["negative"]:
#                 summary["negative"] += 1
#             elif emotion in emotion_categories["neutral"]:
#                 summary["neutral"] += 1

#             total_responses += 1

#         if total_responses > 0:
#             total = summary["positive"] + summary["negative"] + summary["neutral"]
#             for key in summary:
#                 summary[key] = round((summary[key] / total) * 100, 2)
#         try:
#             aggregate_emotion = AggregateEmotion.objects.get(
#                 city=city_name,
#                 news_item__title=news_item_title
#             )
#             logger.info("Found AggregateEmotion object: %s", aggregate_emotion)

#             aggregate_emotion.summary = summary
#             aggregate_emotion.save()
#             logger.info("Updated summary: %s", summary)

#             return "Summary aggregation completed"

#         except AggregateEmotion.DoesNotExist:
#             logger.error(
#                 "AggregateEmotion object not found for city: %s, news_item: %s", 
#                 city_name,
#                 news_item_title
#             )
#             return (
#                 f"Error: AggregateEmotion object not found for city: {city_name}, "
#                 f"news_item: {news_item_title}"
#             )
#     except Exception as e:
#         logger.exception("Error during task execution: %s", str(e))
#         return f"Error during task execution: {str(e)}"
