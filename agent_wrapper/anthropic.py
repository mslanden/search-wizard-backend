import os
import requests
import anthropic
from typing import Optional
from dotenv import load_dotenv

class AnthropicAgent:
    def __init__(self, api_key: str):
        """
        Initialize the Anthropic agent with an API key.

        Args:
            api_key (str): Your Anthropic API key
        """
        self.api_key = api_key
        self.client = anthropic.Anthropic(
            api_key=api_key
        )
    
    def run(self, prompt: str, image_path: Optional[str] = None) -> str:
        """
        Send a prompt to Claude and get the response.
        
        Args:
            prompt (str): The message to send to Claude
            image_path (str, optional): Path to an image file (for future use)
            
        Returns:
            str: Claude's response text or error message
        """
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text
        except requests.exceptions.RequestException as e:
            return f"Network Error: {str(e)}"
        except Exception as e:
            return f"Unexpected Error: {str(e)}"

def main():
    """Example usage of the AnthropicAgent class"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return
    
    # Create an instance of the agent
    agent = AnthropicAgent(api_key)
    
    # Example prompts
    prompts = [
        "What is the capital of France?",
        "Write a short poem about spring.",
    ]
    
    # Test the agent with multiple prompts
    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        print("-" * 50)
        response = agent.run(prompt)
        print(f"Response: {response}")
        print("-" * 50)

if __name__ == "__main__":
    main()
