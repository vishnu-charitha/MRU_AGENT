import json
from api.services.rag_service import get_rag_service

service = get_rag_service()

questions = []
with open('evaluation/datasets/mrdu_eval.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            questions.append(json.loads(line))

report = "# Verification Report\n\n"

for q in questions:
    qid = q['test_id']
    question = q['question']
    hits = service.retrieve(question, limit=3)

    report += f"## {qid}: {question}\n"

    if not hits:
        report += "- **Status**: Flagged for verification (No relevant chunks found in DB)\n"
        report += "- **Reference Answer**: NEEDS REVIEW\n\n"
        continue

    # Get top hit
    best_hit = hits[0].payload
    section = best_hit.get('section', 'General')
    title = best_hit.get('title', 'General Info')
    content = best_hit.get('content', '')

    # Try to generate an answer
    ans = service.generate_answer(question, hits)

    report += f"- **Source Section**: {section} / {title}\n"
    report += f"- **Proposed Reference Answer**: {ans['answer']}\n"
    report += f"- **Evidence**: {content[:200]}...\n"
    report += f"- **Status**: Review needed to confirm accuracy\n\n"

with open('evaluation/results/verification_report.md', 'w', encoding='utf-8') as f:
    f.write(report)

print("Report generated.")
