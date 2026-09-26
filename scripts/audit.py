import os
import json
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
qdrant_url = os.getenv('QDRANT_URL')
qdrant_key = os.getenv('QDRANT_API_KEY')

client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
collection_name = 'mrdu_knowledge_base'

info = client.get_collection(collection_name)
print(f'Vector Count: {info.points_count}')

points, _ = client.scroll(collection_name, limit=5, with_payload=True, with_vectors=False)
print('--- SAMPLE PAYLOADS ---')
for p in points:
    print(json.dumps(p.payload, indent=2))

model = SentenceTransformer('all-MiniLM-L6-v2')
questions = [
    "What is Malla Reddy Deemed to be University?",
    "What is the CSE approved intake?",
    "What programmes are available?",
    "What are the official contact details?",
    "What information is available about the Tirupati campus?"
]

print('\n--- RETRIEVAL TESTS ---')
for q in questions:
    vec = model.encode(q, normalize_embeddings=True).tolist()
    hits = client.query_points(collection_name=collection_name, query=vec, limit=3).points
    print(f"\nQ: {q}")
    for h in hits:
        print(f"  - Score: {h.score:.4f} | Title: {h.payload.get('title')} | Section: {h.payload.get('section')} | Source URL: {h.payload.get('source_url')}")
