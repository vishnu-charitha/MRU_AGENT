import requests

url = 'http://localhost:8000/api/chat'

# First query
print("=== FIRST QUERY ===")
data1 = {
  "question": "What is the duration of B.Tech?",
  "history": []
}
res1 = requests.post(url, json=data1, stream=True)
print("Status:", res1.status_code)
content1 = ""
for chunk in res1.iter_lines():
    if chunk:
        print(chunk.decode())
        content1 += chunk.decode() + "\n"

# Second query
print("\n=== SECOND QUERY ===")
data2 = {
  "question": "What about the eligibility?",
  "history": [
      {"role": "user", "content": "What is the duration of B.Tech?"},
      {"role": "assistant", "content": "The B.Tech program is 4 years, comprising 8 semesters."}
  ]
}
res2 = requests.post(url, json=data2, stream=True)
print("Status:", res2.status_code)
for chunk in res2.iter_lines():
    if chunk:
        print(chunk.decode())
