"""
This module contains utility functions related to the assessment of emotional responses
for personas based on news content. It includes functions to generate an emotional response
using an external service (e.g., Gemini API), process the responses, and handle related data.
"""
from .ask_gemini import ask_gemini

def generate_emotional_response(persona, news_content):
    
    """
    Generates an emotional response for a persona based on news content using Gemini.
    Now includes dynamic categories and subcategories.
    """
    # Fetch the personality traits
    traits = persona.personality_traits or {}
    values = traits.get("values", [])
    hobbies = traits.get("hobbies", [])
    dominant_emotion = traits.get("dominant_emotion", "neutral")
    openness = traits.get("openness", 0.5)
    neuroticism = traits.get("neuroticism", 0.5)
    extraversion = traits.get("extraversion", 0.5)
    agreeableness = traits.get("agreeableness", 0.5)
    conscientiousness = traits.get("conscientiousness", 0.5)
    life_goals = traits.get("life_goals", [])
    daily_routine = traits.get("daily_routine", {})

    # Fetch the associated subcategories dynamically
    subcategories = persona.subcategory_mappings.select_related("subcategory").all()
    subcategories_list = [
        f"{mapping.subcategory.name} ({mapping.subcategory.category.name})"
        for mapping in subcategories
    ]

    # Prepare persona details string
    persona_details = (
        f"Persona: Name {persona.name}, City {persona.city}, "
        f"Demographics: {', '.join(subcategories_list)}.\n"
        f"Personality Traits: Openness {openness}, Conscientiousness {conscientiousness}, "
        f"Extraversion {extraversion}, Agreeableness {agreeableness}, Neuroticism {neuroticism}.\n"
        f"Values: {', '.join(values)}.\n"
        f"Life Goals: {', '.join(life_goals)}.\n"
        f"Hobbies: {', '.join(hobbies)}.\n"
        f"Daily Routine: Morning - {daily_routine.get('morning', 'N/A')}, "
        f"Afternoon - {daily_routine.get('afternoon', 'N/A')}, "
        f"Evening - {daily_routine.get('evening', 'N/A')}.\n"
        f"Dominant Emotion: {dominant_emotion}.\n"
    )

    # Construct the prompt
    prompt = (
        f"{persona_details} "
        f"News: \"{news_content}\" "
        "Question: How does this news impact the persona emotionally? "
        "Please provide an emotion that must be one of the following: "
        "joy, sadness, anger, fear, disgust, surprise, optimism, anxiety, compassion, outrage. "
        "Also, provide an intensity score for the emotion on a scale from 0 to 1, "
        "Explain briefly, in one line, without any newlines or paragraph breaks. "
        "Provide the response in the following format:\n"
        "Person: {persona_name}\nEmotion: {emotion}\nIntensity: {intensity}\nExplanation: {explanation}"
    )

    # Call Gemini with the generated prompt
    gemini_response = ask_gemini(prompt)

    # Extract emotion, intensity, and explanation from the response
    emotion = None
    intensity = None
    explanation = None
    emotion_choices = [
        'joy', 'sadness', 'anger', 'fear', 'disgust', 'surprise',
        'optimism', 'anxiety', 'compassion', 'outrage'
    ]
    try:
        if "Emotion:" in gemini_response and "Explanation:" in gemini_response:
            emotion_line = gemini_response.split("Emotion:")[1].split("\n")[0].strip()
            intensity_line = gemini_response.split("Intensity:")[1].split("\n")[0].strip()
            explanation_line = gemini_response.split("Explanation:")[1].strip()

            if emotion_line.lower() in emotion_choices:
                emotion = emotion_line.lower()
            else:
                emotion = "unknown"

            intensity = float(intensity_line)
            explanation = explanation_line
    except (IndexError, ValueError):
        pass

    return emotion, intensity, explanation


# def generate_emotional_response(persona, news_content):
#     """
#     Generates an emotional response for a persona based on news content using Gemini.
#     """
#     traits = persona.personality_traits or {}
#     values = traits.get("values", [])
#     hobbies = traits.get("hobbies", [])
#     dominant_emotion = traits.get("dominant_emotion", "neutral")
#     openness = traits.get("openness", 0.5)
#     neuroticism = traits.get("neuroticism", 0.5)
#     extraversion = traits.get("extraversion", 0.5)
#     agreeableness = traits.get("agreeableness", 0.5)
#     conscientiousness = traits.get("conscientiousness", 0.5)
#     life_goals = traits.get("life_goals", [])
#     daily_routine = traits.get("daily_routine", {})

#     persona_details = (
#         f"Persona: Name {persona.name}, Age {persona.age_group}, Income {persona.income_level}, "
#         f"Religion {persona.religion}, Occupation {persona.occupation}.\n"
#         f"Personality Traits: Openness {openness}, Conscientiousness {conscientiousness}, "
#         f"Extraversion {extraversion}, Agreeableness {agreeableness}, Neuroticism {neuroticism}.\n"
#         f"Values: {', '.join(values)}.\n"
#         f"Life Goals: {', '.join(life_goals)}.\n"
#         f"Hobbies: {', '.join(hobbies)}.\n"
#         f"Daily Routine: Morning - {daily_routine.get('morning', 'N/A')}, "
#         f"Afternoon - {daily_routine.get('afternoon', 'N/A')}, "
#         f"Evening - {daily_routine.get('evening', 'N/A')}.\n"
#         f"Dominant Emotion: {dominant_emotion}.\n"
#     )

#     prompt = (
#         f"{persona_details} "
#         f"News: \"{news_content}\" "
#         "Question: How does this news impact the persona emotionally? "
#         "Please provide an emotion that must be one of the following: "
#         "joy, sadness, anger, fear, disgust, surprise, optimism, anxiety, compassion, outrage. "
#         "Also, provide an intensity score for the emotion on a scale from 0 to 1, "
#         "Explain briefly, in one line, without any newlines or paragraph breaks. "
#         "Provide the response in the following format:\n"
#         "Person: {persona_name}\nEmotion: {emotion}\nIntensity: {intensity}\nExplanation: {explanation}"
#     )

#     gemini_response = ask_gemini(prompt)

#     emotion = None
#     intensity = None
#     explanation = None
#     emotion_choices = [
#         'joy', 'sadness', 'anger', 'fear', 'disgust', 'surprise',
#         'optimism', 'anxiety', 'compassion', 'outrage'
#     ]
#     try:
#         if "Emotion:" in gemini_response and "Explanation:" in gemini_response:
#             emotion_line = gemini_response.split("Emotion:")[1].split("\n")[0].strip()
#             intensity_line = gemini_response.split("Intensity:")[1].split("\n")[0].strip()
#             explanation_line = gemini_response.split("Explanation:")[1].strip()

#             if emotion_line.lower() in emotion_choices:
#                 emotion = emotion_line.lower()
#             else:
#                 emotion = "unknown"

#             intensity = float(intensity_line)
#             explanation = explanation_line
#     except IndexError:
#         pass

#     return emotion, intensity, explanation
