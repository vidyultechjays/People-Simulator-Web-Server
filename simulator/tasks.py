"""
This module contains the Celery tasks for processing emotional aggregation 
based on personas in a given city in response to a specific news item.
"""
import json
import logging
from celery import shared_task
from simulator.models import AggregateEmotion, Persona,Category
from simulator.utils.impact_assesment_helper import generate_emotional_response

logger = logging.getLogger(__name__)

@shared_task
def aggregate_emotion_task(city_name, news_item_title, aggregate_emotion_id):
    """
    Detailed emotional aggregation across demographics
    """
    try:
        aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)
        personas = Persona.objects.filter(city=city_name)
        
        # Dynamically fetch categories and subcategories filtered by city
        categories = Category.objects.filter(city=city_name).prefetch_related('subcategories')

        # Create a more flexible demographic summary initialization
        demographic_summary = {}
        for category in categories:
            demographic_summary[category.name] = {}
            for subcategory in category.subcategories.all():
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

            # Update subcategories for the persona
            subcategory_mappings = persona.subcategory_mappings.select_related('subcategory__category').all()
            
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

        # Save results to AggregateEmotion
        aggregate_emotion.summary = overall_summary
        aggregate_emotion.demographic_summary = demographic_summary
        aggregate_emotion.save()

        return "Aggregation completed successfully"

    except Exception as e:
        logger.error("Emotion aggregation failed: %s", str(e))
        return f"Aggregation failed: {str(e)}"

# @shared_task
# def aggregate_emotion_task(city_name, news_item_title, aggregate_emotion_id):
#     """
#     Detailed emotional aggregation across demographics
#     """
#     try:
#         aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)

#         personas = Persona.objects.filter(city=city_name)

#         demographic_summary = {
#             "age_categories": {
#                 "18-25": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "26-40": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "41-60": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "60+": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
#             },
#             "income_categories": {
#                 "low": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "medium": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "high": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
#             },
#             "religion_categories": {
#                 "hindu": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "muslim": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "christian": {"positive": 0, "negative": 0, "neutral": 0, "total": 0},
#                 "others": {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
#             }
#         }

#         overall_summary = {
#             "positive": 0,
#             "negative": 0,
#             "neutral": 0,
#             "total": 0
#         }

#         emotion_categories = {
#             "positive": {"joy", "optimism", "compassion"},
#             "negative": {"sadness", "anger", "fear", "disgust", "anxiety", "outrage"},
#             "neutral": {"surprise"}
#         }

#         for persona in personas:
#             # Generate emotional response
#             emotion, intensity, explanation = generate_emotional_response(persona, news_item_title)

#             emotion_category = next(
#                 (cat for cat, emotions in emotion_categories.items()
#                  if emotion in emotions),
#                 "neutral"
#             )

#             overall_summary[emotion_category] += 1
#             overall_summary["total"] += 1

#             age_category = persona.age_group
#             demographic_summary["age_categories"][age_category][emotion_category] += 1
#             demographic_summary["age_categories"][age_category]["total"] += 1

#             income_category = persona.income_level
#             demographic_summary["income_categories"][income_category][emotion_category] += 1
#             demographic_summary["income_categories"][income_category]["total"] += 1

#             religion_category = persona.religion
#             demographic_summary["religion_categories"][religion_category][emotion_category] += 1
#             demographic_summary["religion_categories"][religion_category]["total"] += 1

#         def calculate_percentages(category_dict):
#             for category, data in category_dict.items():
#                 if data["total"] > 0:
#                     data["positive_percentage"] = round((data["positive"] / data["total"]) * 100, 2)
#                     data["negative_percentage"] = round((data["negative"] / data["total"]) * 100, 2)
#                     data["neutral_percentage"] = round((data["neutral"] / data["total"]) * 100, 2)

#         calculate_percentages(demographic_summary["age_categories"])
#         calculate_percentages(demographic_summary["income_categories"])
#         calculate_percentages(demographic_summary["religion_categories"])

#         if overall_summary["total"] > 0:
#             for key in ["positive", "negative", "neutral"]:
#                 overall_summary[f"{key}_percentage"] = round(
#                     (overall_summary[key] / overall_summary["total"]) * 100, 2
#                 )

#         aggregate_emotion.summary = overall_summary
#         aggregate_emotion.demographic_summary = demographic_summary
#         aggregate_emotion.save()

#         return "Aggregation completed successfully"

#     except Exception as e:
#         logger.error("Emotion aggregation failed: %s", str(e))
#         return f"Aggregation failed: {str(e)}"
