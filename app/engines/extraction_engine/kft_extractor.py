# app/engines/extraction_engine/kft_extractor.py
"""
KFT Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class KFTExtractor:
    """Extracts KFT parameters from text."""
    
    PATTERNS = {
        'creatinine': [
            r'(?:creatinine|creat)\s*[:]?\s*([\d.]+)',
            r'creatinine\s*[:]?\s*([\d.]+)',
        ],
        'bun': [
            r'(?:bun|blood urea nitrogen|urea)\s*[:]?\s*([\d.]+)',
            r'bun\s*[:]?\s*([\d.]+)',
        ],
        'uric_acid': [
            r'(?:uric acid|urate)\s*[:]?\s*([\d.]+)',
            r'uric acid\s*[:]?\s*([\d.]+)',
        ],
        'sodium': [
            r'(?:sodium|na)\s*[:]?\s*([\d.]+)',
            r'sodium\s*[:]?\s*([\d.]+)',
        ],
        'potassium': [
            r'(?:potassium|k)\s*[:]?\s*([\d.]+)',
            r'potassium\s*[:]?\s*([\d.]+)',
        ],
        'chloride': [
            r'(?:chloride|cl)\s*[:]?\s*([\d.]+)',
            r'chloride\s*[:]?\s*([\d.]+)',
        ],
        'bicarbonate': [
            r'(?:bicarbonate|hco3)\s*[:]?\s*([\d.]+)',
            r'bicarbonate\s*[:]?\s*([\d.]+)',
        ],
        'egfr': [
            r'(?:egfr|gfr|estimated gfr)\s*[:]?\s*([\d.]+)',
            r'egfr\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract KFT values from text."""
        results = {}
        text_lower = text.lower()
        
        for param, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        results[param] = float(match.group(1))
                        break
                    except ValueError:
                        continue
        
        return results