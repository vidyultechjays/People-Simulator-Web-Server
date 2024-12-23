from venv import logger
from simulator.models import LLMModelAndKey, PossibleUserResponses, PromptModel
from simulator.utils.ask_gemini import ask_gemini
from simulator.utils.ask_gpt import ask_gpt
from simulator.utils.ask_claude import ask_claude

# def generate_emotional_response(persona, news_item):
#     """
#     Generates a response for a persona by selecting from possible user responses.
    
#     Args:
#         persona (Persona): The persona for which to generate a response
#         news_item (NewsItem): The news item to respond to
    
#     Returns:
#         tuple: Selected user response, intensity, and explanation
#     """
#     active_model = LLMModelAndKey.objects.filter(active=True).first()

#     personality_description = persona.personality_description or "No description provided."
    
#     subcategories = persona.subcategory_mappings.select_related("subcategory").all()
#     subcategories_list = [
#         f"{mapping.subcategory.name} ({mapping.subcategory.category.name})"
#         for mapping in subcategories
#     ]

#     possible_responses = PossibleUserResponses.objects.filter(news_item=news_item)
    
#     persona_details = (
#         f"Persona: Name {persona.name}, City {persona.city}, "
#         f"Demographics: {', '.join(subcategories_list)}.\n"
#         f"Personality Description: {personality_description}\n"
#     )

#     responses_list = "\n".join([
#         f"{i+1}. {response.response_text}" 
#         for i, response in enumerate(possible_responses)
#     ])

#     prompt = (
#         f"{persona_details} "
#         f"News: \"{news_item.title}\" "
#         f"Possible Responses:\n{responses_list}\n"
#         "Question: Based on the persona's background and the news, "
#         "which response best reflects their potential reaction? "
#         "Provide the number of the selected response, an intensity score (0-1), "
#         "and a brief explanation. "
#         "Provide the response in the following format:\n"
#         "Selected Response Number: {number}\n"
#         "Intensity: {intensity}\n"
#         "Explanation: {explanation}"
#     )

#     # gemini_response = ask_gemini(prompt)
#     if active_model.provider_name == 'anthropic':
#         gemini_response = ask_claude(prompt,active_model.model_name)
#     elif active_model.provider_name == 'openai':
#         gemini_response=ask_gpt(prompt,active_model.model_name)
#     elif active_model.provider_name == 'google':
#         gemini_response=ask_gemini(prompt,active_model.model_name)
#     else:
#         raise ValueError(f"Unsupported provider: {active_model.provider_name}")

#     # Extract response number, intensity, and explanation
#     response_number = int(gemini_response.split("Selected Response Number:")[1].split("\n")[0].strip())
#     intensity = float(gemini_response.split("Intensity:")[1].split("\n")[0].strip())
#     explanation = gemini_response.split("Explanation:")[1].strip()

#     selected_response = possible_responses[response_number - 1]

#     return selected_response, intensity, explanation

def generate_emotional_response(persona, news_item):
    """
    Generates a response for a persona by selecting from possible user responses.
    Includes improved error handling and response parsing.
    """
    # Get the active LLM model
    active_model = LLMModelAndKey.objects.filter(active=True).first()
    if not active_model:
        raise ValueError("No active LLM model found")

    try:
        # Get the prompt template
        prompt_template = PromptModel.objects.get(task_name='generate_user_response')
    except PromptModel.DoesNotExist:
        raise ValueError("No prompt template found for generate_user_response task")

    # Prepare persona details
    personality_description = persona.personality_description or "No description provided."
    subcategories = persona.subcategory_mappings.select_related("subcategory").all()
    subcategories_list = [
        f"{mapping.subcategory.name} ({mapping.subcategory.category.name})"
        for mapping in subcategories
    ]
    
    persona_details = (
        f"Persona: Name {persona.name}, City {persona.city}, "
        f"Demographics: {', '.join(subcategories_list)}.\n"
        f"Personality Description: {personality_description}\n"
    )
    
    # Get possible responses
    possible_responses = PossibleUserResponses.objects.filter(news_item=news_item)
    if not possible_responses:
        raise ValueError(f"No possible responses found for news item: {news_item.id}")
        
    responses_list = "\n".join([
        f"{i+1}. {response.response_text}" 
        for i, response in enumerate(possible_responses)
    ])
    
    # Format the prompt template with the dynamic values
    try:
        prompt = prompt_template.prompt_template.format(
            persona_details=persona_details,
            news_title=news_item.title,
            responses_list=responses_list,
            version=prompt_template.version
        )
    except KeyError as e:
        raise ValueError(f"Missing required placeholder in prompt template: {str(e)}")

    # Call the appropriate LLM based on the active model
    try:
        if active_model.provider_name == 'anthropic':
            llm_response = ask_claude(prompt, active_model.model_name)
        elif active_model.provider_name == 'openai':
            llm_response = ask_gpt(prompt, active_model.model_name)
        elif active_model.provider_name == 'google':
            llm_response = ask_gemini(prompt, active_model.model_name)
        else:
            raise ValueError(f"Unsupported provider: {active_model.provider_name}")
    except Exception as e:
        raise ValueError(f"LLM API error: {str(e)}")
    
    print(llm_response)

    # Add strict response validation
    if not all(keyword in llm_response for keyword in ['Selected Response Number:', 'Intensity:', 'Explanation:']):
        raise ValueError(f"LLM response missing required fields. Response: {llm_response}")

    try:
        # Extract response number with more robust parsing
        response_parts = llm_response.split("Selected Response Number:")
        if len(response_parts) < 2:
            raise ValueError("Could not find 'Selected Response Number' in response")
            
        number_str = response_parts[1].split("\n")[0].strip()
        response_number = int(number_str)
        
        # Validate response number
        if response_number < 1 or response_number > len(possible_responses):
            raise ValueError(f"Response number {response_number} out of range (1-{len(possible_responses)})")

        # Extract intensity with more robust parsing
        intensity_parts = llm_response.split("Intensity:")
        if len(intensity_parts) < 2:
            raise ValueError("Could not find 'Intensity' in response")
            
        intensity_str = intensity_parts[1].split("\n")[0].strip()
        intensity = float(intensity_str)
        
        # Validate intensity
        if not 0 <= intensity <= 1:
            raise ValueError(f"Intensity {intensity} out of range (0-1)")

        # Extract explanation
        explanation_parts = llm_response.split("Explanation:")
        if len(explanation_parts) < 2:
            raise ValueError("Could not find 'Explanation' in response")
            
        explanation = explanation_parts[1].strip()
        if not explanation:
            raise ValueError("Empty explanation")

        # Get the selected response
        selected_response = possible_responses[response_number - 1]
        
        return selected_response, intensity, explanation
        
    except (IndexError, ValueError) as e:
        logger.error(f"Error processing persona {persona.id}: {str(e)}\nFull response: {llm_response}")
        raise ValueError(f"Failed to parse LLM response for persona {persona.id}: {str(e)}")
# def generate_emotional_response(persona, news_item):
#     """
#     Generates a response for a persona by selecting from possible user responses.
    
#     Args:
#         persona (Persona): The persona for which to generate a response
#         news_item (NewsItem): The news item to respond to
    
#     Returns:
#         tuple: Selected user response, intensity, and explanation
#     """
#     try:
#         # Fetch the active LLM model
#         active_model = LLMModelAndKey.objects.filter(active=True).first()
#         if not active_model:
#             raise ValueError("No active LLM model found.")
        
#         # Fetch the prompt template for the task
#         prompt_entry = PromptModel.objects.filter(task_name="generate_user_response").first()
#         if not prompt_entry:
#             raise ValueError("No prompt template found for 'generate_user_response' task.")

#         # Retrieve the prompt template and version
#         prompt_template = prompt_entry.prompt_template
#         version = prompt_entry.version

#         # Persona details and demographic information
#         personality_description = persona.personality_description or "No description provided."
#         subcategories = persona.subcategory_mappings.select_related("subcategory").all()
#         subcategories_list = [
#             f"{mapping.subcategory.name} ({mapping.subcategory.category.name})"
#             for mapping in subcategories
#         ]
#         persona_details = (
#             f"Persona: Name {persona.name}, City {persona.city}, "
#             f"Demographics: {', '.join(subcategories_list)}.\n"
#             f"Personality Description: {personality_description}\n"
#         )

#         # Possible user responses
#         possible_responses = PossibleUserResponses.objects.filter(news_item=news_item)
#         if not possible_responses.exists():
#             raise ValueError("No possible user responses found for the given news item.")
        
#         responses_list = "\n".join([
#             f"{i+1}. {response.response_text}" 
#             for i, response in enumerate(possible_responses)
#         ])

#         # Format the prompt using the prompt template
#         prompt = prompt_template.format(
#             version=version,  # Pass the version to adjust response length
#             persona_details=persona_details,
#             news_title=news_item.title,
#             responses_list=responses_list
#         )

#         # Send the prompt to the active LLM
#         if active_model.provider_name == 'anthropic':
#             llm_response = ask_claude(prompt, active_model.model_name)
#         elif active_model.provider_name == 'openai':
#             llm_response = ask_gpt(prompt, active_model.model_name)
#         elif active_model.provider_name == 'google':
#             llm_response = ask_gemini(prompt, active_model.model_name)
#         else:
#             raise ValueError(f"Unsupported provider: {active_model.provider_name}")

#         # Parse the LLM's response to extract the details
#         response_number = int(llm_response.split("Selected Response Number:")[1].split("\n")[0].strip())
#         intensity = float(llm_response.split("Intensity:")[1].split("\n")[0].strip())
#         explanation = llm_response.split("Explanation:")[1].strip()

#         selected_response = possible_responses[response_number - 1]

#         return selected_response, intensity, explanation

#     except Exception as e:
#         print(f"Error generating emotional response: {e}")
#         return None, 0, "Error in generating response."
