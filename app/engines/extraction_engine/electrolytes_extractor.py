# app/engines/extraction_engine/electrolytes_extractor.py
"""
Electrolytes Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ElectrolytesExtractor:
    """Extracts Electrolytes parameters from text."""
    
    PATTERNS = {
        'calcium': [
            r'(?:calcium|ca)\s*[:]?\s*([\d.]+)',
            r'calcium\s*[:]?\s*([\d.]+)',
        ],
        'magnesium': [
            r'(?:magnesium|mg)\s*[:]?\s*([\d.]+)',
            r'magnesium\s*[:]?\s*([\d.]+)',
        ],
        'phosphorus': [
            r'(?:phosphorus|phosphate|phos)\s*[:]?\s*([\d.]+)',
            r'phosphorus\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract Electrolytes values from text."""
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