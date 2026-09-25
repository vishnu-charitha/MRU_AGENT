import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# We only import these if they exist, but since previous step proved they do, it's safe.
try:
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

MODEL_NAME = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

def main():
    parser = argparse.ArgumentParser(description="Test MRDU Qdrant Retrieval")
    parser.add_argument("query", nargs="?", type=str, help="Search query")
    parser.add_argument("--campus", type=str, help="Filter by campus")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--program", type=str, help="Filter by program")
    parser.add_argument("--regulation", type=str, help="Filter by regulation")
    parser.add_argument("--run-tests", action="store_true", help="Run automated tests")
    
    args = parser.parse_args()

    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_key = os.getenv('QDRANT_API_KEY')
    qdrant_collection = os.getenv('QDRANT_COLLECTION', 'mrdu_knowledge_base')

    if not qdrant_url or not qdrant_key:
        print("Error: Missing QDRANT_URL or QDRANT_API_KEY in environment or .env file")
        sys.exit(1)

    print(f"Loading embedding model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"Connecting to Qdrant at {qdrant_url}...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)

    def search(query, campus=None, category=None, program=None, regulation=None, limit=5):
        vec = model.encode(query, normalize_embeddings=True).tolist()
        
        must_conditions = []
        if campus: must_conditions.append(FieldCondition(key="campus", match=MatchValue(value=campus)))
        if category: must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
        if program: must_conditions.append(FieldCondition(key="program", match=MatchValue(value=program)))
        if regulation: must_conditions.append(FieldCondition(key="regulation", match=MatchValue(value=regulation)))
        
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        hits = client.query_points(
            collection_name=qdrant_collection,
            query=vec,
            query_filter=query_filter,
            limit=limit
        )
        return hits.points

    if args.run_tests:
        print("\n--- Running automated retrieval tests ---")
        test_queries = [
            ("B.Tech admission eligibility", {}),
            ("B.Tech fees", {"program": "B.Tech"}),
            ("CSE department", {}),
            ("examination timetable", {}),
            ("MR24 regulation", {"regulation": "MR24"}),
            ("Tirupati campus", {"campus": "tirupati"}),
            ("MBA admission", {}),
            ("BCA admission", {})
        ]
        
        report = []
        for q, filters in test_queries:
            hits = search(q, **filters)
            results = []
            for hit in hits:
                results.append({
                    "score": hit.score,
                    "chunk_id": hit.payload.get("chunk_id"),
                    "title": hit.payload.get("title"),
                    "program": hit.payload.get("program"),
                    "category": hit.payload.get("category"),
                    "campus": hit.payload.get("campus"),
                    "regulation": hit.payload.get("regulation"),
                    "content_snippet": hit.payload.get("content", "")[:150].replace('\n', ' ') + "..."
                })
            
            # Simple thresholding / logic for out-of-scope identification
            out_of_scope = False
            top_score = hits[0].score if hits else 0
            # Since MBA and BCA chunks were explicitly removed, their scores against the remaining engineering corpus should be lower or completely mismatched.
            if "MBA" in q or "BCA" in q:
                if top_score < 0.65 or all(r['program'] not in ['MBA', 'BCA'] for r in results):
                    out_of_scope = True
                    
            report.append({
                "query": q,
                "filters": filters,
                "top_score": top_score,
                "results_found": len(hits),
                "is_out_of_scope": out_of_scope,
                "top_results": results
            })
            
        report_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'retrieval_test_report.json')
        with open(report_path, "w", encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        print(f"\nAutomated test report saved to {report_path}")
        sys.exit(0)

    if not args.query:
        print("Please provide a query string or use --run-tests.")
        print('Example: python scripts/test_retrieval.py "What are the B.Tech fees?" --program B.Tech')
        sys.exit(1)

    print(f"\nQuery: '{args.query}'")
    if args.campus: print(f"Filter -> campus: {args.campus}")
    if args.category: print(f"Filter -> category: {args.category}")
    if args.program: print(f"Filter -> program: {args.program}")
    if args.regulation: print(f"Filter -> regulation: {args.regulation}")

    hits = search(args.query, args.campus, args.category, args.program, args.regulation)
    
    print(f"\n--- TOP {len(hits)} RESULTS ---")
    for i, hit in enumerate(hits):
        print(f"\n[Rank {i+1}] Score: {hit.score:.4f} | Chunk ID: {hit.payload.get('chunk_id')}")
        print(f"Source: {hit.payload.get('source_url', 'N/A')}")
        print(f"Title: {hit.payload.get('title')} | Campus: {hit.payload.get('campus')} | Category: {hit.payload.get('category')}")
        print(f"Program: {hit.payload.get('program')} | Regulation: {hit.payload.get('regulation')}")
        print("-" * 40)
        content = hit.payload.get("content", "").strip()
        preview = content if len(content) <= 300 else content[:300] + "..."
        print(preview)
        print("=" * 60)

if __name__ == '__main__':
    main()
