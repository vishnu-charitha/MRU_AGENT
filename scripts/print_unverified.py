import json
with open('evaluation/datasets/mrdu_eval.jsonl', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f if line.strip()]

unverified = [d for d in data if d.get('evaluation_notes') != 'VERIFIED']
for d in unverified[:15]:
    print(f"{d['test_id']}: {d['question']}")
