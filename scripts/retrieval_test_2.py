import os
import sys
sys.path.append(os.getcwd())
from api.services.rag_service import get_rag_service

srv = get_rag_service()

questions = [
    'What is Malla Reddy Deemed to be University?',
    'What is the CSE approved intake?',
    'What programmes are available?',
    'What are the official contact details?',
    'What information is available about the Tirupati campus?',
    'What courses are offered?',
    'How can I contact MRDU?'
]

print('\n--- RETRIEVAL TESTS ---', flush=True)
for q in questions:
    hits = srv.retrieve(q, limit=3)
    print(f'\nQ: {q}', flush=True)
    for h in hits:
        print(f'  - Score: {h.score:.4f} | Title: {h.payload.get("title")} | Section: {h.payload.get("section")} | URL: {h.payload.get("source_url")}', flush=True)

print('\n--- API CHAT LOGIC TEST ---', flush=True)
chat_questions = [
    'What programmes are available?',
    'What are the official contact details?',
    'What is the CSE approved intake?'
]
for q in chat_questions:
    hits = srv.retrieve(q, limit=5)
    print(f"\nAPI Retrieve hits for '{q}': {len(hits)}", flush=True)
    if hits:
        ans = srv.generate_answer(q, hits)
        print(f"API Answer: {ans['answer'][:150]}...", flush=True)
