
import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_JSONL = os.path.join(BASE_DIR, "data", "chunks", "mrdu_chunks.jsonl")
VAL_REPORT_JSON = os.path.join(BASE_DIR, "output", "chunk_validation_report.json")

def run():
    stats = {
        "total_chunks": 0,
        "empty_chunks": 0,
        "duplicate_chunks": 0,
        "manual_review_chunks": 0,
        "excluded_program_flagged": 0,
        "validation_errors": []
    }
    
    if not os.path.exists(CHUNKS_JSONL):
        stats["validation_errors"].append("Chunks JSONL not found")
        return stats
        
    seen_content = set()
    seen_ids = set()
    
    with open(CHUNKS_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            c = json.loads(line)
            stats["total_chunks"] += 1
            
            cid = c.get("chunk_id")
            if cid in seen_ids:
                stats["validation_errors"].append(f"Duplicate chunk ID: {cid}")
            seen_ids.add(cid)
            
            content = c.get("content", "").strip()
            if not content:
                stats["empty_chunks"] += 1
                stats["validation_errors"].append(f"Empty chunk: {cid}")
                continue
                
            if content in seen_content:
                stats["duplicate_chunks"] += 1
            seen_content.add(content)
            
            if c.get("requires_manual_review"):
                stats["manual_review_chunks"] += 1
                
            if not c.get("document_id"):
                stats["validation_errors"].append(f"Missing document_id in {cid}")
                
            content_lower = content.lower()
            if any(ex in content_lower for ex in ["mba", "bba", "bca", "mca", "ph.d", "b.sc", "b.com"]):
                stats["excluded_program_flagged"] += 1
                
    with open(VAL_REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
        
    print(f"Validation complete. Errors: {len(stats['validation_errors'])}")
    return stats

if __name__ == '__main__':
    run()
