import os
import json
import re
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT_FILE = os.path.join(BASE_DIR, 'data', 'final', 'chunking_ready.jsonl')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'chunks')
REPORT_JSON = os.path.join(BASE_DIR, 'output', 'chunk_report.json')
REPORT_TXT = os.path.join(BASE_DIR, 'output', 'chunk_report.txt')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'mrdu_chunks.jsonl')

os.makedirs(OUTPUT_DIR, exist_ok=True)

def word_count(text):
    return len(text.split())

def is_heading(line):
    return re.match(r'^#{1,6}\s+(.*)', line)

def get_heading_level_and_text(line):
    match = re.match(r'^(#{1,6})\s+(.*)', line)
    if match:
        return len(match.group(1)), match.group(2).strip()
    return 0, ""

def chunk_document(doc):
    content = doc.get('content', '')
    if not content.strip():
        return []
    
    # Simple lines grouping by blank lines
    blocks = re.split(r'\n\n+', content)
    
    chunks = []
    current_chunk_blocks = []
    current_words = 0
    
    chapter = None
    section = None
    subsection = None
    
    # target words ~ 500 (which is roughly 650 tokens, inside the 500-1000 token range)
    TARGET_WORDS = 500
    
    def finalize_chunk(blocks_list, chap, sec, subsec):
        text = '\n\n'.join(blocks_list).strip()
        if not text:
            return None
        return {
            'text': text,
            'chapter': chap,
            'section': sec,
            'subsection': subsec
        }
        
    for block in blocks:
        block = block.strip()
        if not block: continue
        
        words_in_block = word_count(block)
        
        # Heading tracking
        h_level, h_text = get_heading_level_and_text(block)
        
        if h_level > 0:
            # If we hit a new heading, and we already have a decent sized chunk (or we just want to split cleanly), 
            # we can decide to finalize the current chunk if it's getting big.
            # But the prompt says "Preserve the logical meaning of each section".
            # Splitting at headings is good if the current chunk isn't empty.
            if current_words > TARGET_WORDS * 0.5:
                res = finalize_chunk(current_chunk_blocks, chapter, section, subsection)
                if res: chunks.append(res)
                current_chunk_blocks = []
                current_words = 0
                
            if h_level == 1:
                chapter = h_text
                section = None
                subsection = None
            elif h_level == 2:
                section = h_text
                subsection = None
            elif h_level >= 3:
                subsection = h_text
                
        current_chunk_blocks.append(block)
        current_words += words_in_block
        
        if current_words >= TARGET_WORDS:
            res = finalize_chunk(current_chunk_blocks, chapter, section, subsection)
            if res: chunks.append(res)
            # small overlap? 
            # To keep it simple and section aware, we just start fresh or keep the last block if it was small
            # Not forcing overlap as per prompt: "Do not force overlap when it would duplicate an entire short section."
            current_chunk_blocks = []
            current_words = 0

    if current_chunk_blocks:
        res = finalize_chunk(current_chunk_blocks, chapter, section, subsection)
        if res: chunks.append(res)
        
    return chunks

def main():
    if not os.path.exists(INPUT_FILE):
        print("No chunking_ready.jsonl found.")
        return

    records = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    report = {
        "total_input_documents": len(records),
        "documents_chunked": 0,
        "total_chunks": 0,
        "average_chunk_size": 0,
        "minimum_chunk_size": 999999,
        "maximum_chunk_size": 0,
        "btech_chunks": 0,
        "mtech_chunks": 0,
        "general_chunks": 0,
        "tirupati_chunks": 0,
        "main_campus_chunks": 0,
        "regulation_chunks": 0,
        "admission_chunks": 0,
        "exam_chunks": 0,
        "notification_chunks": 0,
        "duplicate_chunks_removed": 0,
        "manual_review_chunks": 0,
        "document_chunk_counts": {}
    }
    
    final_chunks = []
    seen_chunk_texts = set()
    total_tokens = 0
    
    for doc in records:
        doc_id = doc['document_id']
        raw_chunks = chunk_document(doc)
        
        if not raw_chunks:
            continue
            
        report['documents_chunked'] += 1
        report['document_chunk_counts'][doc_id] = 0
        
        for idx, rc in enumerate(raw_chunks):
            # Duplicate check
            if rc['text'] in seen_chunk_texts:
                report['duplicate_chunks_removed'] += 1
                continue
                
            seen_chunk_texts.add(rc['text'])
            
            chunk_id = f"{doc_id}-CHUNK-{idx+1:04d}"
            words = word_count(rc['text'])
            tokens = int(words * 1.3) # approx tokens
            
            if tokens < report['minimum_chunk_size']: report['minimum_chunk_size'] = tokens
            if tokens > report['maximum_chunk_size']: report['maximum_chunk_size'] = tokens
            total_tokens += tokens
            
            prog = str(doc.get('program', ''))
            cat = str(doc.get('category', ''))
            campus = str(doc.get('campus', ''))
            
            is_btech = 'B.Tech' in prog or 'BTech' in rc['text']
            is_mtech = 'M.Tech' in prog or 'MTech' in rc['text']
            
            if is_btech: report['btech_chunks'] += 1
            elif is_mtech: report['mtech_chunks'] += 1
            else: report['general_chunks'] += 1
            
            if campus == 'tirupati': report['tirupati_chunks'] += 1
            else: report['main_campus_chunks'] += 1
            
            if doc.get('regulation'): report['regulation_chunks'] += 1
            if 'Admissions' in cat: report['admission_chunks'] += 1
            if 'Examinations' in cat: report['exam_chunks'] += 1
            if 'Notifications' in cat or 'Circular' in str(doc.get('subcategory')): report['notification_chunks'] += 1
            
            final_doc = {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "source_id": doc.get('source_id'),
                "title": doc.get('title'),
                "content": rc['text'],
                "category": doc.get('category'),
                "subcategory": doc.get('subcategory'),
                "program": doc.get('program'),
                "regulation": doc.get('regulation'),
                "department": doc.get('department'),
                "campus": doc.get('campus'),
                "academic_year": doc.get('academic_year'),
                "semester": doc.get('semester'),
                "document_type": doc.get('document_type'),
                "source_url": doc.get('source_url'),
                "source_title": doc.get('source_title'),
                "page_number": doc.get('page_number'),
                "published_date": doc.get('published_date'),
                "effective_date": doc.get('effective_date'),
                "status": doc.get('status'),
                "source_type": doc.get('source_type'),
                "retrieved_at": doc.get('retrieved_at'),
                "chapter": rc['chapter'],
                "section": rc['section'],
                "subsection": rc['subsection'],
                "requires_manual_review": doc.get('requires_manual_review', False),
                "chunk_index": idx + 1,
                "total_chunks": len(raw_chunks) # Note: this is total before dedup
            }
            
            if final_doc['requires_manual_review']:
                report['manual_review_chunks'] += 1
                
            final_chunks.append(final_doc)
            report['document_chunk_counts'][doc_id] += 1
            report['total_chunks'] += 1
            
    if report['total_chunks'] > 0:
        report['average_chunk_size'] = total_tokens // report['total_chunks']
    else:
        report['minimum_chunk_size'] = 0

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for c in final_chunks:
            f.write(json.dumps(c) + '\n')
            
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    with open(REPORT_TXT, 'w', encoding='utf-8') as f:
        f.write("CHUNK REPORT\n============\n")
        f.write(f"Total Documents: {report['total_input_documents']}\n")
        f.write(f"Documents Chunked: {report['documents_chunked']}\n")
        f.write(f"Total Chunks: {report['total_chunks']}\n")
        f.write(f"Average Chunk Size (tokens): {report['average_chunk_size']}\n")
        f.write(f"Smallest Chunk (tokens): {report['minimum_chunk_size']}\n")
        f.write(f"Largest Chunk (tokens): {report['maximum_chunk_size']}\n")
        f.write(f"B.Tech Chunks: {report['btech_chunks']}\n")
        f.write(f"M.Tech Chunks: {report['mtech_chunks']}\n")
        f.write(f"General Chunks: {report['general_chunks']}\n")
        f.write(f"Tirupati Chunks: {report['tirupati_chunks']}\n")
        f.write(f"Regulation Chunks: {report['regulation_chunks']}\n")
        f.write(f"Admission Chunks: {report['admission_chunks']}\n")
        f.write(f"Examination Chunks: {report['exam_chunks']}\n")
        f.write(f"Notification Chunks: {report['notification_chunks']}\n\n")
        
        f.write("Representative Chunk Examples:\n")
        for i in range(min(5, len(final_chunks))):
            ex = final_chunks[i]
            f.write(f"--- Example {i+1} ---\n")
            f.write(f"Chunk ID: {ex['chunk_id']}\n")
            f.write(f"Title: {ex['title']}\n")
            f.write(f"Program: {ex['program']}\n")
            f.write(f"Regulation: {ex['regulation']}\n")
            f.write(f"Campus: {ex['campus']}\n")
            f.write(f"Section: {ex['section']}\n")
            preview = ex['content'][:150].replace('\n', ' ') + '...' if len(ex['content']) > 150 else ex['content']
            f.write(f"Content Preview: {preview}\n\n")

if __name__ == '__main__':
    main()
