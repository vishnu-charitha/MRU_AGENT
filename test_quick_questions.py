import os
from api.services.rag_service import get_rag_service

service = get_rag_service()
queries = [
    "What are the B.Tech admission eligibility requirements?",
    "What departments are available at MRDU?",
    "What are the B.Tech fees?",
    "What information is available about the Tirupati campus?",
    "What is the examination timetable?",
    "What is the MR24 regulation?"
]

for q in queries:
    print(f"\nQuery: {q}")
    hits = service.retrieve(q, limit=3)
    print(f"Found {len(hits)} hits")
    if hits:
        print(f"Top Score: {hits[0].score}")
        print(f"Content Preview: {hits[0].payload.get('content', '')[:100]}")
    else:
        print("No hits found!")
