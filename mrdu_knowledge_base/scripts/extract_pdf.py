
import os, json
from pypdf import PdfReader
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "raw", "pdf")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
os.makedirs(CLEANED_DIR, exist_ok=True)

def run():
    stats = {"extracted": 0, "failed": 0}
    for pdf in os.listdir(PDF_DIR):
        if not pdf.endswith('.pdf'): continue
        pdf_path = os.path.join(PDF_DIR, pdf)
        meta_path = pdf_path + ".meta"
        out_path = os.path.join(CLEANED_DIR, pdf.replace('.pdf', '_extracted.json'))
        
        if os.path.exists(out_path):
            stats["extracted"] += 1
            continue
            
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line and not line.startswith('---'):
                        k, v = line.split(':', 1)
                        meta[k.strip()] = v.strip()
                        
        try:
            reader = PdfReader(pdf_path)
            pages = []
            for i, p in enumerate(reader.pages):
                text = p.extract_text()
                pages.append({"page_number": i+1, "content": text or "", "has_text": bool(text.strip())})
                
            doc = {
                "document_id": meta.get("document_id", pdf),
                "title": meta.get("title", pdf),
                "source_url": meta.get("source_url", ""),
                "originating_page_url": meta.get("originating_page_url", ""),
                "source_id": meta.get("source_id", ""),
                "campus": meta.get("campus", ""),
                "category": meta.get("category", ""),
                "program": meta.get("program", ""),
                "regulation": meta.get("regulation", ""),
                "source_type": "official_mrdu",
                "document_type": "PDF",
                "pages": pages,
                "is_scanned": all(not p["has_text"] for p in pages),
                "retrieved_at": meta.get("retrieved_at", datetime.now().isoformat())
            }
            with open(out_path, 'w', encoding='utf-8') as f: json.dump(doc, f, indent=2)
            stats["extracted"] += 1
        except Exception as e:
            stats["failed"] += 1
    return stats

if __name__ == '__main__': run()
