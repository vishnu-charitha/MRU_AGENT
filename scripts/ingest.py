import os
import uuid
import re
import json
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()
qdrant_url = os.getenv('QDRANT_URL')
qdrant_key = os.getenv('QDRANT_API_KEY')

print("Connecting to Qdrant...")
client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
collection_name = 'mrdu_knowledge_base'

collections = [c.name for c in client.get_collections().collections]
if collection_name not in collections:
    print(f"Creating collection {collection_name}...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Reading and parsing Markdown...")
filename = 'MRDU_Chatbot_Knowledge_Base_100pages.md'
with open(filename, 'r', encoding='utf-8') as f:
    text = f.read()

# Custom Markdown Chunker
chunks = []
# split by H2
sections = re.split(r'\n(?=## )', text)

for sec in sections:
    if not sec.strip(): continue
    lines = sec.strip().split('\n')
    header = lines[0].strip('# ')
    content = '\n'.join(lines[1:]).strip()
    
    # split further by H3
    subsections = re.split(r'\n(?=### )', content)
    for subsec in subsections:
        if not subsec.strip(): continue
        sub_lines = subsec.strip().split('\n')
        sub_header = sub_lines[0].strip('# ') if subsec.startswith('###') else header
        
        chunk_content = subsec.strip()
        if not chunk_content: continue
        
        # Metadata extraction
        lcontent = chunk_content.lower()
        campus = 'tirupati' if 'tirupati' in lcontent else 'main'
        program = 'B.Tech' if 'b.tech' in lcontent else ('M.Tech' if 'm.tech' in lcontent else None)
        regulation = 'MR24' if 'mr24' in lcontent else ('MR22' if 'mr22' in lcontent else ('MR20' if 'mr20' in lcontent else None))
        category = 'Admissions' if 'admission' in lcontent else ('Examinations' if 'exam' in lcontent else 'General')
        
        title = f"{header} - {sub_header}" if header != sub_header else header
        
        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_content))
        chunks.append({
            'chunk_id': chunk_id,
            'content': chunk_content,
            'title': title,
            'section': header,
            'campus': campus,
            'program': program,
            'regulation': regulation,
            'category': category,
            'source_url': 'https://mrdu.edu.in',
            'source_file': 'MRDU_Chatbot_Knowledge_Base_100pages.md'
        })

print(f"Total chunks created: {len(chunks)}")

print("Embedding and uploading chunks...")
batch_size = 50
total_uploaded = 0
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    texts = [c['content'] for c in batch]
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()
    
    points = []
    for j, c in enumerate(batch):
        points.append(PointStruct(
            id=c['chunk_id'],
            vector=embeddings[j],
            payload=c
        ))
    client.upsert(collection_name=collection_name, points=points)
    total_uploaded += len(batch)
    print(f"Uploaded {total_uploaded}/{len(chunks)} points")

info = client.get_collection(collection_name)
print(f"Collection: {collection_name}")
print(f"Vector Count: {info.points_count}")
print(f"Vector Dimension: {info.config.params.vectors.size}")
print(f"Distance Metric: {info.config.params.vectors.distance}")

sample, _ = client.scroll(collection_name, limit=1, with_payload=True, with_vectors=False)
print("Sample payload:", json.dumps(sample[0].payload, indent=2) if sample else "None")

# Test Retrieval
questions = [
    "What is Malla Reddy Deemed to be University?",
    "What programmes are available?",
    "What is the CSE approved intake?",
    "What are the official contact details?",
    "What information is available about the Tirupati campus?"
]

print("\n--- RETRIEVAL TESTS ---")
for q in questions:
    vec = model.encode(q, normalize_embeddings=True).tolist()
    hits = client.query_points(collection_name=collection_name, query=vec, limit=2).points
    print(f"\nQ: {q}")
    for h in hits:
        print(f"  - Score: {h.score:.4f} | Title: {h.payload.get('title')} | Campus: {h.payload.get('campus')}")

print("\n--- API CHAT LOGIC TEST ---")
import sys
sys.path.append(os.getcwd())
from api.services.rag_service import get_rag_service
srv = get_rag_service()
print("RAG Service Initialized")
for q in questions[:1]:
    hits = srv.retrieve(q)
    print(f"API Retrieve hits for '{q}': {len(hits)}")
    if hits:
        ans = srv.generate_answer(q, hits)
        print(f"API Answer Preview: {ans['answer'][:100]}...")

