import requests
import json
import time

url = "http://localhost:8000/api/chat"
payload = {"question": "What programmes are available?"}

print("Testing backend directly to check for token loops...")
try:
    response = requests.post(url, json=payload, stream=True)
    count = 0
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if "answer_chunk" in data:
                count += 1
                if count <= 50:
                    print(f"Token {count}: {repr(data['answer_chunk'])}")
                if count > 50:
                    print("... (backend is still streaming tokens, indicating a loop)")
                    break
except Exception as e:
    print(f"Error: {e}")
