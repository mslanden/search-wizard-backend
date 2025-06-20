#!/usr/bin/env python3
import requests
import json

# Test the URL processing endpoint
url = "http://localhost:8000/process-content"
data = {
    "content_type": "url",
    "content": "https://www.google.com",
    "artifact_type": "company"
}

print(f"Testing {url} with data:", json.dumps(data, indent=2))
print("-" * 50)

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")