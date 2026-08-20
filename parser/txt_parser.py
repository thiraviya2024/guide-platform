# parser/txt_parser.py
from pathlib import Path

def extract_from_txt(file_path: Path) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()