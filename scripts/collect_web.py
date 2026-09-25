import csv
import json
import os
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCES_CSV = os.path.join(BASE_DIR, 'config', 'sources.csv')
RAW_WEB_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'web')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
REPORT_FILE = os.path.join(OUTPUT_DIR, 'collection_report.json')
FAILED_FILE = os.path.join(OUTPUT_DIR, 'failed_sources.jsonl')
PDF_QUEUE_FILE = os.path.join(OUTPUT_DIR, 'pdf_queue.json')

os.makedirs(RAW_WEB_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

VALID_ACTIONS = {'INCLUDE', 'FILTER', 'VERIFY', 'OPTIONAL-FILTER'}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def clean_html(soup):
    for element in soup(['nav', 'header', 'footer', 'script', 'style', 'noscript', 'aside', 'iframe', 'svg']):
        element.decompose()
    return soup

def extract_content(soup):
    content = []
    # VERY basic extraction for markdown
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'table']):
        text = tag.get_text(strip=True)
        if not text:
            continue
        if tag.name.startswith('h'):
            level = int(tag.name[1])
            content.append('#' * level + ' ' + text)
        elif tag.name in ['ul', 'ol']:
            for li in tag.find_all('li'):
                content.append('- ' + li.get_text(strip=True))
        elif tag.name == 'p':
            content.append(text)
        elif tag.name == 'table':
            content.append('[Table Extracted: ' + text[:100] + '...]')
    return '\n\n'.join(content)

def main():
    report = {
        'collection_timestamp': datetime.now().isoformat(),
        'total_sources': 0,
        'successful_sources': 0,
        'failed_sources': 0,
        'skipped_sources': 0,
        'pdfs_discovered': 0,
        'pdfs_downloaded': 0,
        'failed_pdfs': 0,
        'errors': []
    }
    
    pdf_queue = []
    failed_sources = []

    with open(SOURCES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            report['total_sources'] += 1
            action = row.get('action', '').upper()
            if action not in VALID_ACTIONS:
                report['skipped_sources'] += 1
                continue
            
            url = row['url']
            source_id = row['id']
            print(f"Processing {source_id}: {url}")
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'lxml')
                
                # find PDFs
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.lower().endswith('.pdf'):
                        full_url = urljoin(url, href)
                        pdf_queue.append({
                            'source_id': source_id,
                            'url': full_url,
                            'source_meta': row
                        })
                        report['pdfs_discovered'] += 1
                
                # Clean and extract
                soup = clean_html(soup)
                markdown_text = extract_content(soup)
                
                # Metadata
                timestamp = datetime.now().isoformat()
                frontmatter = f"---\ndocument_id: MRDU-WEB-{source_id.zfill(3)}\nsource_id: {source_id}\n"
                frontmatter += f"title: {row.get('title', '')}\nsource_url: {url}\n"
                frontmatter += f"category: {row.get('category', '')}\nsubcategory: {row.get('subcategory', '')}\n"
                frontmatter += f"program: {row.get('program', '')}\nregulation: {row.get('regulation', '')}\n"
                frontmatter += f"campus: {row.get('campus', '')}\nsource_type: Web\ndata_type: HTML\n"
                frontmatter += f"retrieved_at: {timestamp}\n---\n\n"
                
                final_content = frontmatter + markdown_text
                
                out_file = os.path.join(RAW_WEB_DIR, f"source_{source_id.zfill(3)}.md")
                with open(out_file, 'w', encoding='utf-8') as out_f:
                    out_f.write(final_content)
                    
                report['successful_sources'] += 1
                
            except Exception as e:
                print(f"Failed {url}: {e}")
                report['failed_sources'] += 1
                report['errors'].append(str(e))
                failed_sources.append({'id': source_id, 'url': url, 'error': str(e)})

    # Write outputs
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    with open(FAILED_FILE, 'w', encoding='utf-8') as f:
        for fail in failed_sources:
            f.write(json.dumps(fail) + '\n')
            
    with open(PDF_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(pdf_queue, f, indent=2)

if __name__ == '__main__':
    main()
