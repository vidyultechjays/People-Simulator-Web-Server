from anthropic import Anthropic
from django.conf import settings
from typing import Optional

def ask_claude(prompt: str,model_name: str, max_tokens: Optional[int] = 1000) -> str:
    """
    Calls the Claude API and returns the response.
    """
    try:
        client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        
        message = client.messages.create(
            model=model_name,  # You can change this to your preferred Claude model
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        # Extract and return the response text
        if message and hasattr(message, 'content'):
            print(f'message: {message}')
            # Get the first content block of type 'text'
            for content in message.content:
                if content.type == 'text':
                    return content.text
            
            return "No text content found in response."
            
        else:
            return "No response received."
            
    except Exception as e:
        return f"Error: {e}"