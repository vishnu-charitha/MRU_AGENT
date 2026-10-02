import json

with open('evaluation/results/per_question_results.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d['test_id'] == 'eval-002':
            print(f"\n--- {d['test_id']} ---")
            print(f"Gen Answer: {d['generated_answer']}")
            print(f"Ref Answer: {d['expected_answer']}")
            print(f"Faithfulness: {d.get('faithfulness')}")
            print(f"Answer Relevancy: {d.get('answer_relevancy')}")
            print(f"Contexts: {d['retrieved_contexts']}")
