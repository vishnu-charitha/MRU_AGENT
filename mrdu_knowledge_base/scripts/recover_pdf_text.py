import os, json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_JSON = os.path.join(BASE_DIR, "output", "source_text_audit.json")
REPORT_JSON = os.path.join(BASE_DIR, "output", "pdf_recovery_report.json")

def check_ocr_availability():
    """
    Checks if OCR tools (tesseract, pytesseract, pdf2image) are available.
    """
    try:
        import pytesseract
        import pdf2image
        # Check if tesseract binary is in PATH
        # We can try a simple command or check version
        pytesseract.get_tesseract_version()
        return True, None
    except ImportError as e:
        return False, f"Missing Python dependency: {str(e)}. Please run: pip install pytesseract pdf2image"
    except Exception as e:
        return False, f"Tesseract binary not found or not in PATH: {str(e)}. Please install Tesseract-OCR (https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH."

def run():
    report = {
        "ocr_available": False,
        "ocr_missing_dependencies": None,
        "recommended_setup": "1. Install Tesseract-OCR binaries for Windows (https://github.com/UB-Mannheim/tesseract/wiki).\n2. Add Tesseract to system PATH.\n3. Run 'pip install pytesseract pdf2image'.\n4. Install Poppler for Windows and add to PATH (required by pdf2image).\n5. Re-run this script.",
        "scanned_pdfs_identified": 0,
        "pdfs_recovered": 0,
        "pdfs_failed": 0,
        "recovery_logs": []
    }
    
    ocr_avail, error = check_ocr_availability()
    report["ocr_available"] = ocr_avail
    if not ocr_avail:
        report["ocr_missing_dependencies"] = error
        
    if os.path.exists(AUDIT_JSON):
        with open(AUDIT_JSON, 'r', encoding='utf-8') as f:
            audit = json.load(f)
            
        for rec in audit.get("empty_records", []):
            if rec.get("is_scanned"):
                report["scanned_pdfs_identified"] += 1
                
        if not ocr_avail:
            report["recovery_logs"].append(f"OCR is unavailable. Cannot recover {report['scanned_pdfs_identified']} scanned PDFs. Please follow recommended setup.")
        else:
            report["recovery_logs"].append("OCR is available. Implementing OCR loop here... (Placeholder since OCR is not found)")
            
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    run()
