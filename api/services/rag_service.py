import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import openai
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("api")

class RAGService:
    def __init__(self):
        self.model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        self.qdrant_url = os.getenv('QDRANT_URL')
        self.qdrant_key = os.getenv('QDRANT_API_KEY')
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'mrdu_knowledge_base')
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_model = os.getenv('OPENROUTER_MODEL')

        if not self.qdrant_url or not self.qdrant_key:
            raise ValueError("Qdrant configuration is missing.")
        if not self.openrouter_key or not self.openrouter_model:
            raise ValueError("OpenRouter configuration is missing.")

        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        logger.info("Connecting to Qdrant...")
        self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_key)
        
        logger.info("Initializing OpenAI client for OpenRouter...")
        self.llm_client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_key
        )

    def retrieve(self, query: str, campus=None, category=None, program=None, regulation=None, limit=5):
        vec = self.model.encode(query, normalize_embeddings=True).tolist()
        must_conditions = []
        if campus: must_conditions.append(FieldCondition(key="campus", match=MatchValue(value=campus)))
        if category: must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
        if program: must_conditions.append(FieldCondition(key="program", match=MatchValue(value=program)))
        if regulation: must_conditions.append(FieldCondition(key="regulation", match=MatchValue(value=regulation)))
        
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        hits = self.qdrant_client.query_points(
            collection_name=self.qdrant_collection,
            query=vec,
            query_filter=query_filter,
            limit=limit
        )
        return hits.points

    def generate_answer(self, query: str, hits):
        # 1. Scope Guard
        query_lower = query.lower()
        if any(kw in query_lower for kw in ['mba', 'bba', 'bca', 'mca', 'unrelated university']):
            return {
                "answer": "This topic is out of scope. I can only provide information about MRDU's B.Tech and M.Tech programs.",
                "sources": []
            }
            
        # 2. Quality Threshold Guard
        if not hits or hits[0].score < 0.45:
            return {
                "answer": "I couldn't find enough information in the MRDU knowledge base to answer that accurately.",
                "sources": []
            }
            
        # 3. Grounded Context
        context_parts = []
        sources = []
        for h in hits:
            content = h.payload.get('content', '')
            title = h.payload.get('title', 'Unknown Document')
            url = h.payload.get('source_url', 'Unknown URL')
            campus = h.payload.get('campus', 'main')
            context_parts.append(f"--- Document: {title} (Campus: {campus}) ---\n{content}")
            
            # Format source output
            sources.append({
                "title": f"MRDU {title}",
                "url": url,
                "chunk_id": h.payload.get('chunk_id', ''),
                "score": round(h.score, 4)
            })
                
        context = "\n\n".join(context_parts)
        
        system_prompt = f"""
You are an expert academic assistant for MRDU (Malla Reddy Deemed to be University).
You must answer the user's question using ONLY the provided context.
CRITICAL INSTRUCTIONS:
- Do NOT hallucinate or introduce outside facts under any circumstances.
- If the context lacks sufficient information, you MUST state explicitly: "I couldn't find enough information in the MRDU knowledge base to answer that accurately."
- Distinguish clearly between the main campus and Tirupati campus if applicable.
- Respect program (B.Tech vs M.Tech) and regulation (MR20/MR22/MR24) metadata.
- Exclude MBA/BCA/MCA/BBA information.
- Provide a clear, concise answer.

Context:
{context}
"""
        # Call LLM
        logger.info(f"Calling OpenRouter model {self.openrouter_model}...")
        resp = self.llm_client.chat.completions.create(
            model=self.openrouter_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0
        )
        llm_answer = resp.choices[0].message.content
        
        if "I couldn't find enough information" in llm_answer:
            sources = []
            
        return {
            "answer": llm_answer,
            "sources": sources
        }

# Global singleton
rag_service = None

def get_rag_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
