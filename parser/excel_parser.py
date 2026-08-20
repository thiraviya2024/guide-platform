# parser/excel_parser.py
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict

def extract_from_excel(file_path: Path) -> Tuple[str, Optional[Dict]]:
    df = pd.read_excel(file_path) if file_path.suffix == ".xlsx" else pd.read_csv(file_path)
    text = df.to_string()
    structured = df.to_dict('records')
    return text, structured