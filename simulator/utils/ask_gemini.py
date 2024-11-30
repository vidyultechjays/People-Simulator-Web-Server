import google.generativeai as genai
from django.conf import settings

# Configure API
genai.configure(api_key=settings.API_KEY)

def ask_gemini(prompt):
    """Calls the Gemini LLM and returns the response."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-002")
        response = model.generate_content(prompt)
        
        # Print the full response to inspect its structure
        print("Full Response:", response)

        # Adjust to the correct attribute based on the response structure
        if response and hasattr(response, 'text'):
            return response.text  # Assuming 'text' is the correct attribute
        elif response and hasattr(response, 'candidates'):
            return response.candidates[0].get('output', 'No output found')  # Check for 'candidates' and extract output
        else:
            return "No response received."
    
    except Exception as e:
        return f"Error: {e}"
# def ask_gemini(prompt):
#     """Calls the Gemini LLM and returns the response."""
#     try:
#         model = genai.GenerativeModel("gemini-1.5-flash-002")
#         response = model.generate_content(prompt)
#         return response.result if response else "No response received."
#     except Exception as e:
#         return f"Error: {e}"
