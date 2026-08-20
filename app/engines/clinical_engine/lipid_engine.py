# app/engines/clinical_engine/lipid_engine.py
"""Lipid Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class LipidEngine:
    """Evaluates Lipid parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate Lipid parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM lipid_rules
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
                        'category': 'lipid'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'lipid'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get disease risks from lipid results."""
        risks = []
        
        if 'total_cholesterol' in results and 'ldl' in results:
            if results['total_cholesterol']['status'] == 'High' and results['ldl']['status'] == 'High':
                risks.append({
                    'disease': 'Hyperlipidemia',
                    'confidence': 'High',
                    'reason': 'Elevated total cholesterol and LDL',
                    'recommendation': 'Lifestyle changes, consider statin therapy'
                })
        
        if 'hdl' in results and results['hdl']['status'] == 'Low':
            risks.append({
                'disease': 'Low HDL Cholesterol',
                'confidence': 'Medium',
                'reason': 'Low HDL cholesterol levels',
                'recommendation': 'Increase exercise, healthy fats (omega-3), stop smoking'
            })
        
        if 'triglycerides' in results and results['triglycerides']['status'] == 'High':
            risks.append({
                'disease': 'Hypertriglyceridemia',
                'confidence': 'Medium',
                'reason': 'Elevated triglycerides',
                'recommendation': 'Reduce sugar, alcohol, and refined carbohydrates'
            })
        
        return risks
