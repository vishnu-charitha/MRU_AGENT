import os
import sys
sys.path.append(os.getcwd())
from api.services.rag_service import get_rag_service

srv = get_rag_service()

questions = [
    "What is the university's general enquiry phone number?",
    "What is the admissions contact number?",
    "What is the official MRDU email address?",
    "What is the address of the main campus?",
    "What is the address of the Tirupati campus?",
    "What is the approved CSE intake?",
    "What B.Tech programmes are available?",
    "Who is the contact person for admissions?",
    "Give me information about the CSE department.",
    "What are the frequently asked questions about admissions?"
]

print('\n--- RETRIEVAL VALIDATION ---', flush=True)
for q in questions:
    hits = srv.retrieve(q, limit=5)
    print(f'\nQ: {q}', flush=True)
    for i, h in enumerate(hits):
        print(f'  [{i+1}] Score: {h.score:.4f} | Title: {h.payload.get("title")} | Section: {h.payload.get("section")} | URL: {h.payload.get("source_url")}', flush=True)

print('\n--- API CHAT LOGIC TEST ---', flush=True)
for q in questions:
    hits = srv.retrieve(q, limit=5)
    print(f"\nAPI Retrieve hits for '{q}': {len(hits)}", flush=True)
    if hits:
        ans = srv.generate_answer(q, hits)
        print(f"API Answer:\n{ans['answer'][:250]}...", flush=True)
