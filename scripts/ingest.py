
import os
import uuid
import json
import sys
import traceback

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer

load_dotenv(override=True)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "mrdu_knowledge_base_v3"
MARKDOWN_FILE = "MRDU_Chatbot_Knowledge_Base_100pages.md"

if not QDRANT_URL or not QDRANT_API_KEY:
    raise RuntimeError(
        "Missing QDRANT_URL or QDRANT_API_KEY in your .env file."
    )

QUESTIONS = [
    "What is Malla Reddy Deemed to be University?",
    "What programmes are available?",
    "What is the CSE approved intake?",
    "What are the official contact details?",
    "What information is available about the Tirupati campus?",
]


def main():
    print("Connecting to Qdrant...", flush=True)

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=60,
    )

    # ---------------------------------------------------------
    # INGESTION
    # WARNING: This section deletes and recreates the collection.
    # ---------------------------------------------------------
    existing = [
        collection.name
        for collection in client.get_collections().collections
    ]

    if COLLECTION_NAME in existing:
        print(
            f"Deleting old collection {COLLECTION_NAME}...",
            flush=True,
        )
        client.delete_collection(COLLECTION_NAME)

    print(f"Creating collection {COLLECTION_NAME}...", flush=True)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=384,
            distance=Distance.COSINE,
        ),
    )

    print("Creating payload indexes...", flush=True)

    for field in ["campus", "program", "category", "regulation"]:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema="keyword",
        )

    # ---------------------------------------------------------
    # READ AND SPLIT MARKDOWN
    # ---------------------------------------------------------
    print(f"Reading {MARKDOWN_FILE}...", flush=True)

    with open(MARKDOWN_FILE, "r", encoding="utf-8") as file:
        text = file.read()

    try:
        from langchain_text_splitters import (
            MarkdownHeaderTextSplitter,
            RecursiveCharacterTextSplitter,
        )
    except ImportError:
        from langchain.text_splitter import (
            MarkdownHeaderTextSplitter,
            RecursiveCharacterTextSplitter,
        )

    headers = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers
    )

    raw_sections = text.split("\n# ")
    markdown_docs = []

    for index, section_text in enumerate(raw_sections):
        if index > 0:
            section_text = "# " + section_text

        markdown_docs.extend(
            markdown_splitter.split_text(section_text)
        )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )

    docs = text_splitter.split_documents(markdown_docs)

    # Keep Markdown table rows as separate chunks, matching the
    # behavior of the original script.
    processed_docs = []

    for doc in docs:
        current_lines = []

        for line in doc.page_content.split("\n"):
            if line.strip().startswith("|") and len(line.split("|")) > 3:
                if current_lines:
                    processed_docs.append({
                        "page_content": "\n".join(current_lines),
                        "metadata": doc.metadata,
                    })
                    current_lines = []

                processed_docs.append({
                    "page_content": line,
                    "metadata": doc.metadata,
                })
            else:
                current_lines.append(line)

        if current_lines:
            processed_docs.append({
                "page_content": "\n".join(current_lines),
                "metadata": doc.metadata,
            })

    chunks = []

    for doc in processed_docs:
        content = doc["page_content"].strip()

        if not content:
            continue

        metadata = doc["metadata"]

        h1 = metadata.get("Header 1", "")
        h2 = metadata.get("Header 2", "")
        h3 = metadata.get("Header 3", "")

        title = " - ".join(
            heading for heading in [h1, h2, h3] if heading
        ) or "General Info"

        section = h1 or h2 or "General"
        lower_content = (title + " " + content).lower()

        if "tirupati" in lower_content:
            campus = "tirupati"
        elif any(
            word in lower_content
            for word in ["main campus", "hyderabad", "maisammaguda"]
        ):
            campus = "main"
        else:
            campus = None

        has_btech = "b.tech" in lower_content or "btech" in lower_content
        has_mtech = "m.tech" in lower_content or "mtech" in lower_content

        if has_btech and not has_mtech:
            program = "B.Tech"
        elif has_mtech and not has_btech:
            program = "M.Tech"
        else:
            program = None

        if "mr24" in lower_content:
            regulation = "MR24"
        elif "mr22" in lower_content:
            regulation = "MR22"
        elif "mr20" in lower_content:
            regulation = "MR20"
        else:
            regulation = None

        if "admission" in lower_content:
            category = "Admissions"
        elif "exam" in lower_content:
            category = "Examinations"
        else:
            category = "General"

        # Preserve the original deterministic-ID behavior.
        chunk_id = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, content)
        )

        chunks.append({
            "chunk_id": chunk_id,
            "content": content,
            "title": title,
            "section": section,
            "campus": campus,
            "program": program,
            "regulation": regulation,
            "category": category,
            "source_url": "https://mrdu.edu.in",
            "source_file": MARKDOWN_FILE,
        })

    print(f"Total structured chunks created: {len(chunks)}", flush=True)

    # ---------------------------------------------------------
    # EMBEDDING AND UPLOAD
    # ---------------------------------------------------------
    print("Loading embedding model...", flush=True)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Embedding and uploading chunks...", flush=True)

    batch_size = 25
    total_uploaded = 0

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [chunk["content"] for chunk in batch]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        points = []

        for index, chunk in enumerate(batch):
            points.append(
                PointStruct(
                    id=chunk["chunk_id"],
                    vector=embeddings[index],
                    payload=chunk,
                )
            )

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

        total_uploaded += len(batch)

        print(
            f"Processed {total_uploaded}/{len(chunks)} chunks",
            flush=True,
        )

    info = client.get_collection(COLLECTION_NAME)

    print(f"\nCollection: {COLLECTION_NAME}", flush=True)
    print(f"Unique stored vectors: {info.points_count}", flush=True)
    print(
        f"Vector dimension: {info.config.params.vectors.size}",
        flush=True,
    )
    print(
        f"Distance metric: {info.config.params.vectors.distance}",
        flush=True,
    )

    sample, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1,
        with_payload=True,
        with_vectors=False,
    )

    print(
        "Sample payload:",
        json.dumps(sample[0].payload, indent=2) if sample else "None",
        flush=True,
    )

    # ---------------------------------------------------------
    # DIRECT RETRIEVAL TESTS
    # ---------------------------------------------------------
    print("\n--- RETRIEVAL TESTS ---", flush=True)

    for question in QUESTIONS:
        vector = model.encode(
            question,
            normalize_embeddings=True,
        ).tolist()

        hits = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=2,
        ).points

        print(f"\nQ: {question}", flush=True)

        for hit in hits:
            print(
                f"  Score: {hit.score:.4f} | "
                f"Title: {hit.payload.get('title')} | "
                f"Campus: {hit.payload.get('campus')}",
                flush=True,
            )

    # ---------------------------------------------------------
    # API CHAT LOGIC TEST WITH DIAGNOSTICS
    # ---------------------------------------------------------
    print("\n--- API CHAT LOGIC TEST ---", flush=True)

    sys.path.insert(0, os.getcwd())

    try:
        print("Step 1: Importing RAG service...", flush=True)

        from api.services.rag_service import get_rag_service

        print("Step 2: Initializing RAG service...", flush=True)
        srv = get_rag_service()

        print("Step 3: RAG service initialized.", flush=True)

        question = QUESTIONS[0]

        print("Step 4: Retrieving relevant chunks...", flush=True)
        hits = srv.retrieve(question)

        print(
            f"Step 5: Retrieved {len(hits)} chunks.",
            flush=True,
        )

        if hits:
            print("Step 6: Generating answer...", flush=True)

            answer = srv.generate_answer(question, hits)

            print(
                f"Step 7: Answer generated: "
                f"{answer['answer'][:200]}",
                flush=True,
            )
        else:
            print(
                "No relevant chunks found; skipping generation.",
                flush=True,
            )

        print("\nAPI CHAT LOGIC TEST COMPLETED.", flush=True)

    except Exception:
        print("\nAPI CHAT LOGIC TEST FAILED:", flush=True)
        traceback.print_exc()

    finally:
        client.close()


if __name__ == "__main__":
    main()
