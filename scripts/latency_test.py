import os
import sys
import time
sys.path.append(os.getcwd())
from api.services.rag_service import get_rag_service

print("Initializing RAG Service...", flush=True)
t0 = time.time()
srv = get_rag_service()
t1 = time.time()
print(f"Initialization Time: {t1 - t0:.4f}s", flush=True)

question = "What programmes are available?"

for i in range(3):
    print(f"\n--- Run {i+1} ---", flush=True)
    
    t_start = time.time()
    
    expanded_query = question.lower()
    if any(w in expanded_query for w in ['programme', 'programmes', 'course', 'courses']):
        expanded_query += " programmes courses programme portfolio sanctioned intake undergraduate postgraduate"
    
    t_emb_start = time.time()
    vec = srv.model.encode(expanded_query, normalize_embeddings=True).tolist()
    t_emb_end = time.time()
    
    t_qdrant_start = time.time()
    hits_obj = srv.qdrant_client.query_points(
        collection_name=srv.qdrant_collection,
        query=vec,
        limit=5
    )
    hits = hits_obj.points
    t_qdrant_end = time.time()
    
    t_llm_start = time.time()
    ans = srv.generate_answer(question, hits)
    t_llm_end = time.time()
    
    t_end = time.time()
    
    print(f"Embedding Time: {t_emb_end - t_emb_start:.4f}s", flush=True)
    print(f"Qdrant Retrieval Time: {t_qdrant_end - t_qdrant_start:.4f}s", flush=True)
    print(f"Number of retrieved chunks: {len(hits)}", flush=True)
    print(f"OpenRouter Generation Time: {t_llm_end - t_llm_start:.4f}s", flush=True)
    print(f"Total Response Time: {t_end - t_start:.4f}s", flush=True)
