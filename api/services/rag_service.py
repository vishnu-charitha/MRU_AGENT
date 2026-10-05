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
            self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_key, timeout=60.0)

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
            api_key=self.openrouter_key,
            timeout=60.0,
            max_retries=2
        ) if self.openrouter_key else None

    def rewrite_query(self, query: str, history: list) -> str:
        if not history or not self.llm_client:
            return query
            
        if len(history) < 2:
            return query
            
        sys_prompt = """You rewrite university-chatbot queries into standalone retrieval questions.

    Decide whether the CURRENT QUERY expresses an intent or is a follow-up fragment:
    - A complete question or topic phrase that names an information need expresses its own intent (for example, "How many seats are there in B.Tech EEE?", "fees for EEE", "eligibility for EEE", or "documents required"). Keep that intent, even if it differs from history.
    - A short entity/noun-phrase fragment without a requested information type (for example, "btech eee", "cse", "mtech", or "hostel") is a follow-up. Inherit the intent from the MOST RECENT preceding user question that clearly expressed one.

    For follow-ups and partial questions:
    - The latest clear user intent takes precedence over every older topic.
    - If the current query specifies a specialization (like "EEE") but omits the degree program (like "B.Tech"), INHERIT the degree program from the recent context unless the new query explicitly overrides it (e.g., "fee for MBA" overrides B.Tech).
    - Replace the prior entity with the entity in the current query while keeping the inherited degree context where appropriate.
    - Never turn an entity fragment into a generic request to describe the program. For example, after "fee structure", "btech eee" means "What is the fee structure for B.Tech EEE at MRDU?", not "Tell me about B.Tech EEE."

    If there is no prior intent, make a reasonable standalone question without inventing a specific topic. Preserve a complete current question unchanged unless a small clarification is needed (like adding the university name or inherited degree). Do not answer; output only the rewritten question."""
        
        messages = [{"role": "system", "content": sys_prompt}]
        
        # Keep only recent turns; the system prompt gives the latest clear user intent priority.
        recent_history = history[-4:] if len(history) > 4 else history
        for msg in recent_history:
            # Need to handle dictionary vs object depending on how it's passed
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            
            # Truncate long assistant answers so they don't dilute the query rewriter prompt
            if role == 'assistant' and len(content) > 150:
                content = content[:150] + "..."
                
            messages.append({"role": role, "content": content})
            
        messages.append({"role": "user", "content": f"New query: {query}"})
        
        try:
            resp = self.llm_client.chat.completions.create(
                model=self.openrouter_model,
                messages=messages,
                temperature=0.0,
                max_tokens=60
            )
            rewritten = resp.choices[0].message.content.strip(' "')
            if rewritten.lower().startswith("rewritten query:"):
                rewritten = rewritten.split(":", 1)[1].strip(' "')
            return rewritten if rewritten else query
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return query


    def retrieve(self, query: str, campus=None, category=None, program=None, regulation=None, limit=5):
        if not hasattr(self, 'qdrant_client'):
            logger.warning("Qdrant client not initialized. Cannot retrieve context.")
            return []

        import re
        # Basic Query Expansion
        expanded_query = query.lower()

        if any(w in expanded_query for w in ['programme', 'programmes', 'course', 'courses']):
            expanded_query += " programmes courses programme portfolio sanctioned intake undergraduate postgraduate"
        elif any(w in expanded_query for w in ['contact', 'email', 'phone', 'address']):
            expanded_query += " contact details phone email address admissions official"
            
        # Targeted Alias Expansion for MRDU terminology
        if re.search(r'\bmakeup exam(s)?\b', expanded_query):
            expanded_query += " supplementary examinations backlogs"
        if re.search(r'\bcgpa\b|\bgpa\b', expanded_query):
            expanded_query += " sgpa cgpa computation academic regulations grade points"

        vec = self.model.encode(expanded_query, normalize_embeddings=True).tolist()
        must_conditions = []
        if campus: must_conditions.append(FieldCondition(key="campus", match=MatchValue(value=campus)))
        if category: must_conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
        if program: must_conditions.append(FieldCondition(key="program", match=MatchValue(value=program)))
        if regulation: must_conditions.append(FieldCondition(key="regulation", match=MatchValue(value=regulation)))

        query_filter = Filter(must=must_conditions) if must_conditions else None

        pre_rerank_limit = max(25, limit * 5)
        hits = self.qdrant_client.query_points(
            collection_name=self.qdrant_collection,
            query=vec,
            query_filter=query_filter,
            limit=pre_rerank_limit
        ).points

        if not hits or not self.reranker:
            return hits[:limit]

        # Rerank using the expanded query so aliases are evaluated correctly
        pairs = [[expanded_query, h.payload.get('content', '')] for h in hits]
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
        if not hits or hits[0].score < -15.0:
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
You must use the provided context to answer the question, even if the context uses synonyms (e.g. "supplementary" for "makeup") or ambiguous wording (e.g. "as applicable").
If the provided context is completely irrelevant and does not contain the answer or a directly equivalent concept, explicitly state: "I couldn't find enough information in the MRDU knowledge base to answer that accurately."
Keep answers concise while retaining necessary qualifications. Focus exclusively on B.Tech and M.Tech programs.

CRITICAL INFERENCE RULES:
1. Do not add campus-specific claims unless the retrieved evidence supports them.
2. Do not introduce facts from conversational history that are absent from the retrieved context.
3. For conflicting intake figures such as 720 and 960, explain the discrepancy only when relevant and supported; do not arbitrarily choose a figure.
4. Never infer or explain discrepancies unless the provided knowledge-base context explicitly explains them.
5. Recognize standard academic synonyms (e.g., "makeup exams" are equivalent to "supplementary examinations").
6. If the context states a process is defined elsewhere (e.g., "defined in the academic regulations"), state exactly that instead of saying you couldn't find the information. Do not invent the exact formula if it's missing.
7. If the context uses ambiguous wording like "as applicable" (e.g., "GATE/merit as applicable"), explain exactly what the source says rather than claiming it as a universal requirement or refusing to answer.
8. If the user asks for information about a specific specialization (e.g., 'fee for B.Tech EEE') but the context only contains general information for the broader program (e.g., general 'B.Tech fee'), DO NOT say you cannot find the information. Instead, state the general program information (e.g., indicative B.Tech fee) and explicitly clarify that you could not find the specific specialization details.

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
            try:
                resp = self.llm_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=messages,
                    temperature=0.0
                )
                llm_answer = resp.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenRouter LLM error: {e}")
                llm_answer = "The AI service is currently unavailable. Please try again in a few moments."
                sources = []
        else:
            llm_answer = "API key missing. Unable to generate answer."

        if llm_answer.strip().startswith("I couldn't find enough information in the MRDU knowledge base"):
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
        if not hits or hits[0].score < -15.0:
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
5. Recognize standard academic synonyms (e.g., "makeup exams" are equivalent to "supplementary examinations").
6. If the context states a process is defined elsewhere (e.g., "defined in the academic regulations"), state exactly that instead of saying you couldn't find the information. Do not invent the exact formula if it's missing.
7. If the context uses ambiguous wording like "as applicable" (e.g., "GATE/merit as applicable"), explain exactly what the source says rather than claiming it as a universal requirement or refusing to answer.
8. If the user asks for information about a specific specialization (e.g., 'fee for B.Tech EEE') but the context only contains general information for the broader program (e.g., general 'B.Tech fee'), DO NOT say you cannot find the information. Instead, state the general program information (e.g., indicative B.Tech fee) and explicitly clarify that you could not find the specific specialization details.

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
            try:
                resp = self.llm_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    extra_body={"repetition_penalty": 1.1},
                    stream=True
                )
                full_answer = ""
                for chunk in resp:
                    if chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        full_answer += content_piece
                        yield json.dumps({"answer_chunk": content_piece}) + "\n"
    
                if full_answer.strip().startswith("I couldn't find enough information in the MRDU knowledge base") or full_answer.strip().startswith("This topic is out of scope"):
                    yield json.dumps({"clear_sources": True}) + "\n"
                else:
                    followups = self.generate_followup_questions(query, full_answer, history)
                    if followups:
                        yield json.dumps({"type": "followup_questions", "questions": followups}) + "\n"
            except Exception as e:
                logger.error(f"OpenRouter LLM streaming error: {e}")
                yield json.dumps({"error": "The AI service is currently unavailable. Please try again in a few moments."}) + "\n"
        else:
            yield json.dumps({"error": "API key missing. Unable to generate answer."}) + "\n"

    def generate_followup_questions(self, original_query: str, full_answer: str, history: list) -> list[str]:
        if not self.llm_client:
            return []
        
        system_prompt = """
You are an expert academic assistant for MRDU. Based on the user's last question and your answer, generate exactly 1-2 concise, context-aware follow-up questions that the user might want to ask next.
RULES:
1. Generate 1-2 short questions maximum.
2. Questions must be directly related to the current answer and MRDU's B.Tech/M.Tech programs.
3. Do not generate generic questions like "Would you like to know more?" or "Can I help with anything else?".
4. Do not invent facts or suggest unsupported questions.
5. Return ONLY a JSON object in this format: {"followups": ["Question 1", "Question 2"]}
6. If there is no meaningful follow-up, return {"followups": []}
"""
        messages = [{"role": "system", "content": system_prompt.strip()}]
        
        for msg in history[-2:]:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            messages.append({"role": role, "content": content})
            
        messages.append({"role": "user", "content": original_query})
        messages.append({"role": "assistant", "content": full_answer})
        
        try:
            resp = self.llm_client.chat.completions.create(
                model=self.openrouter_model,
                messages=messages,
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            content = resp.choices[0].message.content
            
            import re
            import json
            
            def normalize(s):
                if not s: return ""
                return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', s.lower())).strip()

            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```', '', content)
            
            parsed = json.loads(content)
            followups = parsed.get("followups", [])
            if not isinstance(followups, list):
                logger.error(f"LLM returned non-list followups: {followups}")
                return []
            
            history_texts = set()
            for msg in history:
                role = msg.role if hasattr(msg, 'role') else msg.get('role', 'user')
                txt = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                
                if role == 'user':
                    history_texts.add(normalize(txt))
                
                # Check for previous assistant followups
                fqs = msg.followUpQuestions if hasattr(msg, 'followUpQuestions') else msg.get('followUpQuestions')
                if fqs:
                    for fq in fqs:
                        history_texts.add(normalize(fq))

            history_texts.add(normalize(original_query))
            
            filtered = []
            seen = set()
            for q in followups:
                q_clean = q.strip()
                if not q_clean:
                    continue
                q_norm = normalize(q_clean)
                if q_norm not in history_texts and q_norm not in seen:
                    filtered.append(q_clean)
                    seen.add(q_norm)
            
            logger.info(f"Generated followups: {filtered[:2]}")        
            return filtered[:2]
        except Exception as e:
            logger.error(f"Error generating follow-ups: {e}")
            return []

# Global singleton
rag_service = None

def get_rag_service():
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
