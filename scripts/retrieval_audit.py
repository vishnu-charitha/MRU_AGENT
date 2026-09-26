import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
qdrant_url = os.getenv('QDRANT_URL')
qdrant_key = os.getenv('QDRANT_API_KEY')
client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
collection_name = 'mrdu_knowledge_base'
model = SentenceTransformer('all-MiniLM-L6-v2')

questions = [
    'What is Malla Reddy Deemed to be University?',
    'What is the CSE approved intake?',
    'What programmes are available?',
    'What are the official contact details?',
    'What information is available about the Tirupati campus?'
]
for q in questions:
    vec = model.encode(q, normalize_embeddings=True).tolist()
    hits = client.query_points(collection_name=collection_name, query=vec, limit=3).points
    print(f'\nQ: {q}')
    for h in hits:
        print(f'  - Score: {h.score:.4f} | Title: {h.payload.get("title")} | Section: {h.payload.get("section")} | URL: {h.payload.get("source_url")}')
