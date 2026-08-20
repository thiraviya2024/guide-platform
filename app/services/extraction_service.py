# app/services/extraction_service.py
"""
Medical Report Extraction Service
Extracts medical parameters from text with confidence tracking.
"""

import re
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class ExtractionService:
    """Extract medical parameters from text with confidence."""
    
    # Complete parameter patterns for all modules
    PATTERNS = {
        'lipid': {
            'total_cholesterol': {
                'patterns': [
                    r'(?:total\s*cholesterol|tc|chol)\s*[:]?\s*([\d.]+)',
                    r'(?:cholesterol\s*total)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'mg/dL',
                'display_name': 'Total Cholesterol'
            },
            'ldl': {
                'patterns': [
                    r'(?:ldl|ldl\s*cholesterol|ldl-c|ldl\s*direct)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'mg/dL',
                'display_name': 'LDL Cholesterol'
            },
            'hdl': {
                'patterns': [
                    r'(?:hdl|hdl\s*cholesterol|hdl-c|high\s*density\s*lipoprotein)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'mg/dL',
                'display_name': 'HDL Cholesterol'
            },
            'triglycerides': {
                'patterns': [
                    r'(?:triglycerides|tg|trigs)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'mg/dL',
                'display_name': 'Triglycerides'
            },
            'vldl': {
                'patterns': [
                    r'(?:vldl|vldl\s*cholesterol|very\s*low\s*density\s*lipoprotein)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'mg/dL',
                'display_name': 'VLDL'
            },
            'non_hdl': {
                'patterns': [
                    r'(?:non[- ]hdl|non\s*hdl|non-hdl\s*cholesterol)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'mg/dL',
                'display_name': 'Non-HDL Cholesterol'
            }
        },
        'cbc': {
            'hemoglobin': {
                'patterns': [
                    r'(?:hemoglobin|hb|hgb)\s*[:]?\s*([\d.]+)',
                ],
                'unit': 'g/dL',
                'display_name': 'Hemoglobin'
            },
            'wbc': {
                'patterns': [
                    r'(?:wbc|white\s*blood\s*cells?)\s*[:]?\s*([\d.]+)',
                ],
                'unit': '10³/µL',
                'display_name': 'WBC'
            },
            'platelets': {
                'patterns': [
                    r'(?:platelets?|plt)\s*[:]?\s*([\d.]+)',
                ],
                'unit': '10³/µL',
                'display_name': 'Platelets'
            },
            'rbc': {
                'patterns': [
                    r'(?:rbc|red\s*blood\s*cells?)\s*[:]?\s*([\d.]+)',
                ],
                'unit': '10⁶/µL',
                'display_name': 'RBC'
            },
            'neutrophils': {
                'patterns': [
                    r'(?:neutrophils?|neut)\s*[:]?\s*([\d.]+)',
                ],
                'unit': '%',
                'display_name': 'Neutrophils'
            },
            'lymphocytes': {
                'patterns': [
                    r'(?:lymphocytes?|lymph)\s*[:]?\s*([\d.]+)',
                ],
                'unit': '%',
                'display_name': 'Lymphocytes'
            }
        },
        'lft': {
            'alt': {
                'patterns': [r'(?:alt|alanine\s*transaminase|sgpt)\s*[:]?\s*([\d.]+)'],
                'unit': 'U/L',
                'display_name': 'ALT'
            },
            'ast': {
                'patterns': [r'(?:ast|aspartate\s*transaminase|sgot)\s*[:]?\s*([\d.]+)'],
                'unit': 'U/L',
                'display_name': 'AST'
            },
            'alp': {
                'patterns': [r'(?:alp|alkaline\s*phosphatase)\s*[:]?\s*([\d.]+)'],
                'unit': 'U/L',
                'display_name': 'ALP'
            },
            'total_bilirubin': {
                'patterns': [r'(?:total\s*bilirubin|t\.?bilirubin|tbili)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Total Bilirubin'
            },
            'direct_bilirubin': {
                'patterns': [r'(?:direct\s*bilirubin|d\.?bilirubin|dbili)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Direct Bilirubin'
            },
            'total_protein': {
                'patterns': [r'(?:total\s*protein|t\.?protein)\s*[:]?\s*([\d.]+)'],
                'unit': 'g/dL',
                'display_name': 'Total Protein'
            },
            'albumin': {
                'patterns': [r'(?:albumin|alb)\s*[:]?\s*([\d.]+)'],
                'unit': 'g/dL',
                'display_name': 'Albumin'
            },
            'globulin': {
                'patterns': [r'(?:globulin|glob)\s*[:]?\s*([\d.]+)'],
                'unit': 'g/dL',
                'display_name': 'Globulin'
            },
            'ag_ratio': {
                'patterns': [r'(?:a/g\s*ratio|ag\s*ratio|albumin[/ ]globulin\s*ratio)\s*[:]?\s*([\d.]+)'],
                'unit': '',
                'display_name': 'A/G Ratio'
            },
            'ggt': {
                'patterns': [r'(?:ggt|gamma-glutamyl\s*transferase)\s*[:]?\s*([\d.]+)'],
                'unit': 'U/L',
                'display_name': 'GGT'
            }
        },
        'kft': {
            'creatinine': {
                'patterns': [r'(?:creatinine|creat|cr)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Creatinine'
            },
            'bun': {
                'patterns': [r'(?:bun|blood\s*urea\s*nitrogen|urea)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'BUN'
            },
            'uric_acid': {
                'patterns': [r'(?:uric\s*acid|urate|ua)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Uric Acid'
            },
            'sodium': {
                'patterns': [r'(?:sodium|na)\s*[:]?\s*([\d.]+)'],
                'unit': 'mEq/L',
                'display_name': 'Sodium'
            },
            'potassium': {
                'patterns': [r'(?:potassium|k)\s*[:]?\s*([\d.]+)'],
                'unit': 'mEq/L',
                'display_name': 'Potassium'
            },
            'chloride': {
                'patterns': [r'(?:chloride|cl)\s*[:]?\s*([\d.]+)'],
                'unit': 'mEq/L',
                'display_name': 'Chloride'
            },
            'bicarbonate': {
                'patterns': [r'(?:bicarbonate|hco3)\s*[:]?\s*([\d.]+)'],
                'unit': 'mEq/L',
                'display_name': 'Bicarbonate'
            },
            'egfr': {
                'patterns': [r'(?:egfr|gfr|estimated\s*gfr)\s*[:]?\s*([\d.]+)'],
                'unit': 'mL/min/1.73m²',
                'display_name': 'eGFR'
            }
        },
        'thyroid': {
            'tsh': {
                'patterns': [r'(?:tsh|thyroid\s*stimulating\s*hormone)\s*[:]?\s*([\d.]+)'],
                'unit': 'mIU/L',
                'display_name': 'TSH'
            },
            't3': {
                'patterns': [r'(?:t3|triiodothyronine)\s*[:]?\s*([\d.]+)'],
                'unit': 'ng/dL',
                'display_name': 'T3'
            },
            't4': {
                'patterns': [r'(?:t4|thyroxine)\s*[:]?\s*([\d.]+)'],
                'unit': 'mcg/dL',
                'display_name': 'T4'
            },
            'free_t3': {
                'patterns': [r'(?:free\s*t3|ft3)\s*[:]?\s*([\d.]+)'],
                'unit': 'pg/mL',
                'display_name': 'Free T3'
            },
            'free_t4': {
                'patterns': [r'(?:free\s*t4|ft4)\s*[:]?\s*([\d.]+)'],
                'unit': 'ng/dL',
                'display_name': 'Free T4'
            }
        },
        'diabetes': {
            'fasting_glucose': {
                'patterns': [r'(?:fasting\s*glucose|fbs|fbg)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Fasting Glucose'
            },
            'hba1c': {
                'patterns': [r'(?:hba1c|a1c|hemoglobin\s*a1c)\s*[:]?\s*([\d.]+)'],
                'unit': '%',
                'display_name': 'HbA1c'
            },
            'insulin': {
                'patterns': [r'(?:insulin)\s*[:]?\s*([\d.]+)'],
                'unit': 'µIU/mL',
                'display_name': 'Insulin'
            },
            'homa_ir': {
                'patterns': [r'(?:homa-ir|homa\s*ir)\s*[:]?\s*([\d.]+)'],
                'unit': '',
                'display_name': 'HOMA-IR'
            }
        },
        'vitamins': {
            'vitamin_b12': {
                'patterns': [r'(?:vitamin\s*b12|b12|cobalamin)\s*[:]?\s*([\d.]+)'],
                'unit': 'pg/mL',
                'display_name': 'Vitamin B12'
            },
            'vitamin_d': {
                'patterns': [r'(?:vitamin\s*d|25-oh\s*d|25-hydroxy\s*vitamin\s*d)\s*[:]?\s*([\d.]+)'],
                'unit': 'ng/mL',
                'display_name': 'Vitamin D'
            },
            'folate': {
                'patterns': [r'(?:folate|folic\s*acid)\s*[:]?\s*([\d.]+)'],
                'unit': 'ng/mL',
                'display_name': 'Folate'
            },
            'iron': {
                'patterns': [r'(?:iron|serum\s*iron)\s*[:]?\s*([\d.]+)'],
                'unit': 'mcg/dL',
                'display_name': 'Iron'
            },
            'ferritin': {
                'patterns': [r'(?:ferritin)\s*[:]?\s*([\d.]+)'],
                'unit': 'ng/mL',
                'display_name': 'Ferritin'
            }
        },
        'electrolytes': {
            'calcium': {
                'patterns': [r'(?:calcium|ca)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Calcium'
            },
            'magnesium': {
                'patterns': [r'(?:magnesium|mg)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Magnesium'
            },
            'phosphorus': {
                'patterns': [r'(?:phosphorus|phosphate|phos)\s*[:]?\s*([\d.]+)'],
                'unit': 'mg/dL',
                'display_name': 'Phosphorus'
            }
        }
    }

    def extract_module(self, text: str, module: str) -> Dict[str, Any]:
        """
        Extract parameters for a specific module.
        
        Args:
            text: Raw text to extract from
            module: Module name (lipid, cbc, lft, etc.)
            
        Returns:
            Dict with extraction results including confidence and status
        """
        results = {}
        module_patterns = self.PATTERNS.get(module, {})
        
        if not module_patterns:
            logger.warning(f"No patterns found for module: {module}")
            return results
        
        for param, config in module_patterns.items():
            extracted_value = None
            confidence = 0.0
            matched_pattern = None
            
            # Try each pattern
            for pattern in config['patterns']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        extracted_value = float(match.group(1))
                        confidence = 0.95
                        matched_pattern = pattern
                        break
                    except (ValueError, TypeError):
                        continue
            
            # If not found, try finding in table format
            if extracted_value is None:
                extracted_value, confidence = self._extract_from_table(text, param, config['patterns'])
            
            results[param] = {
                'value': extracted_value,
                'unit': config['unit'],
                'display_name': config.get('display_name', param),
                'confidence': confidence,
                'status': self._determine_status(extracted_value, confidence),
                'matched_pattern': matched_pattern,
                'is_extracted': extracted_value is not None and confidence > 0.5
            }
            
            # Log extraction result
            if extracted_value is None:
                logger.debug(f"Could not extract {param} from text")
            else:
                logger.debug(f"Extracted {param}: {extracted_value} {config['unit']} (confidence: {confidence}")
        
        return results
    
    def _extract_from_table(self, text: str, param: str, patterns: List[str]) -> tuple:
        """Try to extract value from table-like text."""
        # Look for patterns with units or in tabular format
        for pattern in patterns:
            # Try with unit
            unit_patterns = [
                rf"{pattern}\s*mg/dL",
                rf"{pattern}\s*mmol/L",
                rf"{pattern}\s*U/L",
                rf"{pattern}\s*g/dL",
                rf"{pattern}\s*%",
            ]
            for p in unit_patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        return value, 0.85
                    except (ValueError, TypeError):
                        continue
        return None, 0.0
    
    def _determine_status(self, value: Optional[float], confidence: float) -> str:
        """Determine extraction status."""
        if value is None:
            return 'not_extracted'
        if confidence < 0.5:
            return 'uncertain'
        if confidence < 0.8:
            return 'low_confidence'
        return 'extracted'
    
    def get_extraction_summary(self, results: Dict) -> Dict:
        """Get summary of extraction results."""
        total = len(results)
        extracted = sum(1 for r in results.values() if r.get('is_extracted', False))
        missing = total - extracted
        
        return {
            'total_parameters': total,
            'extracted_count': extracted,
            'missing_count': missing,
            'missing_parameters': [
                k for k, v in results.items() if not v.get('is_extracted', False)
            ],
            'extraction_rate': extracted / total if total > 0 else 0
        }


# Singleton instance
extraction_service = ExtractionService()