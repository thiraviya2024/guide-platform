# app/engines/extraction_engine/lipid_extractor.py
"""
Lipid Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class LipidExtractor:
    """Extracts Lipid parameters from text."""
    
    PATTERNS = {
        'total_cholesterol': [
            r'(?:total cholesterol|tc)\s*[:]?\s*([\d.]+)',
            r'total cholesterol\s*[:]?\s*([\d.]+)',
        ],
        'ldl': [
            r'(?:ldl|ldl cholesterol|ldl-c)\s*[:]?\s*([\d.]+)',
            r'ldl\s*[:]?\s*([\d.]+)',
        ],
        'hdl': [
            r'(?:hdl|hdl cholesterol|hdl-c)\s*[:]?\s*([\d.]+)',
            r'hdl\s*[:]?\s*([\d.]+)',
        ],
        'triglycerides': [
            r'(?:triglycerides|tg)\s*[:]?\s*([\d.]+)',
            r'triglycerides\s*[:]?\s*([\d.]+)',
        ],
        'vldl': [
            r'(?:vldl|vldl cholesterol)\s*[:]?\s*([\d.]+)',
            r'vldl\s*[:]?\s*([\d.]+)',
        ],
        'non_hdl': [
            r'(?:non.hdl|non hdl|non-hdl cholesterol)\s*[:]?\s*([\d.]+)',
            r'non.hdl\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract Lipid values from text."""
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
