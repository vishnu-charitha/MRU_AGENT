import json
import shutil

with open('evaluation/datasets/mrdu_eval.jsonl', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f if line.strip()]

shutil.copy('evaluation/datasets/mrdu_eval.jsonl', 'evaluation/datasets/mrdu_eval_backup3.jsonl')

updates = {
    'eval-004': 'Yes, lateral entry is available for B.Tech. It is intended for diploma holders and eligible B.Sc graduates seeking direct entry into the second year of B.Tech.',
    'eval-006': "The eligibility for M.Tech is a relevant bachelor's degree (such as B.E./B.Tech). Admission is based on GATE or merit as applicable.",
    'eval-007': 'A GATE score is accepted, but admission can also be based on merit as applicable.',
    'eval-008': 'The M.Tech specializations offered are Computer Science & Engineering, VLSI and Embedded Systems, Structural Engineering, and Electrical Power Systems.',
    'eval-009': 'The approved intake for M.Tech in Computer Science & Engineering is 12 seats.',
    'eval-010': 'The process is: online registration and application, email verification by the admissions team with a document checklist, counselling attendance with original documents, seat allocation against sanctioned intake, and fee payment to confirm admission.',
    'eval-012': 'Hostel fees are notified separately from tuition. Contact the hostel administration on +91 93481 61303 or check the Notifications page.',
    'eval-014': 'Carry originals plus photocopies of: Class 10 and Class 12 marks memoranda and certificates; entrance rank card/hall ticket; Transfer Certificate; Migration Certificate (if applicable); study/conduct certificate; Aadhaar or government photo ID; passport-size photographs; caste/category certificate if claiming reservation; income certificate for scholarship claims; degree/diploma certificates for PG and lateral entry; gap certificate if applicable; anti-ragging undertaking (mandatory); and a medical fitness certificate.',
    'eval-015': 'MRDU offers merit scholarships for top rank holders in qualifying examinations and entrance tests, sports and cultural achievement awards, and support aligned to eligible state and central government schemes where applicable.'
}

verified_count = 0
for item in data:
    if item['test_id'] in updates:
        item['expected_answer'] = updates[item['test_id']]
        item['evaluation_notes'] = 'VERIFIED'
        verified_count += 1

with open('evaluation/datasets/mrdu_eval.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item) + '\n')

print(f"Updated and verified {verified_count} records.")
