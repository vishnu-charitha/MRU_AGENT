import json

with open('evaluation/datasets/mrdu_eval_backup.jsonl', 'r', encoding='utf-8') as f:
    content = f.read()

# The issue is that the separator is literal backslash followed by n
# which is represented in Python string as '\\n'
parts = content.split('\\n')

valid_rows = []
for p in parts:
    p = p.strip()
    if not p:
        continue
    try:
        obj = json.loads(p)
        valid_rows.append(obj)
    except json.JSONDecodeError as e:
        print(f"Error parsing: {p[:50]}...")
        print(e)

print(f"Recovered {len(valid_rows)} records")

with open('evaluation/datasets/mrdu_eval.jsonl', 'w', encoding='utf-8') as f:
    for row in valid_rows:
        f.write(json.dumps(row) + '\n')
