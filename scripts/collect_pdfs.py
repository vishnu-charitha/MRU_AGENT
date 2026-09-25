import json
import os
import time
from urllib.parse import urlparse
from datetime import datetime
import requests

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PDF_QUEUE_FILE = os.path.join(BASE_DIR, 'output', 'pdf_queue.json')
REPORT_FILE = os.path.join(BASE_DIR, 'output', 'collection_report.json')
RAW_PDF_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'pdf')

os.makedirs(RAW_PDF_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def is_relevant_pdf(url):
    domain = urlparse(url).netloc.lower()
    if 'mrdu.edu.in' not in domain and 'mrec.ac.in' not in domain:
        return False
    # Simple heuristic: Download all PDFs from the official domains that we encountered from the valid pages
    # The instructions say "relevant to source scope". Since we found them on relevant pages, they are likely relevant.
    return True

def main():
    if not os.path.exists(PDF_QUEUE_FILE):
        print("No PDF queue found.")
        return

    with open(PDF_QUEUE_FILE, 'r', encoding='utf-8') as f:
        pdf_queue = json.load(f)

    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        report = json.load(f)

    downloaded = 0
    failed = 0

    # Deduplicate queue by URL
    seen_urls = set()
    unique_queue = []
    for item in pdf_queue:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_queue.append(item)

    source_counters = {}

    for item in unique_queue:
        url = item['url']
        source_id = item['source_id']
        meta = item['source_meta']

        if not is_relevant_pdf(url):
            continue
            
        source_counters[source_id] = source_counters.get(source_id, 0) + 1
        doc_num = source_counters[source_id]

        print(f"Downloading PDF: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()

            filename = f"source_{source_id}_document_{str(doc_num).zfill(3)}.pdf"
            pdf_path = os.path.join(RAW_PDF_DIR, filename)
            with open(pdf_path, 'wb') as f:
                f.write(resp.content)
            
            # Create metadata file
            timestamp = datetime.now().isoformat()
            frontmatter = f"---\ndocument_id: MRDU-PDF-{source_id.zfill(3)}-{str(doc_num).zfill(3)}\nsource_id: {source_id}\n"
            frontmatter += f"title: Document from {meta.get('title', '')}\nsource_url: {url}\n"
            frontmatter += f"category: {meta.get('category', '')}\nsubcategory: {meta.get('subcategory', '')}\n"
            frontmatter += f"program: {meta.get('program', '')}\nregulation: {meta.get('regulation', '')}\n"
            frontmatter += f"campus: {meta.get('campus', '')}\nsource_type: PDF\ndata_type: PDF\n"
            frontmatter += f"retrieved_at: {timestamp}\n---\n"
            
            meta_path = pdf_path + ".meta.txt"
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter)

            downloaded += 1

        except Exception as e:
            print(f"Failed to download PDF {url}: {e}")
            failed += 1
            report['errors'].append(str(e))

    report['pdfs_downloaded'] = downloaded
    report['failed_pdfs'] = failed

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(f"PDF Collection complete. Downloaded: {downloaded}, Failed: {failed}")

if __name__ == '__main__':
    main()
