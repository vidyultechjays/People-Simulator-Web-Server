from simulator.models import LLMModelAndKey, PossibleUserResponses
from simulator.utils.ask_gemini import ask_gemini
from simulator.utils.ask_gpt import ask_gpt
from simulator.utils.ask_claude import ask_claude

def generate_emotional_response(persona, news_item):
    """
    Generates a response for a persona by selecting from possible user responses.
    
    Args:
        persona (Persona): The persona for which to generate a response
        news_item (NewsItem): The news item to respond to
    
    Returns:
        tuple: Selected user response, intensity, and explanation
    """
    active_model = LLMModelAndKey.objects.filter(active=True).first()

    personality_description = persona.personality_description or "No description provided."
    
    subcategories = persona.subcategory_mappings.select_related("subcategory").all()
    subcategories_list = [
        f"{mapping.subcategory.name} ({mapping.subcategory.category.name})"
        for mapping in subcategories
    ]

    possible_responses = PossibleUserResponses.objects.filter(news_item=news_item)
    
    persona_details = (
        f"Persona: Name {persona.name}, City {persona.city}, "
        f"Demographics: {', '.join(subcategories_list)}.\n"
        f"Personality Description: {personality_description}\n"
    )

    responses_list = "\n".join([
        f"{i+1}. {response.response_text}" 
        for i, response in enumerate(possible_responses)
    ])

    prompt = (
        f"{persona_details} "
        f"News: \"{news_item.title}\" "
        f"Possible Responses:\n{responses_list}\n"
        "Question: Based on the persona's background and the news, "
        "which response best reflects their potential reaction? "
        "Provide the number of the selected response, an intensity score (0-1), "
        "and a brief explanation. "
        "Provide the response in the following format:\n"
        "Selected Response Number: {number}\n"
        "Intensity: {intensity}\n"
        "Explanation: {explanation}"
    )

    # gemini_response = ask_gemini(prompt)
    if active_model.provider_name == 'anthropic':
        gemini_response = ask_claude(prompt,active_model.model_name)
    elif active_model.provider_name == 'openai':
        gemini_response=ask_gpt(prompt,active_model.model_name)
    elif active_model.provider_name == 'google':
        gemini_response=ask_gemini(prompt,active_model.model_name)
    else:
        raise ValueError(f"Unsupported provider: {active_model.provider_name}")

    # Extract response number, intensity, and explanation
    response_number = int(gemini_response.split("Selected Response Number:")[1].split("\n")[0].strip())
    intensity = float(gemini_response.split("Intensity:")[1].split("\n")[0].strip())
    explanation = gemini_response.split("Explanation:")[1].strip()

    selected_response = possible_responses[response_number - 1]

    return selected_response, intensity, explanation
