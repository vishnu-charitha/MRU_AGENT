import os
import json
import re

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FINAL_DOCS = os.path.join(BASE_DIR, 'data', 'final', 'final_docs.jsonl')
CHUNKING_READY = os.path.join(BASE_DIR, 'data', 'final', 'chunking_ready.jsonl')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
REPORT_JSON = os.path.join(OUTPUT_DIR, 'scope_fix_report.json')
REPORT_TXT = os.path.join(OUTPUT_DIR, 'scope_fix_report.txt')

MANUAL_REVIEW_IDS = {
    'MRDU-PDF-014-002', 'MRDU-PDF-014-003', 'MRDU-PDF-014-006', 'MRDU-PDF-014-007',
    'MRDU-PDF-001-001', 'MRDU-PDF-001-002', 'MRDU-PDF-001-003', 'MRDU-PDF-001-004',
    'MRDU-PDF-001-005', 'MRDU-PDF-001-006', 'MRDU-PDF-001-007', 'MRDU-PDF-001-008',
    'MRDU-PDF-001-009'
}

# The list from the prompt
EXCLUDED_TERMS = [
    'MBA', 'BBA', 'BCA', 'MCA', 'Ph.D.', 'PhD', 'B.Sc', 'BSc', 'B.Com', 'BCom',
    'Master of Business Administration', 'Bachelor of Business Administration',
    'Bachelor of Computer Applications', 'Master of Computer Applications',
    'Doctor of Philosophy', 'Bachelor of Science', 'Bachelor of Commerce'
]

INCLUDED_TERMS = ['B.Tech', 'BTech', 'B-Tech', 'M.Tech', 'MTech', 'M-Tech', 'Engineering']
VALID_REGS = ['MR20', 'MR21', 'MR22', 'MR24']

def contains_terms(text, terms):
    for term in terms:
        if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
            return True
    return False

def contains_excluded(text):
    for term in EXCLUDED_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
            return True, term
    return False, None

def main():
    if not os.path.exists(FINAL_DOCS):
        print("No final_docs.jsonl found.")
        return
        
    records = []
    with open(FINAL_DOCS, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    report = {
        "total_input_records": len(records),
        "records_retained": 0,
        "records_excluded": 0,
        "records_manual_review": 0,
        "btech_records": 0,
        "mtech_records": 0,
        "general_records": 0,
        "tirupati_records": 0,
        "main_records": 0,
        "mba_content_removed": 0,
        "bba_content_removed": 0,
        "bca_content_removed": 0,
        "mca_content_removed": 0,
        "phd_content_removed": 0,
        "bsc_content_removed": 0,
        "bcom_content_removed": 0,
        "regulation_records": 0,
        "regulation_records_manual_review": 0
    }
    
    retained_ids = []
    excluded_ids = []
    manual_ids = []
    txt_lines = []

    out_records = []

    for r in records:
        doc_id = r['document_id']
        url = str(r.get('source_url', ''))
        
        # 1. EXCLUDE MANUAL-REVIEW DOCUMENTS
        # (Using startswith because PDF docs have -P1 etc if paginated, though we had them without pages or with pages)
        # Let's check exact match or if it starts with the ID and a dash
        is_manual = r.get('requires_manual_review', False)
        for mid in MANUAL_REVIEW_IDS:
            if doc_id == mid or doc_id.startswith(mid + "-"):
                is_manual = True
                
        if is_manual:
            report['records_manual_review'] += 1
            manual_ids.append(doc_id)
            txt_lines.append(f"Document: {doc_id}\nDecision: MANUAL REVIEW\nReason: Explicitly flagged for manual review or extraction failed.\n")
            continue

        # 2 & 3. EXCLUDED PROGRAM FILTER & MIXED CONTENT
        content = str(r.get('content', ''))
        has_excl, term = contains_excluded(content)
        
        if has_excl:
            lines = content.split('\n')
            new_lines = []
            removed_something = False
            for line in lines:
                l_has_excl, p_term = contains_excluded(line)
                l_has_incl = contains_terms(line, INCLUDED_TERMS)
                
                # If a line has excluded terms but NOT included terms, we assume it's purely about an excluded program.
                if l_has_excl and not l_has_incl:
                    removed_something = True
                    term_up = p_term.upper()
                    if 'MBA' in term_up: report['mba_content_removed'] += 1
                    if 'BBA' in term_up: report['bba_content_removed'] += 1
                    if 'BCA' in term_up: report['bca_content_removed'] += 1
                    if 'MCA' in term_up: report['mca_content_removed'] += 1
                    if 'PHD' in term_up or 'PH.D' in term_up: report['phd_content_removed'] += 1
                    if 'BSC' in term_up or 'B.SC' in term_up: report['bsc_content_removed'] += 1
                    if 'BCOM' in term_up or 'B.COM' in term_up: report['bcom_content_removed'] += 1
                else:
                    new_lines.append(line)
            
            new_content = '\n'.join(new_lines)
            
            # If everything was removed or only tiny fragments remain, exclude the whole document
            if len(new_content.strip()) < 50:
                report['records_excluded'] += 1
                excluded_ids.append(doc_id)
                txt_lines.append(f"Document: {doc_id}\nDecision: EXCLUDED\nReason: Document consisted entirely of excluded program content (e.g. {term}).\n")
                continue
            
            # Still has excluded terms? (Maybe they were mixed in the same line)
            # If so, just retain it since it's genuinely mixed/incidental.
            r['content'] = new_content
            if removed_something:
                txt_lines.append(f"Document: {doc_id}\nDecision: PARTIALLY RETAINED\nReason: Mixed document. Retained B.Tech/M.Tech/General content. Removed paragraphs exclusively mentioning {term}.\n")
        
        # 6. REGULATION SCOPE
        # Only set if it's actually an academic regulation document
        is_regulation_doc = False
        if 'regulation' in url.lower() or 'regulation' in str(r.get('subcategory', '')).lower():
            is_regulation_doc = True
            
        if is_regulation_doc:
            reg = str(r.get('regulation', ''))
            valid_reg = None
            for v in VALID_REGS:
                if v in reg or v in content:
                    valid_reg = v
                    break
            if valid_reg:
                r['regulation'] = valid_reg
                report['regulation_records'] += 1
            else:
                # Actual regulation doc but unknown regulation -> manual review
                report['records_manual_review'] += 1
                report['regulation_records_manual_review'] += 1
                manual_ids.append(doc_id)
                txt_lines.append(f"Document: {doc_id}\nDecision: MANUAL REVIEW\nReason: Regulation document but strict MR20/21/22/24 could not be identified.\n")
                continue
        else:
            # General document -> regulation is null
            r['regulation'] = None

        # Stats
        prog = str(r.get('program', ''))
        cont = str(r.get('content', ''))
        if 'B.Tech' in prog or 'BTech' in cont:
            report['btech_records'] += 1
        elif 'M.Tech' in prog or 'MTech' in cont:
            report['mtech_records'] += 1
        else:
            report['general_records'] += 1
            
        if r.get('campus') == 'tirupati':
            report['tirupati_records'] += 1
        else:
            report['main_records'] += 1
            
        report['records_retained'] += 1
        retained_ids.append(doc_id)
        out_records.append(r)

    report['retained_document_ids'] = retained_ids
    report['excluded_document_ids'] = excluded_ids
    report['manual_review_document_ids'] = manual_ids

    # Write output files
    with open(CHUNKING_READY, 'w', encoding='utf-8') as f:
        for rec in out_records:
            f.write(json.dumps(rec) + '\n')
            
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    with open(REPORT_TXT, 'w', encoding='utf-8') as f:
        f.write("SCOPE FIX REPORT\n=================\n\n")
        f.write("\n".join(txt_lines))
        f.write("\nSummary:\n")
        f.write(f"Retained: {len(retained_ids)}\n")
        f.write(f"Excluded: {len(excluded_ids)}\n")
        f.write(f"Manual Review: {len(manual_ids)}\n")

if __name__ == '__main__':
    main()
