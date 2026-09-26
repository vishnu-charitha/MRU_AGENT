import requests
import json
import time

url = "http://localhost:8000/api/chat"
queries = [
    "What programmes are available?",
    "What is the approved CSE intake?",
    "cse fee",
    "What is the capital of France?"
]

for q in queries:
    print(f"\n=========================")
    print(f"QUERY: {q}")
    payload = {"question": q}
    
    try:
        response = requests.post(url, json=payload, stream=True)
        full_text = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "answer_chunk" in data:
                    full_text += data["answer_chunk"]
                elif "answer" in data:
                    full_text = data["answer"]
        print(f"RESPONSE:\n{full_text}")
    except Exception as e:
        print(f"Error: {e}")
