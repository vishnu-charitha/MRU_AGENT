import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath('.'))
from api.services.rag_service import get_rag_service

load_dotenv()
rag_service = get_rag_service()

query = "What programmes are available?"
print(f"Retrieving context for: {query}")
hits = rag_service.retrieve(query, limit=3)

context_parts = []
for h in hits:
    content = h.payload.get('content', '')
    title = h.payload.get('title', 'Unknown Document')
    campus = h.payload.get('campus', 'main')
    context_parts.append(f"--- Document: {title} (Campus: {campus}) ---\n{content}")
    
context = "\n\n".join(context_parts)

system_prompt = f"""You are an MRDU college information assistant.
Answer the user's question using ONLY the provided context.
If the context does not contain the answer, say that the information is not available.
Do not repeat words or sentences.
Give a concise answer.

Context:
{context}
"""

print("\n--- SIMPLE RAG GENERATION ---")
resp = rag_service.llm_client.chat.completions.create(
    model=rag_service.openrouter_model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
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
