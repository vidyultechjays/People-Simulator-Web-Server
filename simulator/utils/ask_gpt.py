import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

def ask_gpt(prompt, model="gpt-4"):
    """Calls the OpenAI GPT model and returns the response."""
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )

        print(f"GPT response : {response}")
        # Extract the response text
        if response and 'choices' in response and len(response.choices) > 0:
            return response.choices[0].message['content'].strip()
        else:
            return "No response received."
    
    except Exception as e:
        return f"Error: {e}"
