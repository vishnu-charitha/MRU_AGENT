import logging; logging.basicConfig(level=logging.DEBUG)
import os
import sys
os.environ['QDRANT_COLLECTION'] = 'mrdu_knowledge_base_v3'
sys.path.append(os.getcwd())
from api.services.rag_service import get_rag_service

service = get_rag_service()
queries = [
    ("Are there any provisions for makeup exams?", None),
    ("How is the CGPA calculated for B.Tech students?", None),
    ("Do I need a valid GATE score for M.Tech admissions?", None),
    ("What is the B.Tech fee?", "tirupati"),
    ("Does the campus have an alien landing pad?", None),
    ("Who is the HOD of Civil Engineering?", "tirupati"),
    ("what is the duration of b.tech?", None)
]

for q, campus in queries:
    print(f"\\n=======================================================")
    print(f"--- QUERY: {q} | CAMPUS: {campus} ---")
    hits = service.retrieve(q, campus=campus, limit=5)
    print(f"Retrieved {len(hits)} hits:")
    for i, h in enumerate(hits):
        print(f"  [{i+1}] Score: {h.score:.4f} | Text: {h.payload.get('content', '')[:100].replace(chr(10), ' ').encode('ascii', 'ignore').decode('ascii')}...")
        print(f"       Metadata: Campus={h.payload.get('campus')}, Program={h.payload.get('program')}, Category={h.payload.get('category')}")
