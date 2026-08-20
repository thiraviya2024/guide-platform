# app/engines/clinical_engine/kft_engine.py
"""KFT Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class KFTEngine:
    """Evaluates KFT parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate KFT parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM kft_rules
                    WHERE parameter = :param
                    AND min_value <= :value
                    AND max_value >= :value
                    AND is_active = TRUE
                    ORDER BY id
                    LIMIT 1
                """)
                
                row = db.execute(query, {"param": param, "value": value}).fetchone()
                
                if row:
                    results[param] = {
                        'value': value,
                        'status': row.status,
                        'recommendation': row.recommendation,
                        'category': 'kft'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'kft'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on KFT results."""
        risks = []
        
        # Acute Kidney Injury (High Creatinine + High BUN)
        if 'creatinine' in results and 'bun' in results:
            if results['creatinine']['status'] in ['High', 'Very High'] and results['bun']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Acute Kidney Injury',
                    'confidence': 'High',
                    'reason': 'Elevated creatinine and BUN',
                    'recommendation': 'Check urine output, renal ultrasound, consider nephrology consult'
                })
        
        # Chronic Kidney Disease (High Creatinine + Low eGFR)
        if 'creatinine' in results and 'egfr' in results:
            if results['creatinine']['status'] in ['High', 'Very High'] and results['egfr']['status'] in ['Moderate Decrease', 'Severe Decrease', 'Very Severe']:
                risks.append({
                    'disease': 'Chronic Kidney Disease',
                    'confidence': 'High',
                    'reason': 'Elevated creatinine and decreased eGFR',
                    'recommendation': 'Stage CKD, monitor regularly, consider nephrology consult'
                })
        
        # Dehydration (High Sodium + High BUN)
        if 'sodium' in results and 'bun' in results:
            if results['sodium']['status'] in ['High', 'Very High'] and results['bun']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Dehydration',
                    'confidence': 'High',
                    'reason': 'Elevated sodium and BUN',
                    'recommendation': 'Increase fluid intake, monitor urine output'
                })
        
        # Hyperkalemia (High Potassium)
        if 'potassium' in results and results['potassium']['status'] in ['High', 'Very High']:
            risks.append({
                'disease': 'Hyperkalemia',
                'confidence': 'High' if results['potassium']['status'] == 'Very High' else 'Medium',
                'reason': f"Elevated potassium ({results['potassium']['status']})",
                'recommendation': 'Cardiac monitoring, consider potassium binders, consult nephrologist'
            })
        
        # Hypokalemia (Low Potassium)
        if 'potassium' in results and results['potassium']['status'] in ['Low', 'Very Low']:
            risks.append({
                'disease': 'Hypokalemia',
                'confidence': 'High' if results['potassium']['status'] == 'Very Low' else 'Medium',
                'reason': f"Low potassium ({results['potassium']['status']})",
                'recommendation': 'Potassium supplementation, monitor cardiac rhythm'
            })
        
        # Gout (High Uric Acid)
        if 'uric_acid' in results and results['uric_acid']['status'] in ['High', 'Very High']:
            risks.append({
                'disease': 'Gout',
                'confidence': 'Medium',
                'reason': 'Elevated uric acid',
                'recommendation': 'Assess for joint pain, consider urate-lowering therapy'
            })
        
        # Metabolic Acidosis (Low Bicarbonate)
        if 'bicarbonate' in results and results['bicarbonate']['status'] in ['Low', 'Very Low']:
            risks.append({
                'disease': 'Metabolic Acidosis',
                'confidence': 'High' if results['bicarbonate']['status'] == 'Very Low' else 'Medium',
                'reason': f"Low bicarbonate ({results['bicarbonate']['status']})",
                'recommendation': 'Check anion gap, consider arterial blood gas, consult nephrologist'
            })
        
        # End-Stage Renal Disease (Very High Creatinine + Very Low eGFR)
        if 'creatinine' in results and 'egfr' in results:
            if results['creatinine']['status'] == 'Very High' and results['egfr']['status'] == 'Very Severe':
                risks.append({
                    'disease': 'End-Stage Renal Disease',
                    'confidence': 'High',
                    'reason': 'Very high creatinine and very low eGFR',
                    'recommendation': 'Immediate nephrology consult, consider dialysis'
                })
        
        return risks
