import google.generativeai as genai
from django.conf import settings
from simulator.models import LLMModelAndKey

genai.configure(api_key=settings.GEMINI_API_KEY)

def ask_gemini(prompt,model_name):
    """Calls the Gemini LLM and returns the response."""
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        print(f"Gemini response :{response}")
        if response and hasattr(response, 'text'):
            return response.text  
        elif response and hasattr(response, 'candidates'):
            return response.candidates[0].get('output', 'No output found')
        else:
            return "No response received."
    
    except Exception as e:
        return f"Error: {e}"

