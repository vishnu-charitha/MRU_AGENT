import json
import shutil

with open('evaluation/datasets/mrdu_eval.jsonl', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f if line.strip()]

shutil.copy('evaluation/datasets/mrdu_eval.jsonl', 'evaluation/datasets/mrdu_eval_backup4.jsonl')

updates = {
    'eval-016': 'MRDU follows an Outcome-Based Education (OBE) grade system with credit-weighted evaluation under the Choice Based Credit System (CBCS). Letter grades, grade points and SGPA/CGPA computation are defined in the academic regulations for each specific batch regulation code.',
    'eval-017': 'A minimum attendance percentage is required for examination eligibility, with shortfalls addressed through condonation as per regulation. The exact threshold (commonly 75%) is printed in the academic regulations for your batch.',
    'eval-018': 'Yes, end-semester examinations are held in regular, supplementary and advanced supplementary modes.',
    'eval-024': 'Dr. K. Vasanth Kumar is the Professor & Head of the Department of Computer Science & Engineering.'
}

verified_count = 0
needs_review_count = 0
for item in data:
    if item['test_id'] in updates:
        item['expected_answer'] = updates[item['test_id']]
        item['evaluation_notes'] = 'VERIFIED'

    if item.get('evaluation_notes') == 'VERIFIED':
        verified_count += 1
    else:
        needs_review_count += 1

with open('evaluation/datasets/mrdu_eval.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item) + '\n')

print(f"Update complete. Total VERIFIED: {verified_count}. Total NEEDS_REVIEW: {needs_review_count}.")
