import os
import json
import re
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FINAL_DOCS = os.path.join(BASE_DIR, 'data', 'final', 'chunking_ready.jsonl')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
REPORT_JSON = os.path.join(OUTPUT_DIR, 'final_audit_report.json')
REPORT_TXT = os.path.join(OUTPUT_DIR, 'final_audit_report.txt')

REQUIRED_META = [
    'document_id', 'source_id', 'title', 'content', 'category', 'subcategory',
    'program', 'regulation', 'department', 'campus', 'academic_year', 'semester',
    'document_type', 'source_url', 'source_title', 'page_number', 'published_date',
    'effective_date', 'status', 'source_type', 'retrieved_at', 'requires_manual_review'
]

EXCLUDED_TERMS = [
    'MBA', 'BBA', 'BCA', 'MCA', 'Ph.D.', 'PhD', 'B.Sc', 'BSc', 'B.Com', 'BCom',
    'Master of Business Administration', 'Bachelor of Business Administration',
    'Bachelor of Computer Applications', 'Master of Computer Applications',
    'Doctor of Philosophy', 'Bachelor of Science', 'Bachelor of Commerce'
]

VALID_REGS = ['MR20', 'MR21', 'MR22', 'MR24', None]

def main():
    if not os.path.exists(FINAL_DOCS):
        print("No final_docs.jsonl found.")
        return
        
    records = []
    with open(FINAL_DOCS, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    audit = {
        "total_final_records": len(records),
        "excluded_program_leaks": [],
        "excluded_program_records": 0,
        "btech_records": 0,
        "mtech_records": 0,
        "general_records": 0,
        "tirupati_records": 0,
        "main_records": 0,
        "manual_review_records": [],
        "empty_records": [],
        "low_quality_records": [],
        "duplicate_records": [],
        "regulation_issues": [],
        "metadata_issues": []
    }
    
    seen_ids = set()
    seen_content = set()
    
    for r in records:
        content = str(r.get('content', ''))
        url = str(r.get('source_url', ''))
        
        # 1. Excluded Program Leaks
        leak_found = False
        for term in EXCLUDED_TERMS:
            # Check line by line to differentiate exclusive leaks vs incidental mentions
            for line in content.split('\n'):
                if re.search(r'\b' + re.escape(term) + r'\b', line, re.IGNORECASE):
                    # If this line also contains an included term, we treat it as incidental
                    if not any(re.search(r'\b' + re.escape(incl) + r'\b', line, re.IGNORECASE) for incl in ['B.Tech', 'BTech', 'B-Tech', 'M.Tech', 'MTech', 'M-Tech', 'Engineering']):
                        leak_found = True
                        print(f"Leak found in {r['document_id']}: {line}")
                        break
            if leak_found:
                break
        
        if leak_found:
            audit['excluded_program_leaks'].append(r['document_id'])
            audit['excluded_program_records'] += 1
            
        # 2. B.Tech/M.Tech Check
        prog = str(r.get('program', ''))
        if 'B.Tech' in prog or 'BTech' in content:
            audit['btech_records'] += 1
        elif 'M.Tech' in prog or 'MTech' in content:
            audit['mtech_records'] += 1
        else:
            audit['general_records'] += 1
            
        # 3. Regulation Check
        reg = r.get('regulation')
        if reg:
            # Check if any part of reg matches VALID_REGS
            valid = False
            for v in VALID_REGS:
                if v and v in str(reg):
                    valid = True
                    break
            if not valid:
                audit['regulation_issues'].append(r['document_id'])
                
        # 4. Manual Review
        if r.get('requires_manual_review'):
            audit['manual_review_records'].append({
                "document_id": r['document_id'],
                "title": r.get('title'),
                "source_url": r.get('source_url'),
                "page_number": r.get('page_number'),
                "reason": "Content extraction failed or regulation unclear",
                "is_empty": len(content.strip()) == 0 or "Extraction Failed" in content,
                "recommendation": "EXCLUDE until reviewed"
            })
            
        # 5. Tirupati Check
        campus = str(r.get('campus', '')).lower()
        if 'tirupati' in url.lower():
            if campus != 'tirupati':
                audit['metadata_issues'].append(f"{r['document_id']} should have tirupati campus")
            audit['tirupati_records'] += 1
        else:
            if campus == 'tirupati':
                audit['metadata_issues'].append(f"{r['document_id']} should NOT have tirupati campus")
            audit['main_records'] += 1
            
        # 6. Metadata Validation
        for req in REQUIRED_META:
            if req not in r:
                audit['metadata_issues'].append(f"{r['document_id']} missing {req}")
                
        # 7. Duplicates
        doc_id = r.get('document_id')
        if doc_id in seen_ids:
            audit['duplicate_records'].append(f"Duplicate doc_id: {doc_id}")
        seen_ids.add(doc_id)
        
        if content in seen_content and len(content) > 50:
            audit['duplicate_records'].append(f"Duplicate content in doc_id: {doc_id}")
        seen_content.add(content)
        
        # 8. Empty / Low Quality
        if len(content.strip()) == 0 or "Extraction Failed" in content:
            audit['empty_records'].append(doc_id)
        elif len(content.strip()) < 50:
            audit['low_quality_records'].append(doc_id)
            
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(audit, f, indent=2)
        
    with open(REPORT_TXT, 'w', encoding='utf-8') as f:
        f.write("FINAL DATA QUALITY AUDIT REPORT\n")
        f.write("===============================\n")
        f.write(f"Total Records: {audit['total_final_records']}\n")
        f.write(f"Safe for Chunking: {audit['total_final_records'] - len(audit['manual_review_records']) - len(audit['empty_records']) - audit['excluded_program_records']}\n")
        f.write(f"Manual Review Needed: {len(audit['manual_review_records'])}\n\n")
        
        leak_pass = "FAIL" if audit['excluded_program_records'] > 0 else "PASS"
        meta_pass = "FAIL" if len(audit['metadata_issues']) > 0 else "PASS"
        dup_pass = "FAIL" if len(audit['duplicate_records']) > 0 else "PASS"
        reg_pass = "FAIL" if len(audit['regulation_issues']) > 0 else "PASS"
        
        # Determine tirupati pass (we checked it inside metadata issues)
        tiru_issues = [x for x in audit['metadata_issues'] if 'tirupati' in x]
        tiru_pass = "FAIL" if len(tiru_issues) > 0 else "PASS"
        if len(tiru_issues) == 0 and meta_pass == "FAIL":
            # Just separate them conceptually
            pass
            
        f.write(f"Excluded-Program Leakage: {leak_pass}\n")
        f.write(f"Required Metadata: {meta_pass}\n")
        f.write(f"Duplicates: {dup_pass}\n")
        f.write(f"Regulation Scope: {reg_pass}\n")
        f.write(f"Tirupati Campus Separation: {tiru_pass}\n\n")
        
        if audit['manual_review_records']:
            f.write("Manual Review List:\n")
            for m in audit['manual_review_records']:
                f.write(f" - {m['document_id']} ({m['source_url']}) Page: {m['page_number']}. Reason: {m['reason']}. Recommendation: {m['recommendation']}\n")

if __name__ == '__main__':
    main()
