
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
