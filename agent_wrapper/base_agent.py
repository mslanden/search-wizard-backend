class AgentWrapper:
    def __init__(self, framework, api_key=None):
        if framework == "openai":
            from .openai import OpenAIAgent
            self.agent = OpenAIAgent(api_key)
        elif framework == "anthropic":
            from .anthropic import AnthropicAgent
            self.agent = AnthropicAgent(api_key)
        elif framework == "gemini":
            from .gemini import GeminiAgent
            self.agent = GeminiAgent(api_key)
        elif framework == "deepseek":
            # Assuming DeepSeek module exists or will be added later
            from .deepseek import DeepSeekAgent
            self.agent = DeepSeekAgent(api_key)
        else:
            raise ValueError("Unsupported framework")

    def run(self, prompt, image_path=None):
        result = self.agent.run(prompt, image_path)
        
        # Check if the result is an error message
        if isinstance(result, str) and result.startswith("Error:"):
            # Extract the error message
            error_msg = result[7:].strip()
            raise Exception(f"LLM execution failed: {error_msg}")
            
        return result
