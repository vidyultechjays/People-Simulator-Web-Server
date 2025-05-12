from venv import logger
from simulator.models import LLMModelAndKey, PossibleUserResponses, PromptModel, AggregateEmotion, OptimizedResponse, NewsItem, Persona, Category, SubCategory
from simulator.utils.ask_gemini import ask_gemini
from simulator.utils.ask_gpt import ask_gpt
from simulator.utils.ask_claude import ask_claude
from simulator.utils.ask_claude_tools import ask_claude_tools
import json
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
        f"id = {response.id}: {response.response_text}" 
        for response in possible_responses
    ])
    print(f"responses_list: {responses_list}")
    # Format the prompt template with the dynamic values
    try:
        prompt = prompt_template.prompt_template.format(
            persona_details=persona_details,
            news_title=news_item.title,
            responses_list=responses_list,
            version=prompt_template.version
        )
        prompt_tools = prompt_template.tools_content
    except KeyError as e:
        raise ValueError(f"Missing required placeholder in prompt template: {str(e)}")

    # Call the appropriate LLM based on the active model
    try:
        if active_model.provider_name == 'anthropic':
            llm_response = ask_claude_tools(prompt, active_model.model_name, prompt_tools)
        elif active_model.provider_name == 'openai':
            llm_response = ask_gpt(prompt, active_model.model_name)
        elif active_model.provider_name == 'google':
            llm_response = ask_gemini(prompt, active_model.model_name)
        else:
            raise ValueError(f"Unsupported provider: {active_model.provider_name}")
    except Exception as e:
        raise ValueError(f"LLM API error: {str(e)}")
    
    # print(f"llm_response: {llm_response}  :: end :: type: {type(llm_response)}")
    # Add strict response validation
    # if not all(keyword in llm_response for keyword in ['Selected Response Number:', 'Intensity:', 'Explanation:']):
    #     raise ValueError(f"LLM response missing required fields. Response: {llm_response}")

    try:
        # # Extract response number with more robust parsing
        # response_parts = llm_response.split("Selected Response Number:")
        # if len(response_parts) < 2:
        #     raise ValueError("Could not find 'Selected Response Number' in response")
            
        # number_str = response_parts[1].split("\n")[0].strip()
        # response_number = int(number_str)
        
        # # Validate response number
        # if response_number < 1 or response_number > len(possible_responses):
        #     raise ValueError(f"Response number {response_number} out of range (1-{len(possible_responses)})")

        # # Extract intensity with more robust parsing
        # intensity_parts = llm_response.split("Intensity:")
        # if len(intensity_parts) < 2:
        #     raise ValueError("Could not find 'Intensity' in response")
            
        # intensity_str = intensity_parts[1].split("\n")[0].strip()
        # intensity = float(intensity_str)
        
        # # Validate intensity
        # if not 0 <= intensity <= 1:
        #     raise ValueError(f"Intensity {intensity} out of range (0-1)")

        # # Extract explanation
        # explanation_parts = llm_response.split("Explanation:")
        # if len(explanation_parts) < 2:
        #     raise ValueError("Could not find 'Explanation' in response")
            
        # explanation = explanation_parts[1].strip()
        # if not explanation:
        #     raise ValueError("Empty explanation")

        # # Get the selected response
        # selected_response = possible_responses[response_number - 1]
        print(f"llm_response: selected_response_number: type: {type(llm_response['selected_response_number'])}")
        print(f"llm_response: intensity: type: {type(llm_response['intensity'])}")
        print(f"llm_response: explanation: type: {type(llm_response['explanation'])}")
        return llm_response["selected_response_number"], llm_response["intensity"], llm_response["explanation"]
        
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

def generate_optimal_response(city_name, news_item, demographic_focus):
    """
    Generates strategic recommendations to maximize satisfaction levels for a news item
    
    Args:
        city_name (str): The name of the city
        news_item_title (str): The title of the news item
    
    Returns:
        dict: Optimization results including strategic recommendations and metrics
    """
    try:
        
        # Get all personas for this city
        personas = Persona.objects.filter(city=city_name)
        
        # Get demographic breakdown for the city
        categories = Category.objects.filter(city=city_name)
        subcategories = SubCategory.objects.filter(city=city_name)
        
        # Fetch the active LLM model
        active_model = LLMModelAndKey.objects.filter(active=True).first()
        if not active_model:
            raise ValueError("No active LLM model found.")
        
        # Fetch the prompt template for optimization
        prompt_entry = PromptModel.objects.filter(task_name="generate_optimal_response").first()
        prompt_template = prompt_entry.prompt_template
        prompt_tools = prompt_entry.tools_content
        
        # Get current responses summary
        aggregate = AggregateEmotion.objects.filter(
            city=city_name, 
            news_item__title__icontains=news_item.title
        ).first()
        
        current_responses = aggregate.demographic_summary if aggregate else {}
        
        # Format demographic breakdown
        
        # demographic_focus is a list of subcategories that the user wants to focus on. eg demographic_focus: ['173', '174', '175', '176']
        demographic_breakdown = []
        print(f"demographich_focus : {demographic_focus}")
        print('demorgaphic _ breakdown below')
        for category in categories:
            # If demographic focus is specified, only include those subcategories
            if demographic_focus != [''] and demographic_focus and len(demographic_focus) > 0:
                subs = subcategories.filter(
                    category=category, 
                    id__in=demographic_focus
                )
            else:
                subs = subcategories.filter(category=category)
                
            if subs.exists():
                demographic_breakdown.append({
                    "category": category.name,
                    "subcategories": [
                        {"name": sub.name, "percentage": sub.percentage} 
                        for sub in subs
                    ]
                })
        print(f"demographic_breakdown: {demographic_breakdown}")
        # Prepare the prompt
        prompt = prompt_template.format(
            original_content=news_item.content,
            selected_demographic_breakdown="All" if demographic_focus == [''] else demographic_breakdown,
            current_responses=current_responses
        )
        
        # Send the prompt to the LLM
        if active_model.provider_name == 'anthropic':
            llm_response = ask_claude_tools(prompt, active_model.model_name, prompt_tools)
        elif active_model.provider_name == 'openai':
            llm_response = ask_gpt(prompt, active_model.model_name)
        elif active_model.provider_name == 'google':
            llm_response = ask_gemini(prompt, active_model.model_name)
        else:
            raise ValueError(f"Unsupported provider: {active_model.provider_name}")
        
        print(f"llm_response type: {type(llm_response)}  :: end")
        
        if isinstance(llm_response, dict) and len(llm_response) == 1 and "optimized_content" in llm_response:
            llm_response = llm_response["optimized_content"]
        if isinstance(llm_response, dict) and "recommendations" in llm_response and isinstance(llm_response["recommendations"], str):
            try:
                llm_response = json.loads(llm_response["recommendations"])
            except json.JSONDecodeError:
                pass
        llm_response = json.loads(llm_response)
        # Parse strategic recommendations
        optimization_metrics = {
            "original_sentiment_breakdown": current_responses,
        }
        
        # Create or update OptimizedResponse
        optimized_response, created = OptimizedResponse.objects.update_or_create(
            news_item=news_item,
            city=city_name,
            defaults={
                'original_content': news_item.content,
                'optimized_content': llm_response,
                'optimization_metrics': optimization_metrics,
                'demographic_focus': demographic_focus
            }
        )
        return {
            "optimized_content": json.loads(llm_response),
            "optimization_metrics": optimization_metrics,
            "success": True
        }
        
    except Exception as e:
        print(f"Error generating optimization recommendations: {e}")
        return {
            "success": False,
            "error": str(e)
        }