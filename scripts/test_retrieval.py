import sys
sys.path.append('.')
from api.services.rag_service import get_rag_service

srv = get_rag_service()
queries = [
    "What are the eligibility criteria for B.Tech admission at MRDU?",
    "Is there an entrance exam for B.Tech?",
    "What is the B.Tech CSE intake capacity at the main campus?"
]

for q in queries:
    print(f'\n--- Query: {q} ---')
    hits = srv.retrieve(q, limit=5)
    for i, h in enumerate(hits):
        c = h.payload.get('campus')
        t = h.payload.get('title')
        s = h.payload.get('section')
        content = h.payload.get('content', '')[:150].replace('\n', ' ')
        print(f'Rank {i+1}: Score={h.score:.4f} | Campus={c} | Title={t} | Section={s}')
        print(f'Excerpt: {content}...\n')
