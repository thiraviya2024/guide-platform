# app/engines/clinical_engine/electrolytes_engine.py
"""Electrolytes Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class ElectrolytesEngine:
    """Evaluates Electrolytes parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate Electrolytes parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM electrolytes_rules
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
                        'category': 'electrolytes'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'electrolytes'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on Electrolytes results."""
        risks = []
        
        # Hypercalcemia
        if 'calcium' in results:
            if results['calcium']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Hypercalcemia',
                    'confidence': 'High' if results['calcium']['status'] == 'Very High' else 'Medium',
                    'reason': f"Elevated calcium ({results['calcium']['status']})",
                    'recommendation': 'Check PTH, vitamin D, consider malignancy workup, consult endocrinologist'
                })
        
        # Hypocalcemia
        if 'calcium' in results:
            if results['calcium']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Hypocalcemia',
                    'confidence': 'High' if results['calcium']['status'] == 'Very Low' else 'Medium',
                    'reason': f"Low calcium ({results['calcium']['status']})",
                    'recommendation': 'Check vitamin D, PTH, calcium supplementation, consult physician'
                })
        
        # Hypermagnesemia
        if 'magnesium' in results:
            if results['magnesium']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Hypermagnesemia',
                    'confidence': 'High' if results['magnesium']['status'] == 'Very High' else 'Medium',
                    'reason': f"Elevated magnesium ({results['magnesium']['status']})",
                    'recommendation': 'Check renal function, review medications, consult nephrologist'
                })
        
        # Hypomagnesemia
        if 'magnesium' in results:
            if results['magnesium']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Hypomagnesemia',
                    'confidence': 'High' if results['magnesium']['status'] == 'Very Low' else 'Medium',
                    'reason': f"Low magnesium ({results['magnesium']['status']})",
                    'recommendation': 'Magnesium supplementation, check renal function, consult physician'
                })
        
        # Hyperphosphatemia
        if 'phosphorus' in results:
            if results['phosphorus']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Hyperphosphatemia',
                    'confidence': 'High' if results['phosphorus']['status'] == 'Very High' else 'Medium',
                    'reason': f"Elevated phosphorus ({results['phosphorus']['status']})",
                    'recommendation': 'Check renal function, phosphate binders, dietary changes, consult nephrologist'
                })
        
        # Hypophosphatemia
        if 'phosphorus' in results:
            if results['phosphorus']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Hypophosphatemia',
                    'confidence': 'High' if results['phosphorus']['status'] == 'Very Low' else 'Medium',
                    'reason': f"Low phosphorus ({results['phosphorus']['status']})",
                    'recommendation': 'Phosphorus supplementation, check nutrition status, consult physician'
                })
        
        return risks
