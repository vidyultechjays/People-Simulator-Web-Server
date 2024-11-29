"""
This module contains helper functions for managing personas, 
including generating demographic data,validating demographic percentages,
and generating random personality traits, occupations, and life details.
"""
import random

def extract_demographics(request):
    """
    Extracts and validates demographic data from a request.
    """
    return {
        "age_groups": {
            "18-25": int(request.POST.get("demographics[age_groups][18-25]")),
            "26-40": int(request.POST.get("demographics[age_groups][26-40]")),
            "41-60": int(request.POST.get("demographics[age_groups][41-60]")),
            "60+": int(request.POST.get("demographics[age_groups][60+]")),
        },
        "religions": {
            "hindu": int(request.POST.get("demographics[religions][hindu]")),
            "muslim": int(request.POST.get("demographics[religions][muslim]")),
            "christian": int(request.POST.get("demographics[religions][christian]")),
            "others": int(request.POST.get("demographics[religions][others]")),
        },
        "income_groups": {
            "low": int(request.POST.get("demographics[income_groups][low]")),
            "medium": int(request.POST.get("demographics[income_groups][medium]")),
            "high": int(request.POST.get("demographics[income_groups][high]")),
        },
    }

def validate_demographics(demographics):
    """Validate that demographic percentages sum to 100."""
    return all(sum(group.values()) == 100 for group in demographics.values())

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


def get_occupation_by_income(income_group):
    """
    Assigns an occupation based on the income group.
    """
    low_income_occupations = [
        'laborer', 'service worker', 'clerk', 'farmer',
        'delivery driver', 'cleaner', 'security guard',
        'factory worker', 'retail assistant', 'construction worker'
    ]
    medium_income_occupations = [
        'teacher', 'nurse', 'manager', 'technician',
        'engineer', 'salesperson', 'accountant',
        'software developer', 'real estate agent', 'project coordinator'
    ]
    high_income_occupations = [
        'doctor', 'lawyer', 'executive', 'entrepreneur',
        'researcher', 'investment banker', 'architect',
        'university professor', 'business consultant', 'pilot'
    ]

    if income_group == 'low':
        return random.choice(low_income_occupations)
    if income_group == 'medium':
        return random.choice(medium_income_occupations)
    if income_group == 'high':
        return random.choice(high_income_occupations)
    raise ValueError(f"Invalid income group: {income_group}")
    