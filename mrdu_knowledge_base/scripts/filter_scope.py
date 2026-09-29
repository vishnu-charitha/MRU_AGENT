
import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
FINAL_DIR = os.path.join(BASE_DIR, "data", "final")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(FINAL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_JSONL = os.path.join(FINAL_DIR, "mrdu_knowledge_base.jsonl")
REJECTED_JSONL = os.path.join(OUTPUT_DIR, "rejected_documents.jsonl")

EXCLUDED = ["mba", "bba", "bca", "mca", "ph.d", "b.sc", "b.com"]

def run():
    stats = {"retained": 0, "rejected": 0, "manual_review": 0}
    retained_docs = []
    rejected_docs = []
    
    for f in os.listdir(CLEANED_DIR):
        if not f.endswith('.json'): continue
        with open(os.path.join(CLEANED_DIR, f), 'r', encoding='utf-8') as jf:
            doc = json.load(jf)
            
        full_text = doc.get("content", "").lower()
        if "pages" in doc:
            full_text = " ".join([p.get("content", "").lower() for p in doc["pages"]])
            
        rejected = False
        reason = ""
        
        # Simple scope exclusion (If it exclusively talks about MBA and not B.Tech)
        if any(ex in full_text for ex in EXCLUDED) and not any(inc in full_text for inc in ["b.tech", "m.tech", "university"]):
            rejected = True
            reason = "Only contains excluded programs"
            
        if rejected:
            doc["reject_reason"] = reason
            rejected_docs.append(doc)
            stats["rejected"] += 1
        else:
            if any(ex in full_text for ex in EXCLUDED):
                doc["requires_manual_review"] = True
                stats["manual_review"] += 1
            else:
                doc["requires_manual_review"] = False
            retained_docs.append(doc)
            stats["retained"] += 1
            
    with open(FINAL_JSONL, 'w', encoding='utf-8') as out:
        for d in retained_docs: out.write(json.dumps(d) + "\n")
        
    with open(REJECTED_JSONL, 'w', encoding='utf-8') as out:
        for d in rejected_docs: out.write(json.dumps(d) + "\n")
        
    return stats

if __name__ == '__main__': run()
