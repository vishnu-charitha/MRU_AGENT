import os
from api.services.rag_service import get_rag_service

service = get_rag_service()
queries = [
    "what are the b.tech programmes?",
    "what is the cse fee?"
]

for q in queries:
    print(f"\nQuery: {q}")
    hits = service.retrieve(q, limit=3)
    print(f"Found {len(hits)} hits")
    for h in hits:
        print(f"Score: {h.score}")
        print(f"Content Preview: {h.payload.get('content', '')[:100]}")
