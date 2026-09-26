import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

print("Testing NON-RAG query...")
resp = client.chat.completions.create(
    model=os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write one short sentence saying that a university offers undergraduate and postgraduate programmes."}
    ],
    temperature=0.0,
    stream=True
)

count = 0
for chunk in resp:
    content = chunk.choices[0].delta.content
    if content:
        count += 1
        print(f"Token {count}: {repr(content)}")

print("Done.")
