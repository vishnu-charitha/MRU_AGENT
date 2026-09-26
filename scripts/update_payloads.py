import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()
qdrant_url = os.getenv('QDRANT_URL')
qdrant_key = os.getenv('QDRANT_API_KEY')
client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
collection = 'mrdu_knowledge_base'

offset = None
updated = 0
while True:
    points, offset = client.scroll(collection_name=collection, limit=100, offset=offset)
    if not points: break
    
    ids = [p.id for p in points]
    client.set_payload(
        collection_name=collection,
        payload={
            'source_url': 'https://mrdu.edu.in',
            'source_file': 'MRDU_Chatbot_Knowledge_Base_100pages.md'
        },
        points=ids
    )
    updated += len(ids)
    if offset is None: break

print(f'Successfully updated {updated} point payloads.')
