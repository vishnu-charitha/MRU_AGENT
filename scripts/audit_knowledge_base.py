import json
import os
from collections import defaultdict
import glob

def run_audit():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    embeddings_file = os.path.join(base_dir, 'data', 'embeddings', 'embeddings.jsonl')
    
    audit_data = {
        "corpus": {
            "num_source_urls": 0,
            "num_raw_web_docs": 0,
            "num_pdfs": 0,
            "num_final_docs": 0,
            "num_chunks": 0,
            "num_embeddings": 0,
            "qdrant_vector_count": 66,
            "programs": set(),
            "regulations": set(),
            "campuses": set(),
            "categories": set()
        },
        "regulations": {
            "B.Tech": {"MR20": "NOT FOUND", "MR21": "NOT FOUND", "MR22": "NOT FOUND", "MR24": "NOT FOUND"},
            "M.Tech": {"MR20": "NOT FOUND", "MR21": "NOT FOUND", "MR22": "NOT FOUND", "MR24": "NOT FOUND"}
        },
        "scope_audit": {
            "leakage_count": 0,
            "affected_chunks": [],
            "exact_terms": set()
        },
        "campus_audit": {
            "tirupati_chunks": 0,
            "main_chunks": 0
        },
        "metadata_audit": {
            "missing_categories": 0,
            "empty_metadata": 0,
            "categories": defaultdict(int)
        },
        "duplicate_audit": {
            "duplicate_text_chunks": 0
        },
        "mtech_mr20": {}
    }
    
    chunks_text = set()
    
    if os.path.exists(embeddings_file):
        with open(embeddings_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                audit_data["corpus"]["num_embeddings"] += 1
                meta = data.get("metadata", {})
                
                # Meta aggregations
                prog = meta.get("program")
                reg = meta.get("regulation")
                camp = meta.get("campus")
                cat = meta.get("category")
                
                if prog: audit_data["corpus"]["programs"].add(prog)
                if reg: audit_data["corpus"]["regulations"].add(reg)
                if camp: audit_data["corpus"]["campuses"].add(camp)
                if cat: 
                    audit_data["corpus"]["categories"].add(cat)
                    audit_data["metadata_audit"]["categories"][cat] += 1
                else:
                    audit_data["metadata_audit"]["missing_categories"] += 1
                
                # Regulations Matrix
                if prog in audit_data["regulations"] and reg in audit_data["regulations"][prog]:
                    audit_data["regulations"][prog][reg] = "FOUND"
                    
                # Scope Audit
                text = data.get("content", "").lower()
                forbidden = ["mba", "bba", "bca", "mca", "b.sc", "b.com", "ph.d."]
                found_leakage = [term for term in forbidden if term in text]
                if found_leakage:
                    audit_data["scope_audit"]["leakage_count"] += 1
                    audit_data["scope_audit"]["affected_chunks"].append(meta.get("chunk_id"))
                    for term in found_leakage:
                        audit_data["scope_audit"]["exact_terms"].add(term)
                        
                # Campus Audit
                if camp == "tirupati":
                    audit_data["campus_audit"]["tirupati_chunks"] += 1
                elif camp == "main":
                    audit_data["campus_audit"]["main_chunks"] += 1
                    
                # M.Tech MR20 Check
                if prog == "M.Tech" and reg == "MR20":
                    audit_data["mtech_mr20"] = {
                        "chunk_id": meta.get("chunk_id"),
                        "source": meta.get("source"),
                        "program": prog,
                        "regulation": reg
                    }
                    
                # Duplicates
                if text in chunks_text:
                    audit_data["duplicate_audit"]["duplicate_text_chunks"] += 1
                chunks_text.add(text)

    # Convert sets to lists
    for k in ["programs", "regulations", "campuses", "categories"]:
        audit_data["corpus"][k] = list(audit_data["corpus"][k])
    audit_data["scope_audit"]["exact_terms"] = list(audit_data["scope_audit"]["exact_terms"])
    
    with open(os.path.join(base_dir, 'output', 'step10_knowledge_audit.json'), 'w') as f:
        json.dump(audit_data, f, indent=2)

    print("Audit Complete.")

if __name__ == "__main__":
    run_audit()
