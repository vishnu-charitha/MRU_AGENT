import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath('.'))
from api.services.rag_service import get_rag_service

load_dotenv()
rag_service = get_rag_service()

query = "What programmes are available?"
hits = rag_service.retrieve(query, limit=3)

print("\n--- ORIGINAL PROMPT (STREAM=FALSE) ---")

# Let's mock generate_answer to just call the API synchronously
context_parts = []
for h in hits:
    content = h.payload.get('content', '')
    title = h.payload.get('title', 'Unknown Document')
    campus = h.payload.get('campus', 'main')
    context_parts.append(f"--- Document: {title} (Campus: {campus}) ---\n{content}")

context = "\n\n".join(context_parts)

system_prompt = f"""
You are an expert academic assistant for MRDU (Malla Reddy Deemed to be University).
You must answer the user's question using ONLY the provided context.
CRITICAL INSTRUCTIONS:
- Do NOT hallucinate or introduce outside facts under any circumstances.
- If the context lacks sufficient information, you MUST state explicitly: "I couldn't find enough information in the MRDU knowledge base to answer that accurately."
- Distinguish clearly between the main campus and Tirupati campus if applicable.
- Respect program (B.Tech vs M.Tech) and regulation (MR20/MR22/MR24) metadata.
- Exclude MBA/BCA/MCA/BBA information.
- Provide a clear, concise answer.

Context:
{context}
"""

resp = rag_service.llm_client.chat.completions.create(
    model=rag_service.openrouter_model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ],
    temperature=0.1,
    stream=False
)

print(repr(resp.choices[0].message.content))
print("Done.")
