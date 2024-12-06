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
        aggregate_emotion = AggregateEmotion.objects.get(id=aggregate_emotion_id)

        personas = Persona.objects.filter(city=city_name)

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
                (cat for cat, emotions in emotion_categories.items()
                 if emotion in emotions),
                "neutral"
            )

            overall_summary[emotion_category] += 1
            overall_summary["total"] += 1

            age_category = persona.age_group
            demographic_summary["age_categories"][age_category][emotion_category] += 1
            demographic_summary["age_categories"][age_category]["total"] += 1

            income_category = persona.income_level
            demographic_summary["income_categories"][income_category][emotion_category] += 1
            demographic_summary["income_categories"][income_category]["total"] += 1

            religion_category = persona.religion
            demographic_summary["religion_categories"][religion_category][emotion_category] += 1
            demographic_summary["religion_categories"][religion_category]["total"] += 1

        def calculate_percentages(category_dict):
            for category, data in category_dict.items():
                if data["total"] > 0:
                    data["positive_percentage"] = round((data["positive"] / data["total"]) * 100, 2)
                    data["negative_percentage"] = round((data["negative"] / data["total"]) * 100, 2)
                    data["neutral_percentage"] = round((data["neutral"] / data["total"]) * 100, 2)

        calculate_percentages(demographic_summary["age_categories"])
        calculate_percentages(demographic_summary["income_categories"])
        calculate_percentages(demographic_summary["religion_categories"])

        if overall_summary["total"] > 0:
            for key in ["positive", "negative", "neutral"]:
                overall_summary[f"{key}_percentage"] = round(
                    (overall_summary[key] / overall_summary["total"]) * 100, 2
                )

        aggregate_emotion.summary = overall_summary
        aggregate_emotion.demographic_summary = demographic_summary
        aggregate_emotion.save()

        return "Aggregation completed successfully"

    except Exception as e:
        logger.error("Emotion aggregation failed: %s", str(e))
        return f"Aggregation failed: {str(e)}"
