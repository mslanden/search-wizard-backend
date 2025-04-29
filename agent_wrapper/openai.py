from openai import OpenAI

class OpenAIAgent:
    def __init__(self, api_key):
        # Create the client instance with the API key
        # Adjusted for compatibility with OpenAI version 1.3.0
        self.client = OpenAI(
            api_key=api_key,
            # Remove any parameters that might cause issues in older versions
        )

    def run(self, prompt, image_path=None):
        try:
            # Build the conversation messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]

            if image_path:
                messages.append({
                    "role": "user",
                    "content": f"This is the image path: {image_path}"
                })

            # Call the ChatCompletion endpoint using the client
            response = self.client.chat.completions.create(
                model="o3-mini",
                messages=messages
            )

            # Extract and return the assistant's reply
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"
