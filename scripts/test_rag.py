"""Diagnostic script for MRDU Chatbot RAG integration.

Tests the existing RAG service without mutating, ingesting, or deleting any Qdrant collections.

Usage:
    python scripts/test_rag.py
    python scripts/test_rag.py --test-llm
    python scripts/test_rag.py --query "What are the B.Tech admission eligibility requirements?" --test-llm
"""

import os
import sys
import time
import argparse
import traceback
from dotenv import load_dotenv

# Ensure root workspace directory is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

def main():
    parser = argparse.ArgumentParser(description="Test MRDU Chatbot RAG Service safely.")
    parser.add_argument(
        "--test-llm",
        action="store_true",
        default=os.getenv("TEST_LLM", "false").lower() in ("true", "1", "yes"),
        help="Enable end-to-end answer generation via OpenRouter LLM (disabled by default)."
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What are the B.Tech admission eligibility requirements?",
        help="Sample query to test retrieval and answer generation."
    )
    args = parser.parse_args()

    print("=" * 70)
    print("MRDU Chatbot RAG Integration Diagnostic")
    print("=" * 70)

    # 1. Load Environment Variables
    load_dotenv(override=True)
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION", "mrdu_knowledge_base_v3")
    embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    reranker_model = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    enable_reranker = os.getenv("ENABLE_RERANKER", "true")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it")

    print(f"Target Qdrant Collection : {collection_name}")
    print(f"Embedding Model          : {embedding_model}")
    print(f"Reranker Model           : {reranker_model} (enabled: {enable_reranker})")
    print(f"OpenRouter Model         : {openrouter_model}")
    print(f"OpenRouter Key Present   : {'Yes' if openrouter_key else 'No'}")
    print(f"Qdrant Key Present       : {'Yes' if qdrant_key else 'No'}")
    print("-" * 70)

    if not qdrant_url or not qdrant_key:
        print("[FAIL] Missing QDRANT_URL or QDRANT_API_KEY in environment variables.")
        sys.exit(1)

    # 2. Initialize RAG Service & Measure Time
    print("\n[Step 1] Initializing RAG Service...")
    t0 = time.time()
    try:
        from api.services.rag_service import get_rag_service
        service = get_rag_service()
        init_time = time.time() - t0
        print(f"[PASS] RAG Service initialized in {init_time:.2f}s.")
    except Exception as e:
        print(f"[FAIL] Error initializing RAG Service: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 3. Check Qdrant Collection & Vector Count
    print("\n[Step 2] Validating Qdrant Cloud Collection...")
    t1 = time.time()
    try:
        if not service.qdrant_client:
            print("[FAIL] Qdrant client is not connected.")
            sys.exit(1)

        collections = [c.name for c in service.qdrant_client.get_collections().collections]
        if collection_name not in collections:
            print(f"[FAIL] Collection '{collection_name}' not found. Available collections: {collections}")
            sys.exit(1)

        info = service.qdrant_client.get_collection(collection_name)
        check_time = time.time() - t1
        print(f"[PASS] Collection '{collection_name}' confirmed in {check_time:.2f}s!")
        print(f"       Total Stored Vectors : {info.points_count}")
        print(f"       Vector Dimension     : {info.config.params.vectors.size}")
        print(f"       Distance Metric      : {info.config.params.vectors.distance}")
    except Exception as e:
        print(f"[FAIL] Error checking Qdrant collection: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 4. Test Retrieval
    test_query = args.query
    print(f"\n[Step 3] Running Retrieval Query...")
    print(f"       Query: \"{test_query}\"")
    t2 = time.time()
    try:
        hits = service.retrieve(test_query, limit=5)
        retrieval_time = time.time() - t2
        print(f"[PASS] Retrieved {len(hits)} relevant chunks in {retrieval_time:.2f}s.")
        print("-" * 70)
        for i, hit in enumerate(hits, 1):
            title = hit.payload.get("title", "No Title")
            campus = str(hit.payload.get("campus") or "unspecified")
            preview = hit.payload.get("content", "")[:120].replace("\n", " ")
            print(f" {i}. Score: {hit.score:7.4f} | Campus: {campus:11} | Title: {title}")
            print(f"    Excerpt: {preview}...")
        print("-" * 70)
    except Exception as e:
        print(f"[FAIL] Retrieval failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 5. Test Answer Generation (Optional)
    if args.test_llm:
        print("\n[Step 4] Testing Answer Generation with OpenRouter...")
        t3 = time.time()
        try:
            result = service.generate_answer(test_query, hits)
            llm_time = time.time() - t3
            print(f"[PASS] Answer generated in {llm_time:.2f}s.")
            print("-" * 70)
            print("Answer Preview:")
            print(result.get("answer", "").strip())
            print("-" * 70)
            print(f"Citations: {len(result.get('sources', []))} source(s)")
        except Exception as e:
            print(f"[FAIL] Answer generation failed: {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        print("\n[Step 4] LLM Answer Generation test skipped (use --test-llm to run).")

    print("\n" + "=" * 70)
    print("ALL CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    main()
