import requests

url = "http://localhost:8000/api/chat"
payload = {
    "question": "What programmes are available?"
}
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response snippet: {str(response.json())[:300]}")
except Exception as e:
    print(f"Error: {e}")
