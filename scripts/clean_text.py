import re

def clean_markdown(text):
    # Basic cleaning
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_pdf_text(pdf_path):
    import pypdf
    pages = []
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append((i+1, text.strip()))
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return pages
