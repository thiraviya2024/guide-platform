# app/engines/extraction_engine/vitamins_extractor.py
"""
Vitamins Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class VitaminsExtractor:
    """Extracts Vitamins parameters from text."""
    
    PATTERNS = {
        'vitamin_b12': [
            r'(?:vitamin b12|b12|vitamin b-12|cobalamin)\s*[:]?\s*([\d.]+)',
            r'b12\s*[:]?\s*([\d.]+)',
        ],
        'vitamin_d': [
            r'(?:vitamin d|vitamin d3|25-hydroxy vitamin d|25-oh d)\s*[:]?\s*([\d.]+)',
            r'vitamin d\s*[:]?\s*([\d.]+)',
        ],
        'folate': [
            r'(?:folate|folic acid)\s*[:]?\s*([\d.]+)',
            r'folate\s*[:]?\s*([\d.]+)',
        ],
        'iron': [
            r'(?:iron|serum iron)\s*[:]?\s*([\d.]+)',
            r'iron\s*[:]?\s*([\d.]+)',
        ],
        'ferritin': [
            r'(?:ferritin)\s*[:]?\s*([\d.]+)',
            r'ferritin\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract Vitamins values from text."""
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