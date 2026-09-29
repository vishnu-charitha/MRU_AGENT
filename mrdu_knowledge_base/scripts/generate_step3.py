import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

def write_script(name, content):
    with open(os.path.join(SCRIPTS_DIR, name), 'w', encoding='utf-8') as f:
        f.write(content)

collect_web_py = r"""
import os, csv, json, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_CSV = os.path.join(BASE_DIR, "config", "sources.csv")
WEB_DIR = os.path.join(BASE_DIR, "data", "raw", "web")
PDF_DIR = os.path.join(BASE_DIR, "data", "raw", "pdf")
REPORT_JSON = os.path.join(BASE_DIR, "output", "collection_report.json")
FAILED_JSONL = os.path.join(BASE_DIR, "output", "failed_sources.jsonl")

os.makedirs(WEB_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0"
PDF_RELEVANT = ["regulation", "syllabus", "timetabl", "exam", "circular", "question paper", "policy", "admiss", "fee", "notification"]

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "aside"]):
        tag.decompose()
    return soup

def run():
    report = {"timestamp": datetime.now().isoformat(), "total_sources": 0, "successful_sources": 0, "failed_sources": 0, "skipped_sources": 0, "pdfs_discovered": 0, "pdfs_downloaded": 0, "pdfs_failed": 0, "errors": []}
    failed = []
    
    with open(SOURCES_CSV, "r", encoding="utf-8") as f:
        sources = list(csv.DictReader(f))
    report["total_sources"] = len(sources)
    
    for row in sources:
        action = row.get("action", "").strip().upper()
        if action not in ["INCLUDE", "FILTER", "VERIFY", "OPTIONAL-FILTER"]:
            report["skipped_sources"] += 1
            continue
            
        url = row.get("url", "").strip()
        source_id = row.get("source_id", "unknown").strip()
        md_filename = f"source_{source_id.zfill(3)}.md"
        md_path = os.path.join(WEB_DIR, md_filename)
        
        if os.path.exists(md_path):
            report["successful_sources"] += 1
            continue
            
        try:
            print(f"Fetching {url}")
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            resp.raise_for_status()
            soup = clean_html(resp.text)
            title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
            
            lines = []
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table', 'a']):
                if element.name.startswith('h'): lines.append(f"{'#' * int(element.name[1])} {element.get_text(strip=True)}")
                elif element.name == 'p': lines.append(element.get_text(strip=True))
                elif element.name in ['ul', 'ol']:
                    for li in element.find_all('li', recursive=False): lines.append(f"- {li.get_text(strip=True)}")
                elif element.name == 'a':
                    href = element.get('href')
                    if href:
                        abs_url = urljoin(url, href)
                        text = element.get_text(strip=True)
                        lines.append(f"[{text}]({abs_url})")
                        if abs_url.lower().endswith('.pdf'):
                            report["pdfs_discovered"] += 1
                            if any(k in abs_url.lower() or k in text.lower() for k in PDF_RELEVANT):
                                try:
                                    pdf_index = report["pdfs_downloaded"] + 1
                                    pdf_path = os.path.join(PDF_DIR, f"source_{source_id}_document_{pdf_index}.pdf")
                                    if not os.path.exists(pdf_path):
                                        p_resp = requests.get(abs_url, headers={"User-Agent": USER_AGENT}, timeout=10)
                                        p_resp.raise_for_status()
                                        with open(pdf_path, 'wb') as pf: pf.write(p_resp.content)
                                        meta = f"---\ndocument_id: MRDU-PDF-{source_id}-{pdf_index}\nsource_id: {source_id}\ntitle: {text}\nsource_url: {abs_url}\noriginating_page_url: {url}\ncategory: {row.get('category','')}\nsubcategory: {row.get('subcategory','')}\nprogram: {row.get('program','')}\nregulation: {row.get('regulation','')}\ncampus: {row.get('campus','')}\nsource_type: PDF\ndata_type: PDF\nretrieved_at: {datetime.now().isoformat()}\n---\n"
                                        with open(f"{pdf_path}.meta", 'w', encoding='utf-8') as pmf: pmf.write(meta)
                                    report["pdfs_downloaded"] += 1
                                except Exception as e:
                                    report["pdfs_failed"] += 1
                                    report["errors"].append(str(e))
            
            meta_header = f"---\ndocument_id: MRDU-WEB-{source_id.zfill(3)}\nsource_id: {source_id}\ntitle: {title}\nsource_url: {url}\noriginating_page_url: {url}\ncategory: {row.get('category', '')}\nsubcategory: {row.get('subcategory', '')}\nprogram: {row.get('program', '')}\nregulation: {row.get('regulation', '')}\ncampus: {row.get('campus', '')}\nsource_type: Web\ndata_type: HTML\nretrieved_at: {datetime.now().isoformat()}\n---\n\n"
            with open(md_path, 'w', encoding='utf-8') as mf:
                mf.write(meta_header + "\n\n".join([line for line in lines if line]))
            report["successful_sources"] += 1
        except Exception as e:
            report["failed_sources"] += 1
            row["error"] = str(e)
            failed.append(row)
            
    with open(REPORT_JSON, 'w', encoding='utf-8') as f: json.dump(report, f, indent=2)
    with open(FAILED_JSONL, 'w', encoding='utf-8') as f:
        for fs in failed: f.write(json.dumps(fs) + "\n")
    return report

if __name__ == '__main__': run()
"""

extract_pdf_py = r"""
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
"""

clean_text_py = r"""
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
"""

filter_scope_py = r"""
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
"""

validate_dataset_py = r"""
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
"""

build_dataset_py = r"""
import os, json
import collect_web
import extract_pdf
import clean_text
import filter_scope
import validate_dataset

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_JSON = os.path.join(BASE_DIR, "output", "step3_report.json")

def main():
    print("Running collect_web...")
    col_stats = collect_web.run()
    print("Running extract_pdf...")
    ext_stats = extract_pdf.run()
    print("Running clean_text...")
    cln_stats = clean_text.run()
    print("Running filter_scope...")
    flt_stats = filter_scope.run()
    print("Running validate_dataset...")
    val_stats = validate_dataset.run()
    
    report = {
        "manifest_source_count": col_stats.get("total_sources"),
        "successful_webpages": col_stats.get("successful_sources"),
        "pdfs_discovered": col_stats.get("pdfs_discovered"),
        "pdfs_downloaded": col_stats.get("pdfs_downloaded"),
        "pdfs_extracted": ext_stats.get("extracted"),
        "pdfs_failed_extraction": ext_stats.get("failed"),
        "cleaned_documents": cln_stats.get("cleaned_web") + ext_stats.get("extracted"),
        "retained_final_records": flt_stats.get("retained"),
        "rejected_records": flt_stats.get("rejected"),
        "manual_review_records": flt_stats.get("manual_review"),
        "validation_issues": val_stats.get("issues"),
        "active_project_directory": BASE_DIR,
        "step3_report_location": REPORT_JSON
    }
    
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
"""

write_script("collect_web.py", collect_web_py)
write_script("extract_pdf.py", extract_pdf_py)
write_script("clean_text.py", clean_text_py)
write_script("filter_scope.py", filter_scope_py)
write_script("validate_dataset.py", validate_dataset_py)
write_script("build_dataset.py", build_dataset_py)

print("Generated scripts")
