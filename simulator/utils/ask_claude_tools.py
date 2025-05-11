from anthropic import Anthropic
from django.conf import settings
from typing import Optional
import json
import re

def ask_claude_tools(prompt: str, model_name: str, tools: Optional[list] = None, max_tokens: Optional[int] = 1000) -> str:
    """
    Calls the Claude API with tools for optimization tasks and returns the response.
    
    Args:
        prompt: The text prompt to send to Claude
        model_name: The Claude model to use
        max_tokens: Maximum number of tokens in the response
        tools: List of tools to use
    Returns:
        str: JSON formatted string containing the optimization strategies
    """
    try:
        client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        
        message = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=tools,
        )
        
        # Check for tool calls in the response
       
        for content in message.content:
            
            if content.type == 'tool_use':
                # Extract the tool call data directly from the ToolUseBlock
                tool_data = content.input
                return tool_data
        
        return json.dumps({"error": "No valid content found in response"})
            
    except Exception as e:
        error_message = str(e)
        print(f"Error in ask_claude_optimize: {error_message}")
        return json.dumps({"error": error_message})  # Return JSON error, don't raise