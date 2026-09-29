
import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL_JSONL = os.path.join(BASE_DIR, "data", "final", "mrdu_knowledge_base.jsonl")

def run():
    stats = {"valid": 0, "invalid": 0, "issues": []}
    if not os.path.exists(FINAL_JSONL):
        stats["issues"].append("Final JSONL not found")
        return stats
        
    with open(FINAL_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line)
            if not doc.get("source_url"):
                stats["invalid"] += 1
                stats["issues"].append(f"Missing source_url in {doc.get('document_id')}")
            else:
                stats["valid"] += 1
    return stats

if __name__ == '__main__': run()
