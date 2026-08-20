# parser/pdf_parser.py
import pdfplumber
import fitz
from pathlib import Path

def extract_text_from_pdf(file_path: Path) -> str:
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)