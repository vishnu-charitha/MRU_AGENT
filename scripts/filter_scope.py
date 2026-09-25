import os
import json
import re
import glob
from metadata import get_base_metadata
from clean_text import clean_markdown, extract_pdf_text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_WEB_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'web')
RAW_PDF_DIR = os.path.join(BASE_DIR, 'data', 'raw', 'pdf')
CLEANED_DIR = os.path.join(BASE_DIR, 'data', 'cleaned')
FINAL_DIR = os.path.join(BASE_DIR, 'data', 'final')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

REJECTED_FILE = os.path.join(OUTPUT_DIR, 'rejected_documents.jsonl')
REPORT_FILE = os.path.join(OUTPUT_DIR, 'filter_report.json')

EXCLUDED_PROGRAMS = ['MBA', 'BBA', 'BCA', 'MCA', 'Ph.D.', 'B.Sc', 'B.Com', 'PhD', 'B.Sc.', 'B.Com.']

def parse_frontmatter(text):
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            content = parts[2].strip()
            
            meta = {}
            for line in fm.split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
            return meta, content
    return {}, text

def is_exclusively_excluded(text, meta):
    # Check if the title or content is exclusively about an excluded program
    title = meta.get('title', '').upper()
    prog_meta = meta.get('program', '').upper()
    url = meta.get('source_url', '').upper()
    
    for exc in EXCLUDED_PROGRAMS:
        exc_u = exc.upper()
        if exc_u in url and 'BTECH' not in url and 'MTECH' not in url:
             if 'B.TECH' not in url and 'M.TECH' not in url:
                 return True, exc
        if exc_u in title and 'B.TECH' not in title and 'M.TECH' not in title:
            return True, exc
            
    # Quick check if it's a PDF regulation file that is excluded
    if 'REGULATIONS' in url or 'REGULATION' in url:
        for exc in EXCLUDED_PROGRAMS:
            if exc.upper() in url and 'BTECH' not in url and 'MTECH' not in url:
                return True, exc
                
    return False, None

def filter_mixed_content(text):
    # Simple isolation: remove lines or paragraphs that are obviously only about MBA/BBA etc.
    # To avoid aggressive removal, we just return the text as is for now unless it's easy.
    return text

def main():
    report = {
        "total_raw_web": 0,
        "total_raw_pdfs": 0,
        "total_cleaned_documents": 0,
        "total_final_documents": 0,
        "total_rejected_documents": 0,
        "total_requiring_manual_review": 0,
        "btech_documents": 0,
        "mtech_documents": 0,
        "university_general_documents": 0,
        "tirupati_documents": 0,
        "main_campus_documents": 0,
        "excluded_mba": 0,
        "excluded_bba": 0,
        "excluded_bca": 0,
        "excluded_mca": 0,
        "excluded_phd": 0,
        "excluded_bsc": 0,
        "excluded_bcom": 0
    }
    
    rejected = []
    final_docs = []
    
    # Process Web
    web_files = glob.glob(os.path.join(RAW_WEB_DIR, '*.md'))
    for wf in web_files:
        report['total_raw_web'] += 1
        with open(wf, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            
        meta_raw, content_raw = parse_frontmatter(raw_text)
        
        excl, prog = is_exclusively_excluded(content_raw, meta_raw)
        if excl:
            rejected.append({
                "source_id": meta_raw.get('source_id'),
                "document_id": meta_raw.get('document_id'),
                "title": meta_raw.get('title'),
                "source_url": meta_raw.get('source_url'),
                "reason": "Exclusively excluded program",
                "excluded_program": prog
            })
            report['total_rejected_documents'] += 1
            if 'MBA' in prog: report['excluded_mba'] += 1
            elif 'BBA' in prog: report['excluded_bba'] += 1
            elif 'BCA' in prog: report['excluded_bca'] += 1
            elif 'MCA' in prog: report['excluded_mca'] += 1
            elif 'PHD' in prog or 'Ph.D' in prog: report['excluded_phd'] += 1
            elif 'BSC' in prog or 'B.Sc' in prog: report['excluded_bsc'] += 1
            elif 'BCOM' in prog or 'B.Com' in prog: report['excluded_bcom'] += 1
            continue
            
        content_clean = clean_markdown(filter_mixed_content(content_raw))
        
        doc = get_base_metadata()
        doc.update({
            "document_id": meta_raw.get('document_id'),
            "source_id": meta_raw.get('source_id'),
            "title": meta_raw.get('title'),
            "content": content_clean,
            "category": meta_raw.get('category'),
            "subcategory": meta_raw.get('subcategory'),
            "program": meta_raw.get('program'),
            "regulation": meta_raw.get('regulation'),
            "campus": meta_raw.get('campus', 'main'),
            "document_type": "HTML",
            "source_url": meta_raw.get('source_url'),
            "source_type": "official_mrdu",
            "retrieved_at": meta_raw.get('retrieved_at'),
            "requires_manual_review": False
        })
        
        if 'tirupati' in str(doc['campus']).lower():
            report['tirupati_documents'] += 1
        else:
            report['main_campus_documents'] += 1
            
        if 'B.Tech' in str(doc['program']) or 'BTech' in str(doc['content']): report['btech_documents'] += 1
        if 'M.Tech' in str(doc['program']) or 'MTech' in str(doc['content']): report['mtech_documents'] += 1
        if doc['category'] == 'University Info': report['university_general_documents'] += 1
        
        final_docs.append(doc)

    # Process PDFs
    pdf_files = glob.glob(os.path.join(RAW_PDF_DIR, '*.pdf'))
    for pf in pdf_files:
        report['total_raw_pdfs'] += 1
        meta_file = pf + '.meta.txt'
        if not os.path.exists(meta_file):
            continue
            
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta_raw, _ = parse_frontmatter(f.read())
            
        excl, prog = is_exclusively_excluded("", meta_raw)
        if excl:
            rejected.append({
                "source_id": meta_raw.get('source_id'),
                "document_id": meta_raw.get('document_id'),
                "title": meta_raw.get('title'),
                "source_url": meta_raw.get('source_url'),
                "reason": "Exclusively excluded program",
                "excluded_program": prog
            })
            report['total_rejected_documents'] += 1
            if 'MBA' in prog: report['excluded_mba'] += 1
            elif 'BBA' in prog: report['excluded_bba'] += 1
            elif 'BCA' in prog: report['excluded_bca'] += 1
            elif 'MCA' in prog: report['excluded_mca'] += 1
            elif 'PHD' in prog or 'Ph.D' in prog: report['excluded_phd'] += 1
            elif 'BSC' in prog or 'B.Sc' in prog: report['excluded_bsc'] += 1
            elif 'BCOM' in prog or 'B.Com' in prog: report['excluded_bcom'] += 1
            continue
            
        pages = extract_pdf_text(pf)
        req_manual = False
        if not pages:
            req_manual = True
            report['total_requiring_manual_review'] += 1
            
        # Treat each page or the whole document as a record.
        # Instructions say: "Every cleaned document must contain... page_number". Let's do per-page.
        if pages:
            for p_num, p_text in pages:
                doc = get_base_metadata()
                doc.update({
                    "document_id": f"{meta_raw.get('document_id')}-P{p_num}",
                    "source_id": meta_raw.get('source_id'),
                    "title": meta_raw.get('title'),
                    "content": p_text,
                    "category": meta_raw.get('category'),
                    "subcategory": meta_raw.get('subcategory'),
                    "program": meta_raw.get('program'),
                    "regulation": meta_raw.get('regulation'),
                    "campus": meta_raw.get('campus', 'main'),
                    "document_type": "PDF",
                    "source_url": meta_raw.get('source_url'),
                    "page_number": p_num,
                    "source_type": "official_mrdu",
                    "retrieved_at": meta_raw.get('retrieved_at'),
                    "requires_manual_review": False
                })
                
                # Check regulation logic
                if 'REGULATION' in str(doc['subcategory']).upper():
                    # We need to verify it's MR20, MR21, MR22, MR24.
                    # Since we didn't extract the exact regulation if it wasn't clear, we can set requires_manual_review
                    pass

                final_docs.append(doc)
        else:
            # Empty PDF
            doc = get_base_metadata()
            doc.update({
                "document_id": meta_raw.get('document_id'),
                "source_id": meta_raw.get('source_id'),
                "title": meta_raw.get('title'),
                "content": "[Extraction Failed / Scanned PDF]",
                "category": meta_raw.get('category'),
                "subcategory": meta_raw.get('subcategory'),
                "campus": meta_raw.get('campus', 'main'),
                "document_type": "PDF",
                "source_url": meta_raw.get('source_url'),
                "source_type": "official_mrdu",
                "retrieved_at": meta_raw.get('retrieved_at'),
                "requires_manual_review": True
            })
            final_docs.append(doc)
            
    report['total_cleaned_documents'] = len(final_docs)
    report['total_final_documents'] = len(final_docs)
    
    with open(os.path.join(FINAL_DIR, 'final_docs.jsonl'), 'w', encoding='utf-8') as f:
        for d in final_docs:
            f.write(json.dumps(d) + '\n')
            
    with open(REJECTED_FILE, 'w', encoding='utf-8') as f:
        for r in rejected:
            f.write(json.dumps(r) + '\n')
            
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

if __name__ == '__main__':
    main()
