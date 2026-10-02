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
        self.openrouter_model = os.getenv('OPENROUTER_MODEL', 'google/gemma-4-31b-it')

        if not self.qdrant_url or not self.qdrant_key:
            logger.warning("Qdrant configuration is missing.")
        else:
            logger.info("Connecting to Qdrant...")
            self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_key)

        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        self.reranker_model_name = os.getenv('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker model: {self.reranker_model_name}")
            self.reranker = CrossEncoder(self.reranker_model_name)
        except Exception as e:
            logger.warning(f"Could not load reranker: {e}. Falling back to default retrieval.")
            self.reranker = None

        if not self.openrouter_key:
            logger.warning("OpenRouter configuration is missing.")

        logger.info("Initializing OpenAI client for OpenRouter...")
        self.llm_client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_key
        ) if self.openrouter_key else None

    def retrieve(self, query: str, campus=None, category=None, program=None, regulation=None, limit=5):
        if not hasattr(self, 'qdrant_client'):
            logger.warning("Qdrant client not initialized. Cannot retrieve context.")
            return []

        # Basic Query Expansion
        expanded_query = query.lower()
        if any(w in expanded_query for w in ['programme', 'programmes', 'course', 'courses']):
            expanded_query += " programmes courses programme portfolio sanctioned intake undergraduate postgraduate"
        elif any(w in expanded_query for w in ['contact', 'email', 'phone', 'address']):
            expanded_query += " contact details phone email address admissions official"

        vec = self.model.encode(expanded_query, normalize_embeddings=True).tolist()
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
            limit=limit * 3  # Fetch more for reranking
        ).points

        if not hits or not self.reranker:
            return hits[:limit]

        # Rerank
        pairs = [[query, h.payload.get('content', '')] for h in hits]
        scores = self.reranker.predict(pairs)

        # Assign cross-encoder scores and sort
        for h, score in zip(hits, scores):
            h.score = float(score)

        hits.sort(key=lambda x: x.score, reverse=True)
        return hits[:limit]

    def generate_answer(self, query: str, hits, history=None):
        if history is None:
            history = []

        # 1. Scope Guard (preserved)
        query_lower = query.lower()
        if any(kw in query_lower for kw in ['mba', 'bba', 'bca', 'mca', 'unrelated university']):
            return {
                "answer": "This topic is out of scope. I can only provide information about MRDU's B.Tech and M.Tech programs.",
                "sources": []
            }

        # 2. Quality Threshold Guard
        if not hits or hits[0].score < 0.40:
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
Answer the user's specific question directly using ONLY the provided context.
If the context does not contain the answer, explicitly state: "I couldn't find enough information in the MRDU knowledge base to answer that accurately."
Keep answers concise while retaining necessary qualifications. Focus exclusively on B.Tech and M.Tech programs.

CRITICAL INFERENCE RULES:
1. Do not add campus-specific claims unless the retrieved evidence supports them.
2. Do not introduce facts from conversational history that are absent from the retrieved context.
3. For conflicting intake figures such as 720 and 960, explain the discrepancy only when relevant and supported; do not arbitrarily choose a figure.
4. Never infer or explain discrepancies unless the provided knowledge-base context explicitly explains them.

FORMATTING RULES:
1. Use standard Markdown syntax (e.g., **text** for bold, - item for lists).
2. Never output literal backslashes before Markdown characters. Do not escape Markdown syntax.

Context:
{context}
"""

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": query})

        if self.llm_client:
            logger.info(f"Calling OpenRouter model {self.openrouter_model}...")
            resp = self.llm_client.chat.completions.create(
                model=self.openrouter_model,
                messages=messages,
                temperature=0.0
            )
            llm_answer = resp.choices[0].message.content
        else:
            llm_answer = "API key missing. Unable to generate answer."

        if llm_answer.strip().startswith("I couldn't find enough information"):
            sources = []

        return {
            "answer": llm_answer,
            "sources": sources
        }

    def generate_answer_stream(self, query: str, hits, history=None):
        import json
        if history is None:
            history = []

        # 1. Scope Guard (preserved)
        query_lower = query.lower()
        if any(kw in query_lower for kw in ['mba', 'bba', 'bca', 'mca', 'unrelated university']):
            yield json.dumps({"answer": "This topic is out of scope. I can only provide information about MRDU's B.Tech and M.Tech programs.", "sources": []}) + "\n"
            return

        # 2. Quality Threshold Guard
        if not hits or hits[0].score < 0.40:
            yield json.dumps({"answer": "I couldn't find enough information in the MRDU knowledge base to answer that accurately.", "sources": []}) + "\n"
            return

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
Answer the user's specific question directly using ONLY the provided context.
If the context does not contain the answer, explicitly state: "I couldn't find enough information in the MRDU knowledge base to answer that accurately."
Keep answers concise while retaining necessary qualifications. Focus exclusively on B.Tech and M.Tech programs.

CRITICAL INFERENCE RULES:
1. Do not add campus-specific claims unless the retrieved evidence supports them.
2. Do not introduce facts from conversational history that are absent from the retrieved context.
3. For conflicting intake figures such as 720 and 960, explain the discrepancy only when relevant and supported; do not arbitrarily choose a figure.
4. Never infer or explain discrepancies unless the provided knowledge-base context explicitly explains them.

FORMATTING RULES:
1. Use standard Markdown syntax (e.g., **text** for bold, - item for lists).
2. Never output literal backslashes before Markdown characters. Do not escape Markdown syntax.

Context:
{context}
"""

        yield json.dumps({"sources": sources}) + "\n"

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": query})

        if self.llm_client:
            logger.info(f"Calling OpenRouter model {self.openrouter_model} with stream=True...")
            resp = self.llm_client.chat.completions.create(
                model=self.openrouter_model,
                messages=messages,
                temperature=0.1,
                extra_body={"repetition_penalty": 1.1},
                stream=True
            )
            full_answer = ""
            for chunk in resp:
                if chunk.choices[0].delta.content:
                    content_piece = chunk.choices[0].delta.content
                    full_answer += content_piece
                    yield json.dumps({"answer_chunk": content_piece}) + "\n"

            if full_answer.strip().startswith("I couldn't find enough information"):
                yield json.dumps({"clear_sources": True}) + "\n"

        else:
            yield json.dumps({"answer": "API key missing. Unable to generate answer."}) + "\n"

# Global singleton
rag_service = None

def get_rag_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
