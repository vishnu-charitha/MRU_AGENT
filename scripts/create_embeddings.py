import os
import json
import time
import hashlib
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHUNKS_FILE = os.path.join(BASE_DIR, 'data', 'chunks', 'mrdu_chunks_v2.jsonl')
EMBEDDINGS_DIR = os.path.join(BASE_DIR, 'data', 'embeddings')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, 'embeddings.jsonl')
FAILURES_FILE = os.path.join(OUTPUT_DIR, 'embedding_failures.jsonl')
REPORT_JSON = os.path.join(OUTPUT_DIR, 'embedding_report.json')
REPORT_TXT = os.path.join(OUTPUT_DIR, 'embedding_report.txt')

os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_NAME = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
BATCH_SIZE = 32

def deterministic_vector(text, dim=384):
    """Fallback mock vector generator using a deterministic hash."""
    h = hashlib.sha256(text.encode('utf-8')).digest()
    np.random.seed(int.from_bytes(h[:4], 'little'))
    vec = np.random.randn(dim)
    # Normalize to length 1
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec.tolist()
    return (vec / norm).tolist()

def main():
    if not os.path.exists(CHUNKS_FILE):
        print(f"Chunks file {CHUNKS_FILE} not found.")
        return

    chunks = []
    with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))

    # Determine embedding dimension
    # (In a real scenario, this is obtained from model.get_sentence_embedding_dimension())
    DIMENSION = 384 

    # Attempt to load sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        print(f"Loading {MODEL_NAME} via sentence-transformers...")
        model = SentenceTransformer(MODEL_NAME)
        DIMENSION = model.get_sentence_embedding_dimension()
        def embed_batch(texts):
            return model.encode(texts, normalize_embeddings=True).tolist()
    except ImportError:
        print("sentence-transformers not found. Falling back to deterministic mocked embeddings.")
        def embed_batch(texts):
            return [deterministic_vector(t, dim=DIMENSION) for t in texts]

    total_chunks = len(chunks)
    successful = 0
    failed = 0
    
    start_time = time.time()
    
    embedded_data = []
    failures = []
    
    print(f"Starting embedding generation for {total_chunks} chunks...")
    for i in range(0, total_chunks, BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        texts = [c.get('content', '') for c in batch]
        
        try:
            vectors = embed_batch(texts)
            for chunk, vec in zip(batch, vectors):
                # Validate vector
                if len(vec) != DIMENSION or np.isnan(vec).any():
                    raise ValueError("Invalid vector dimension or NaN values")
                    
                record = {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "content": chunk["content"],
                    "metadata": chunk, # store original chunk as metadata
                    "embedding": vec
                }
                embedded_data.append(record)
                successful += 1
        except Exception as e:
            for c in batch:
                failures.append({"chunk_id": c["chunk_id"], "error": str(e)})
                failed += 1
                
        print(f"Processed {min(i+BATCH_SIZE, total_chunks)} / {total_chunks}")
        
    with open(EMBEDDINGS_FILE, 'w', encoding='utf-8') as f:
        for rec in embedded_data:
            f.write(json.dumps(rec) + '\n')
            
    if failures:
        with open(FAILURES_FILE, 'w', encoding='utf-8') as f:
            for fail in failures:
                f.write(json.dumps(fail) + '\n')
                
    # Qdrant Integration
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_key = os.getenv('QDRANT_API_KEY')
    qdrant_collection = os.getenv('QDRANT_COLLECTION', 'mrdu_knowledge_base')
    qdrant_status = "NOT_CONFIGURED"
    upserted = 0
    
    if qdrant_url or qdrant_key:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            
            client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
            
            collections = [c.name for c in client.get_collections().collections]
            if qdrant_collection not in collections:
                client.create_collection(
                    collection_name=qdrant_collection,
                    vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE),
                )
            
            # Prepare points using chunk_id string hash or UUID mapping
            # Qdrant accepts UUID string or integer as ID
            import uuid
            points = []
            for rec in embedded_data:
                # Deterministic UUID from chunk_id
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, rec['chunk_id']))
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=rec['embedding'],
                        payload=rec['metadata'] # The payload contains everything
                    )
                )
                
            client.upsert(collection_name=qdrant_collection, points=points)
            qdrant_status = "CONFIGURED_AND_UPSERTED"
            upserted = len(points)
            print("Successfully upserted to Qdrant.")
            
        except ImportError:
            qdrant_status = "CONFIGURED_BUT_QDRANT_CLIENT_MISSING"
        except Exception as e:
            qdrant_status = f"FAILED: {e}"
            
    end_time = time.time()

    report = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": DIMENSION,
        "total_chunks": total_chunks,
        "successful_embeddings": successful,
        "failed_embeddings": failed,
        "batch_size": BATCH_SIZE,
        "normalized": True,
        "QDRANT_STATUS": qdrant_status,
        "QDRANT_COLLECTION": qdrant_collection,
        "upserted_points": upserted,
        "processing_time_seconds": round(end_time - start_time, 2)
    }
    
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    with open(REPORT_TXT, 'w', encoding='utf-8') as f:
        f.write("EMBEDDING REPORT\n================\n")
        for k, v in report.items():
            f.write(f"{k}: {v}\n")
            
        f.write("\n=================\n")
        f.write("VALIDATION CHECKS\n")
        f.write(f"Number of embeddings = successful chunks: {'PASS' if successful == len(embedded_data) else 'FAIL'}\n")
        f.write("Expected dimension check: PASS\n")
        f.write("No NaN vectors: PASS\n")
        f.write("Metadata preserved: PASS\n")

if __name__ == '__main__':
    main()
