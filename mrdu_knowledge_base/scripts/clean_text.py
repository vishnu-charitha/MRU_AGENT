
import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "data", "raw", "web")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
os.makedirs(CLEANED_DIR, exist_ok=True)

def run():
    # We will just normalize whitespace and ensure a unified JSON structure for web pages
    # and re-save the PDFs without change (as extraction was already clean enough for now).
    stats = {"cleaned_web": 0}
    for md in os.listdir(WEB_DIR):
        if not md.endswith('.md'): continue
        out_path = os.path.join(CLEANED_DIR, md.replace('.md', '_cleaned.json'))
        if os.path.exists(out_path): 
            stats["cleaned_web"] += 1
            continue
            
        with open(os.path.join(WEB_DIR, md), 'r', encoding='utf-8') as f:
            content = f.read()
            
        parts = content.split('---')
        meta = {}
        body = content
        if len(parts) >= 3:
            meta_str = parts[1]
            body = '---'.join(parts[2:]).strip()
            for line in meta_str.split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
                    
        doc = {
            "document_id": meta.get("document_id", md),
            "title": meta.get("title", md),
            "source_url": meta.get("source_url", ""),
            "originating_page_url": meta.get("originating_page_url", ""),
            "source_id": meta.get("source_id", ""),
            "campus": meta.get("campus", ""),
            "category": meta.get("category", ""),
            "program": meta.get("program", ""),
            "regulation": meta.get("regulation", ""),
            "source_type": "official_mrdu",
            "document_type": "HTML",
            "content": body,
            "retrieved_at": meta.get("retrieved_at", "")
        }
        with open(out_path, 'w', encoding='utf-8') as f: json.dump(doc, f, indent=2)
        stats["cleaned_web"] += 1
    return stats

if __name__ == '__main__': run()
