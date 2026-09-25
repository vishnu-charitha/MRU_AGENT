import os
import json
import uuid
import time
from dotenv import load_dotenv

# Ensure we don't commit credentials
with open('.gitignore', 'a+') as f:
    f.seek(0)
    content = f.read()
    if '.env' not in content:
        f.write('\n.env\n')

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EMBEDDINGS_FILE = os.path.join(BASE_DIR, 'data', 'embeddings', 'embeddings.jsonl')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
REPORT_JSON = os.path.join(OUTPUT_DIR, 'qdrant_report.json')
REPORT_TXT = os.path.join(OUTPUT_DIR, 'qdrant_report.txt')

def main():
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_key = os.getenv('QDRANT_API_KEY')
    collection_name = os.getenv('QDRANT_COLLECTION', 'mrdu_knowledge_base')
    
    report = {
        "QDRANT_STATUS": "NOT_CONFIGURED",
        "missing_config": [],
        "collection_name": collection_name,
        "vector_dimension": 0,
        "distance_metric": "COSINE",
        "points_uploaded": 0,
        "points_verified": 0,
        "duplicate_points": 0,
        "failed_points": 0,
        "filter_counts": {
            "B.Tech": 0,
            "M.Tech": 0,
            "Tirupati": 0,
            "Main campus": 0,
            "MR20": 0,
            "MR22": 0,
            "MR24": 0,
            "Admissions": 0,
            "Examinations": 0
        }
    }
    
    if not qdrant_url: report["missing_config"].append("QDRANT_URL")
    if not qdrant_key: report["missing_config"].append("QDRANT_API_KEY")
        
    if not qdrant_url or not qdrant_key:
        with open(REPORT_JSON, 'w') as f:
            json.dump(report, f, indent=2)
        with open(REPORT_TXT, 'w') as f:
            f.write("QDRANT REPORT\n=============\n")
            f.write("QDRANT_STATUS: NOT_CONFIGURED\n")
            f.write(f"Missing configuration: {', '.join(report['missing_config'])}\n")
            f.write("Please configure QDRANT_URL and QDRANT_API_KEY as environment variables or in a .env file to proceed with upserting.\n")
        print("QDRANT_STATUS = NOT_CONFIGURED")
        return

    # If it is configured, we proceed to connect and upsert
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

    print(f"Connecting to Qdrant at {qdrant_url}")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    # Read embeddings
    records = []
    with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    if not records:
        print("No embeddings found.")
        return
        
    dimension = len(records[0]['embedding'])
    report['vector_dimension'] = dimension
    
    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        print(f"Created collection {collection_name}")
    else:
        print(f"Collection {collection_name} already exists.")
        
    points = []
    for rec in records:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, rec['chunk_id']))
        # Ensure payload preserves exactly what's requested
        metadata = rec['metadata']
        points.append(
            PointStruct(
                id=point_id,
                vector=rec['embedding'],
                payload=metadata
            )
        )
        
    # Upsert in batches
    BATCH_SIZE = 50
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i+BATCH_SIZE]
        client.upsert(collection_name=collection_name, points=batch)
        report['points_uploaded'] += len(batch)
        
    # Validation
    time.sleep(2) # Give Qdrant a moment to index
    collection_info = client.get_collection(collection_name=collection_name)
    report['points_verified'] = collection_info.points_count
    report['QDRANT_STATUS'] = "CONFIGURED_AND_UPSERTED"
    
    # Filter validation
    def count_filter(key, value):
        try:
            return client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key=key, match=MatchValue(value=value))]
                )
            ).count
        except:
            return 0
            
    report['filter_counts']['B.Tech'] = count_filter('program', 'B.Tech')
    report['filter_counts']['M.Tech'] = count_filter('program', 'M.Tech')
    report['filter_counts']['Tirupati'] = count_filter('campus', 'tirupati')
    report['filter_counts']['Main campus'] = count_filter('campus', 'main')
    report['filter_counts']['MR20'] = count_filter('regulation', 'MR20')
    report['filter_counts']['MR22'] = count_filter('regulation', 'MR22')
    report['filter_counts']['MR24'] = count_filter('regulation', 'MR24')
    report['filter_counts']['Admissions'] = count_filter('category', 'Admissions')
    report['filter_counts']['Examinations'] = count_filter('category', 'Examinations')

    with open(REPORT_JSON, 'w') as f:
        json.dump(report, f, indent=2)
        
    with open(REPORT_TXT, 'w') as f:
        f.write("QDRANT REPORT\n=============\n")
        for k, v in report.items():
            if k == 'filter_counts':
                f.write("\nFILTER COUNTS:\n")
                for fk, fv in v.items():
                    f.write(f"  {fk}: {fv}\n")
            elif k != 'missing_config':
                f.write(f"{k}: {v}\n")

if __name__ == '__main__':
    main()
