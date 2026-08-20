# extractor/blood_test_parser.py
import re
from typing import Dict, Any, List

class BloodTestParser:
    """Parse human-written blood test results"""
    
    def __init__(self):
        self.patterns = {
            # CBC
            'hemoglobin': [r'hemoglobin\s*:?\s*([\d.]+)', r'hb\s*:?\s*([\d.]+)', r'hgb\s*:?\s*([\d.]+)'],
            'wbc': [r'wbc\s*:?\s*([\d.]+)', r'white blood cells?\s*:?\s*([\d.]+)'],
            'platelets': [r'platelets?\s*:?\s*([\d.]+)', r'plt\s*:?\s*([\d.]+)'],
            'neutrophils': [r'neutrophils?\s*:?\s*([\d.]+)', r'neut\s*:?\s*([\d.]+)'],
            'lymphocytes': [r'lymphocytes?\s*:?\s*([\d.]+)', r'lymph\s*:?\s*([\d.]+)'],
            'mcv': [r'mcv\s*:?\s*([\d.]+)'],
            'mch': [r'mch\s*:?\s*([\d.]+)'],
            
            # LFT
            'alt_sgpt': [r'alt\s*:?\s*([\d.]+)', r'sgpt\s*:?\s*([\d.]+)'],
            'ast_sgot': [r'ast\s*:?\s*([\d.]+)', r'sgot\s*:?\s*([\d.]+)'],
            'alkaline_phosphatase': [r'alkaline phosphatase\s*:?\s*([\d.]+)', r'alk phos\s*:?\s*([\d.]+)'],
            'bilirubin_total': [r'bilirubin\s*:?\s*([\d.]+)', r'total bilirubin\s*:?\s*([\d.]+)'],
            'albumin': [r'albumin\s*:?\s*([\d.]+)'],
            'total_protein': [r'total protein\s*:?\s*([\d.]+)'],
            
            # RFT/KFT
            'creatinine': [r'creatinine\s*:?\s*([\d.]+)', r'cr\s*:?\s*([\d.]+)'],
            'bun': [r'bun\s*:?\s*([\d.]+)', r'blood urea nitrogen\s*:?\s*([\d.]+)'],
            'urea': [r'urea\s*:?\s*([\d.]+)'],
            'uric_acid': [r'uric acid\s*:?\s*([\d.]+)', r'ua\s*:?\s*([\d.]+)'],
            'sodium': [r'sodium\s*:?\s*([\d.]+)', r'na\s*:?\s*([\d.]+)'],
            'potassium': [r'potassium\s*:?\s*([\d.]+)', r'k\s*:?\s*([\d.]+)'],
            
            # Vitamins
            'vitamin_b12': [r'vitamin b[ -]?12\s*:?\s*([\d.]+)', r'b12\s*:?\s*([\d.]+)'],
            'vitamin_b6': [r'vitamin b[ -]?6\s*:?\s*([\d.]+)', r'b6\s*:?\s*([\d.]+)'],
            'vitamin_b9_folate': [r'vitamin b[ -]?9\s*:?\s*([\d.]+)', r'folate\s*:?\s*([\d.]+)'],
            'homocysteine': [r'homocysteine\s*:?\s*([\d.]+)'],
            'vitamin_d': [r'vitamin d\s*:?\s*([\d.]+)', r'vit d\s*:?\s*([\d.]+)'],
            
            # Diabetes
            'fasting_glucose': [r'fasting\s*:?\s*([\d.]+)', r'fbs\s*:?\s*([\d.]+)', r'fasting blood sugar\s*:?\s*([\d.]+)'],
            'pp_glucose': [r'post? prandial\s*:?\s*([\d.]+)', r'ppbs\s*:?\s*([\d.]+)'],
            'hba1c': [r'hba1c\s*:?\s*([\d.]+)', r'a1c\s*:?\s*([\d.]+)'],
        }
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse blood test results from text"""
        results = {}
        text_lower = text.lower()
        
        for param, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        results[param] = float(match.group(1))
                        break
                    except ValueError:
                        continue
        
        return results
    
    def parse_structured(self, structured_data: Dict) -> Dict[str, Any]:
        """Parse from structured data (Excel/PDF extraction)"""
        results = {}
        
        if structured_data:
            for param, value in structured_data.items():
                if value is not None:
                    try:
                        results[param] = float(value)
                    except (ValueError, TypeError):
                        continue
        
        return results