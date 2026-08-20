# app/engines/extraction_engine/thyroid_extractor.py
"""
Thyroid Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ThyroidExtractor:
    """Extracts Thyroid parameters from text."""
    
    PATTERNS = {
        'tsh': [
            r'(?:tsh|thyroid stimulating hormone)\s*[:]?\s*([\d.]+)',
            r'tsh\s*[:]?\s*([\d.]+)',
        ],
        't3': [
            r'(?:t3|triiodothyronine)\s*[:]?\s*([\d.]+)',
            r't3\s*[:]?\s*([\d.]+)',
        ],
        't4': [
            r'(?:t4|thyroxine)\s*[:]?\s*([\d.]+)',
            r't4\s*[:]?\s*([\d.]+)',
        ],
        'free_t3': [
            r'(?:free t3|ft3|free triiodothyronine)\s*[:]?\s*([\d.]+)',
            r'ft3\s*[:]?\s*([\d.]+)',
        ],
        'free_t4': [
            r'(?:free t4|ft4|free thyroxine)\s*[:]?\s*([\d.]+)',
            r'ft4\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract Thyroid values from text."""
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