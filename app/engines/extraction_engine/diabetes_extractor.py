# app/engines/extraction_engine/diabetes_extractor.py
"""
Diabetes Parameter Extractor
"""

import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DiabetesExtractor:
    """Extracts Diabetes parameters from text."""
    
    PATTERNS = {
        'fasting_glucose': [
            r'(?:fasting glucose|fasting blood sugar|fbs|fbg)\s*[:]?\s*([\d.]+)',
            r'fasting glucose\s*[:]?\s*([\d.]+)',
        ],
        'hba1c': [
            r'(?:hba1c|a1c|hemoglobin a1c|glycated hemoglobin)\s*[:]?\s*([\d.]+)',
            r'hba1c\s*[:]?\s*([\d.]+)',
        ],
        'insulin': [
            r'(?:insulin)\s*[:]?\s*([\d.]+)',
            r'insulin\s*[:]?\s*([\d.]+)',
        ],
        'homa_ir': [
            r'(?:homa-ir|homa ir|homa index)\s*[:]?\s*([\d.]+)',
            r'homa\s*[:]?\s*([\d.]+)',
        ],
        'postprandial_glucose': [
            r'(?:postprandial glucose|ppbs|post meal glucose|2hr glucose)\s*[:]?\s*([\d.]+)',
            r'postprandial\s*[:]?\s*([\d.]+)',
        ],
    }
    
    def extract(self, text: str) -> Dict[str, float]:
        """Extract Diabetes values from text."""
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