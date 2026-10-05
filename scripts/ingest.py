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
client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=60)
collection_name = 'mrdu_knowledge_base_v3'

collections = [c.name for c in client.get_collections().collections]
if collection_name in collections:
    print(f"Deleting old collection {collection_name} to re-index...")
    client.delete_collection(collection_name)

print(f"Creating collection {collection_name}...")
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

print("Creating payload indices...")
for field in ['campus', 'program', 'category', 'regulation']:
    client.create_payload_index(
        collection_name=collection_name,
        field_name=field,
        field_schema="keyword"
    )
print("Reading and parsing Markdown...")
filename = 'MRDU_Chatbot_Knowledge_Base_100pages.md'
with open(filename, 'r', encoding='utf-8') as f:
    text = f.read()

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# Structural chunking by Markdown headers
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]
markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

# Pre-split on Header 1 to prevent catastrophic backtracking in MarkdownHeaderTextSplitter regex
raw_sections = text.split('\n# ')
md_header_splits = []
for i, section_text in enumerate(raw_sections):
    if i > 0:
        section_text = '# ' + section_text
    md_header_splits.extend(markdown_splitter.split_text(section_text))

# Further recursive split for large chunks to respect embedding limits safely
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)
docs = text_splitter.split_documents(md_header_splits)

# Post-process docs to ensure Markdown table rows are independent
new_docs = []
for doc in docs:
    lines = doc.page_content.split('\n')
    current_chunk = []
    for line in lines:
        if line.strip().startswith('|') and len(line.split('|')) > 3:
            if current_chunk:
                new_docs.append({'page_content': '\n'.join(current_chunk), 'metadata': doc.metadata})
                current_chunk = []
            new_docs.append({'page_content': line, 'metadata': doc.metadata})
        else:
            current_chunk.append(line)
    if current_chunk:
        new_docs.append({'page_content': '\n'.join(current_chunk), 'metadata': doc.metadata})

chunks = []
for doc in new_docs:
    chunk_content = doc['page_content'].strip()
    if not chunk_content: continue

    metadata = doc['metadata']
    h1 = metadata.get("Header 1", "")
    h2 = metadata.get("Header 2", "")
    h3 = metadata.get("Header 3", "")

    title_parts = [h for h in [h1, h2, h3] if h]
    title = " - ".join(title_parts) if title_parts else "General Info"
    section = h1 or h2 or "General"

    # Metadata extraction
    lcontent = (title + " " + chunk_content).lower()
    
    if 'tirupati' in lcontent:
        campus = 'tirupati'
    elif 'main campus' in lcontent or 'hyderabad' in lcontent or 'maisammaguda' in lcontent:
        campus = 'main'
    else:
        campus = None

    has_btech = 'b.tech' in lcontent or 'btech' in lcontent
    has_mtech = 'm.tech' in lcontent or 'mtech' in lcontent
    
    if has_btech and not has_mtech:
        program = 'B.Tech'
    elif has_mtech and not has_btech:
        program = 'M.Tech'
    else:
        program = None

    regulation = 'MR24' if 'mr24' in lcontent else ('MR22' if 'mr22' in lcontent else ('MR20' if 'mr20' in lcontent else None))
    category = 'Admissions' if 'admission' in lcontent else ('Examinations' if 'exam' in lcontent else 'General')

    chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_content))
    chunks.append({
        'chunk_id': chunk_id,
        'content': chunk_content,
        'title': title,
        'section': section,
        'campus': campus,
        'program': program,
        'regulation': regulation,
        'category': category,
        'source_url': 'https://mrdu.edu.in',
        'source_file': 'MRDU_Chatbot_Knowledge_Base_100pages.md'
    })

print(f"Total structured chunks created: {len(chunks)}")

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding and uploading chunks...")
batch_size = 25
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

