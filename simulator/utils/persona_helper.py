"""
This module contains helper functions for managing personas, 
including generating demographic data,validating demographic percentages,
and generating random personality traits, occupations, and life details.
"""
import random

def generate_persona_traits():
    """Generate random personality traits for a persona."""
    return {
        "openness": round(random.uniform(0, 1), 2),
        "conscientiousness": round(random.uniform(0, 1), 2),
        "extraversion": round(random.uniform(0, 1), 2),
        "agreeableness": round(random.uniform(0, 1), 2),
        "neuroticism": round(random.uniform(0, 1), 2),
        "dominant_emotion": random.choice([
            "joy", "sadness", "anger", "fear", "disgust", "surprise", 
            "optimism", "anxiety", "compassion", "outrage"
        ]),
        "values": random.sample([
            "family", "career", "spirituality", "adventure", "security", 
            "knowledge", "freedom", "creativity", "health"
        ], k=2),
        "life_goals": random.sample([
            "financial security", "personal growth", "community service", 
            "fame", "adventure", "healthy living", "academic achievement", 
            "building relationships"
        ], k=2),
        "hobbies": random.sample([
            "reading", "traveling", "cooking", "sports", "gardening", 
            "painting", "photography", "writing", "music", "dancing"
        ], k=2),
        "daily_routine": {
            "morning": random.choice([
                "gym", "yoga", "jogging", "reading", "meditation", "breakfast with family"
            ]),
            "afternoon": random.choice([
                "work", "study", "relaxing", "networking", "volunteering"
            ]),
            "evening": random.choice([
                "family time", "watching TV", "reading", "exercise", 
                "attending social events", "hobbies"
            ])
        }
    }

