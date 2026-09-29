
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
