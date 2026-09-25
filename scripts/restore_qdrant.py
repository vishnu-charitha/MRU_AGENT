import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance, PointStruct
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

def restore_qdrant():
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_key = os.getenv('QDRANT_API_KEY')
    qdrant_collection = os.getenv('QDRANT_COLLECTION', 'mrdu_knowledge_base')

    if not qdrant_url or not qdrant_key:
        print("Missing Qdrant configuration in .env")
        sys.exit(1)

    print("Connecting to Qdrant Cloud...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)

    print("Listing collections:")
    try:
        collections = client.get_collections().collections
        found = False
        for col in collections:
            print(f"- {col.name}")
            if col.name == qdrant_collection:
                found = True
        
        if found:
            print(f"Collection {qdrant_collection} found. Point count: {client.get_collection(qdrant_collection).points_count}")
        else:
            print(f"\nCollection {qdrant_collection} NOT FOUND. Proceeding with restoration...")
            
            # Read embeddings
            embeddings_file = os.path.join(os.path.dirname(__file__), "..", "data", "embeddings", "embeddings.jsonl")
            if not os.path.exists(embeddings_file):
                print(f"Embeddings file not found: {embeddings_file}")
                sys.exit(1)
                
            print(f"Creating collection {qdrant_collection} (Dimension: 384, Distance: COSINE)")
            client.create_collection(
                collection_name=qdrant_collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            
            print("Creating payload indexes...")
            client.create_payload_index(qdrant_collection, "program", field_type="keyword")
            client.create_payload_index(qdrant_collection, "regulation", field_type="keyword")
            client.create_payload_index(qdrant_collection, "campus", field_type="keyword")
            client.create_payload_index(qdrant_collection, "category", field_type="keyword")
            
            points = []
            print(f"Loading data from {embeddings_file}")
            with open(embeddings_file, 'r', encoding='utf-8') as f:
                for idx, line in enumerate(f):
                    data = json.loads(line)
                    points.append(PointStruct(
                        id=idx,
                        vector=data["embedding"],
                        payload=data["metadata"]
                    ))
            
            print(f"Uploading {len(points)} points...")
            client.upsert(
                collection_name=qdrant_collection,
                points=points
            )
            
            # Verify
            count = client.get_collection(qdrant_collection).points_count
            print(f"\nRestoration Complete. Verified points in collection: {count}")

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    restore_qdrant()
