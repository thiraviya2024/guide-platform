# parser/file_parser.py
from pathlib import Path
from typing import Tuple, Optional, Dict

from utils.logger import logger   # ← Add this line

from .pdf_parser import extract_text_from_pdf
from .word_parser import extract_text_from_docx
from .excel_parser import extract_from_excel
from .txt_parser import extract_from_txt
from .image_parser import extract_text_from_image

def parse_uploaded_file(file_path: Path) -> Tuple[str, Optional[Dict]]:
    suffix = file_path.suffix.lower()
    
    try:
        if suffix == ".pdf":
            text = extract_text_from_pdf(file_path)
            structured = None
        elif suffix == ".docx":
            text = extract_text_from_docx(file_path)
            structured = None
        elif suffix in [".xlsx", ".xls"]:
            text, structured = extract_from_excel(file_path)
        elif suffix == ".txt":
            text = extract_from_txt(file_path)
            structured = None
        elif suffix in [".png", ".jpg", ".jpeg"]:
            text = extract_text_from_image(file_path)
            structured = None
        else:
            text = "Unsupported format"
            structured = None
            
        return text.strip(), structured
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")   # Now it will work
        return "", None