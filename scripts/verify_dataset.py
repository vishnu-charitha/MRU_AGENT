import json
import os
import shutil
from dotenv import load_dotenv
load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Setup OpenAI
openai_key = os.getenv("OPENROUTER_API_KEY")
llm = ChatOpenAI(
    api_key=openai_key,
    base_url="https://openrouter.ai/api/v1",
    model=os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it"),
    temperature=0,
    max_retries=1,
    timeout=15.0
)

client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))
model = SentenceTransformer('all-MiniLM-L6-v2')

# Load dataset
data = []
with open('evaluation/datasets/mrdu_eval.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

verified_count = 0
partial_count = 0
unresolved_count = 0

for item in data:
    q = item['question']

    vec = model.encode(q, normalize_embeddings=True).tolist()
    hits = client.query_points(collection_name='mrdu_knowledge_base_v2', query=vec, limit=5).points

    if not hits:
        item['expected_answer'] = "DRAFT_ANSWER_REQUIRES_VERIFICATION"
        item['evaluation_notes'] = "NEEDS_REVIEW: No relevant context found."
        unresolved_count += 1
        continue

    contexts = "\n\n---\n\n".join([f"Source: {h.payload.get('section')} - {h.payload.get('title')}\nContent: {h.payload.get('content')}" for h in hits])

    sys_prompt = """You are verifying ground truth answers for an evaluation dataset.
Given the provided snippets from the official knowledge base, answer the user's question CONCISELY (1-3 sentences max).
CRITICAL RULES:
1. ONLY use the provided context.
2. If the context does not fully answer the question, output EXACTLY the word: NEEDS_REVIEW
3. Do not guess or invent policies, fees, or requirements.
4. Keep Tirupati and Main campus facts explicitly separate.
"""

    try:
        resp = llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Context:\n{contexts}\n\nQuestion: {q}")
        ])
        ans = resp.content.strip()
    except Exception as e:
        print(f"Error on {q}: {e}")
        ans = "NEEDS_REVIEW"

    print(f"Processed: {q[:50]}... -> {'VERIFIED' if 'NEEDS_REVIEW' not in ans else 'NEEDS_REVIEW'}")

    if "NEEDS_REVIEW" in ans or "I couldn't find" in ans or "I cannot answer" in ans:
        item['expected_answer'] = "DRAFT_ANSWER_REQUIRES_VERIFICATION"
        item['evaluation_notes'] = "NEEDS_REVIEW: Insufficient or ambiguous evidence."
        unresolved_count += 1
    else:
        # Verified
        item['expected_answer'] = ans
        item['evaluation_notes'] = "VERIFIED: Auto-verified against local knowledge base."
        item['expected_source_urls'] = [hits[0].payload.get('source_url', '')]
        item['expected_document_ids'] = [hits[0].payload.get('source_file', '')]
        item['relevant_contexts'] = [h.payload.get('content', '') for h in hits]
        item['best_hit_title'] = hits[0].payload.get('title', '')
        item['best_hit_section'] = hits[0].payload.get('section', '')
        item['best_hit_campus'] = hits[0].payload.get('campus', '')
        verified_count += 1

# Backup original
import shutil
shutil.copy('evaluation/datasets/mrdu_eval.jsonl', 'evaluation/datasets/mrdu_eval_backup.jsonl')

with open('evaluation/datasets/mrdu_eval.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item) + '\n')

# Generate Markdown Report
report = "# Dataset Verification Report\n\n"
report += f"- Total Records: {len(data)}\n"
report += f"- Verified: {verified_count}\n"
report += f"- Needs Review / Unsupported: {unresolved_count}\n\n"

for item in data:
    report += f"### ID: {item.get('test_id', 'Unknown')}\n"
    report += f"- **Question**: {item['question']}\n"
    report += f"- **Status**: {item.get('evaluation_notes', '')}\n"
    if "VERIFIED" in item.get('evaluation_notes', ''):
        report += f"- **Ground Truth**: {item['expected_answer']}\n"
        report += f"- **Source Document**: {item.get('best_hit_title', '')} ({item.get('best_hit_campus', '')} campus)\n"
        report += f"- **Evidence Excerpt**: {item.get('relevant_contexts', [''])[0][:200]}...\n"
    report += "\n"

with open('evaluation/results/verification_report.md', 'w', encoding='utf-8') as f:
    f.write(report)

print(f"Total: {len(data)}")
print(f"Verified: {verified_count}")
print(f"Unresolved: {unresolved_count}")
