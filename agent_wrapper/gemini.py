import requests
import time

class GeminiAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def run(self, prompt, image_path=None):
        if image_path:
            prompt += f" Also, use the information from this image: {image_path}"

        delay = 1          # initial delay in seconds
        max_delay = 60     # maximum delay allowed before giving up

        while True:
            try:
                response = requests.post(
                    self.url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key
                    },
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "maxOutputTokens": 2048
                        }
                    }
                )
                response.raise_for_status()
                # Parse the JSON response
                return response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")
            except Exception as e:
                # If the delay exceeds the maximum allowed, return the error message.
                if delay > max_delay:
                    return f"Error: {str(e)}"
                print(f"Request failed: {e}. Retrying in {delay} second(s)...")
                time.sleep(delay)
                delay *= 2  # Double the delay for the next attempt
