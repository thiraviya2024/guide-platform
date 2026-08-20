# app/engines/extraction_engine/cbc_extractor.py
"""
CBC Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class CBCExtractor:
    """Extracts CBC parameters from text."""
    
    PATTERNS = {
        'hemoglobin': [
            r'(?:hemoglobin|hb|hgb)\s*[:]?\s*([\d.]+)',
            r'hb\s*[:]?\s*([\d.]+)',
        ],
        'wbc': [
            r'(?:wbc|white blood cells?)\s*[:]?\s*([\d.]+)',
            r'wbc\s*[:]?\s*([\d.]+)',
        ],
        'platelets': [
            r'(?:platelets?|plt)\s*[:]?\s*([\d.]+)',
            r'plt\s*[:]?\s*([\d.]+)',
        ],
        'rbc': [
            r'(?:rbc|red blood cells?)\s*[:]?\s*([\d.]+)',
            r'rbc\s*[:]?\s*([\d.]+)',
        ],
        'neutrophils': [
            r'(?:neutrophils?|neut)\s*[:]?\s*([\d.]+)',
            r'neut\s*[:]?\s*([\d.]+)',
        ],
        'lymphocytes': [
            r'(?:lymphocytes?|lymph)\s*[:]?\s*([\d.]+)',
            r'lymph\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract CBC values from text."""
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