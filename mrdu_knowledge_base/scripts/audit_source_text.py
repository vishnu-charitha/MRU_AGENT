import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL_JSONL = os.path.join(BASE_DIR, "data", "final", "mrdu_knowledge_base.jsonl")
AUDIT_JSON = os.path.join(BASE_DIR, "output", "source_text_audit.json")

def run():
    audit = {
        "total_records": 0,
        "empty_records_count": 0,
        "text_rich_records_count": 0,
        "empty_records": [],
        "text_rich_records": []
    }
    
    with open(FINAL_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line)
            audit["total_records"] += 1
            
            content = doc.get("content", "")
            if not content and "pages" in doc:
                content = "".join([p.get("content", "") for p in doc["pages"]])
                
            record_info = {
                "document_id": doc.get("document_id"),
                "title": doc.get("title"),
                "source_url": doc.get("source_url"),
                "category": doc.get("category"),
                "program": doc.get("program"),
                "regulation": doc.get("regulation"),
                "campus": doc.get("campus"),
                "document_type": doc.get("document_type"),
                "is_scanned": doc.get("is_scanned", False)
            }
            
            if not content.strip():
                audit["empty_records_count"] += 1
                record_info["reason"] = "Scanned PDF or unextractable text" if doc.get("is_scanned") else "Missing extraction or mapping"
                audit["empty_records"].append(record_info)
            else:
                audit["text_rich_records_count"] += 1
                audit["text_rich_records"].append(record_info)
                
    with open(AUDIT_JSON, 'w', encoding='utf-8') as f:
        json.dump(audit, f, indent=2)
        
    print(f"Audit complete. Total: {audit['total_records']}, Empty: {audit['empty_records_count']}, Rich: {audit['text_rich_records_count']}")

if __name__ == '__main__':
    run()
