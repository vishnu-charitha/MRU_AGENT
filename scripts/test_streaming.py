import requests
import time
import json

url = "http://localhost:8000/api/chat"
test_queries = [
    "What programmes are available?",
    "What is the approved CSE intake?",
    "What is the admissions contact number?"
]

print("Warming up API (lazy loading weights)...", flush=True)
try:
    _ = requests.post(url, json={"question": "hi"}, timeout=30)
except Exception as e:
    print("Warm up error:", e)

for q in test_queries:
    print(f"\n--- Query: {q} ---", flush=True)
    payload = {"question": q}
    
    t0 = time.time()
    try:
        response = requests.post(url, json=payload, stream=True)
        t_first_chunk = None
        
        full_content = ""
        for line in response.iter_lines():
            if line:
                if t_first_chunk is None:
                    t_first_chunk = time.time()
                try:
                    data = json.loads(line)
                    if "answer_chunk" in data:
                        full_content += data["answer_chunk"]
                except:
                    pass
        
        t_total = time.time()
        
        if t_first_chunk:
            print(f"Time to First Streamed Token (TTFT): {t_first_chunk - t0:.4f}s", flush=True)
            print(f"Total Request Time: {t_total - t0:.4f}s", flush=True)
        else:
            print(f"Total Request Time: {t_total - t0:.4f}s (no chunks)", flush=True)
            
    except Exception as e:
        print(f"Error: {e}")
