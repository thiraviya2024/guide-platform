# parser/word_parser.py
from docx import Document
from pathlib import Path

def extract_text_from_docx(file_path: Path) -> str:
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])