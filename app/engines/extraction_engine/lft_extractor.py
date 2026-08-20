# app/engines/extraction_engine/lft_extractor.py
"""
LFT Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class LFTExtractor:
    """Extracts LFT parameters from text."""
    
    PATTERNS = {
        'alt': [
            r'(?:alt|alanine transaminase|sgpt)\s*[:]?\s*([\d.]+)',
            r'alt\s*[:]?\s*([\d.]+)',
        ],
        'ast': [
            r'(?:ast|aspartate transaminase|sgot)\s*[:]?\s*([\d.]+)',
            r'ast\s*[:]?\s*([\d.]+)',
        ],
        'alp': [
            r'(?:alp|alkaline phosphatase)\s*[:]?\s*([\d.]+)',
            r'alp\s*[:]?\s*([\d.]+)',
        ],
        'total_bilirubin': [
            r'(?:total bilirubin|bilirubin total|t\.?bilirubin)\s*[:]?\s*([\d.]+)',
            r'total bilirubin\s*[:]?\s*([\d.]+)',
        ],
        'direct_bilirubin': [
            r'(?:direct bilirubin|conjugated bilirubin|d\.?bilirubin)\s*[:]?\s*([\d.]+)',
            r'direct bilirubin\s*[:]?\s*([\d.]+)',
        ],
        'total_protein': [
            r'(?:total protein|t\.?protein)\s*[:]?\s*([\d.]+)',
            r'total protein\s*[:]?\s*([\d.]+)',
        ],
        'albumin': [
            r'(?:albumin|alb)\s*[:]?\s*([\d.]+)',
            r'albumin\s*[:]?\s*([\d.]+)',
        ],
        'globulin': [
            r'(?:globulin|glob)\s*[:]?\s*([\d.]+)',
            r'globulin\s*[:]?\s*([\d.]+)',
        ],
        'ag_ratio': [
            r'(?:a/g ratio|albumin/globulin ratio)\s*[:]?\s*([\d.]+)',
            r'ag ratio\s*[:]?\s*([\d.]+)',
        ],
        'ggt': [
            r'(?:ggt|gamma-glutamyl transferase)\s*[:]?\s*([\d.]+)',
            r'ggt\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract LFT values from text."""
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