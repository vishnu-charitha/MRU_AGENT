
import os, json, hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_JSONL = os.path.join(BASE_DIR, "data", "final", "mrdu_knowledge_base.jsonl")
CHUNKS_DIR = os.path.join(BASE_DIR, "data", "chunks")
CHUNKS_JSONL = os.path.join(CHUNKS_DIR, "mrdu_chunks.jsonl")
REPORT_JSON = os.path.join(BASE_DIR, "output", "chunking_report.json")

os.makedirs(CHUNKS_DIR, exist_ok=True)

def tokenize(text):
    return text.split()

def chunk_text(text, max_tokens=600, overlap=100):
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for p in paragraphs:
        p = p.strip()
        if not p: continue
        
        # Don't break tables or small lists unnecessarily.
        # This simple heuristic adds paragraph by paragraph.
        p_tokens = tokenize(p)
        p_len = len(p_tokens)
        
        if current_length + p_len > max_tokens and current_length > 0:
            chunks.append(" ".join(current_chunk))
            
            # overlap
            overlap_chunk = []
            overlap_length = 0
            for w in reversed(current_chunk):
                overlap_chunk.insert(0, w)
                overlap_length += 1
                if overlap_length >= overlap:
                    break
                    
            current_chunk = overlap_chunk
            current_length = overlap_length
            
        current_chunk.extend(p_tokens)
        current_length += p_len
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def run():
    stats = {
        "source_records_processed": 0,
        "chunks_created": 0,
        "token_length_stats": {"min": 999999, "max": 0, "avg": 0},
        "errors": []
    }
    
    if not os.path.exists(INPUT_JSONL):
        stats["errors"].append("Input file not found")
        return stats
        
    all_chunks = []
    total_tokens = 0
    
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line)
            stats["source_records_processed"] += 1
            
            content = doc.get("content", "")
            if not content and "pages" in doc:
                content = "\n".join([p.get("content", "") for p in doc["pages"]])
                
            text_chunks = chunk_text(content)
            
            for i, tc in enumerate(text_chunks):
                if not tc.strip(): continue
                chunk_id = hashlib.md5(f"{doc.get('document_id')}_{i}_{tc}".encode()).hexdigest()
                
                chunk_doc = {
                    "chunk_id": chunk_id,
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                    "category": doc.get("category"),
                    "subcategory": doc.get("subcategory"),
                    "program": doc.get("program"),
                    "regulation": doc.get("regulation"),
                    "department": doc.get("department"),
                    "campus": doc.get("campus"),
                    "academic_year": doc.get("academic_year"),
                    "document_type": doc.get("document_type"),
                    "source_url": doc.get("source_url"),
                    "source_title": doc.get("source_title"),
                    "originating_page_url": doc.get("originating_page_url", doc.get("source_url")),
                    "page_number": doc.get("page_number"),
                    "published_date": doc.get("published_date"),
                    "effective_date": doc.get("effective_date"),
                    "status": doc.get("status"),
                    "retrieved_at": doc.get("retrieved_at"),
                    "requires_manual_review": doc.get("requires_manual_review", False),
                    "content": tc
                }
                
                # Replace None with null (already handled by json.dumps)
                all_chunks.append(chunk_doc)
                stats["chunks_created"] += 1
                
                tc_len = len(tokenize(tc))
                total_tokens += tc_len
                if tc_len < stats["token_length_stats"]["min"]: stats["token_length_stats"]["min"] = tc_len
                if tc_len > stats["token_length_stats"]["max"]: stats["token_length_stats"]["max"] = tc_len
                
    if stats["chunks_created"] > 0:
        stats["token_length_stats"]["avg"] = total_tokens / stats["chunks_created"]
    else:
        stats["token_length_stats"]["min"] = 0
        
    with open(CHUNKS_JSONL, 'w', encoding='utf-8') as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")
            
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
        
    print(f"Chunking complete. Created {stats['chunks_created']} chunks.")
    return stats

if __name__ == '__main__':
    run()
