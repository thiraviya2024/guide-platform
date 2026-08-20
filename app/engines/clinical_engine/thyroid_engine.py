# app/engines/clinical_engine/thyroid_engine.py
"""Thyroid Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class ThyroidEngine:
    """Evaluates Thyroid parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate Thyroid parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM thyroid_rules
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
                        'category': 'thyroid'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'thyroid'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on Thyroid results."""
        risks = []
        
        # Hypothyroidism (High TSH + Low T4)
        if 'tsh' in results and 't4' in results:
            if results['tsh']['status'] in ['High', 'Very High'] and results['t4']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Hypothyroidism',
                    'confidence': 'High',
                    'reason': 'High TSH and low T4',
                    'recommendation': 'Consider levothyroxine therapy, monitor TSH regularly'
                })
        
        # Hyperthyroidism (Low TSH + High T4)
        if 'tsh' in results and 't4' in results:
            if results['tsh']['status'] in ['Low', 'Very Low'] and results['t4']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Hyperthyroidism',
                    'confidence': 'High',
                    'reason': 'Low TSH and high T4',
                    'recommendation': 'Consider antithyroid medications, endocrinology consult'
                })
        
        # Subclinical Hypothyroidism (High TSH + Normal T4)
        if 'tsh' in results and 't4' in results:
            if results['tsh']['status'] in ['High', 'Very High'] and results['t4']['status'] == 'Normal':
                risks.append({
                    'disease': 'Subclinical Hypothyroidism',
                    'confidence': 'Medium',
                    'reason': 'High TSH with normal T4',
                    'recommendation': 'Monitor TSH, consider treatment if symptomatic or TSH > 10'
                })
        
        # Subclinical Hyperthyroidism (Low TSH + Normal T4)
        if 'tsh' in results and 't4' in results:
            if results['tsh']['status'] in ['Low', 'Very Low'] and results['t4']['status'] == 'Normal':
                risks.append({
                    'disease': 'Subclinical Hyperthyroidism',
                    'confidence': 'Medium',
                    'reason': 'Low TSH with normal T4',
                    'recommendation': 'Monitor TSH, assess for symptoms, consider treatment'
                })
        
        # Grave's Disease (Low TSH + High T3 + High T4)
        if 'tsh' in results and 't3' in results and 't4' in results:
            if results['tsh']['status'] in ['Low', 'Very Low'] and results['t3']['status'] in ['High', 'Very High'] and results['t4']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': "Grave's Disease",
                    'confidence': 'High',
                    'reason': 'Low TSH with high T3 and T4',
                    'recommendation': 'Check TSI antibodies, endocrinology consult, consider antithyroid therapy'
                })
        
        # Hashimoto's Thyroiditis (High TSH + Low T4)
        if 'tsh' in results and 't4' in results:
            if results['tsh']['status'] in ['High', 'Very High'] and results['t4']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': "Hashimoto's Thyroiditis",
                    'confidence': 'Medium',
                    'reason': 'High TSH with low T4 (autoimmune pattern)',
                    'recommendation': 'Check anti-TPO antibodies, endocrinology consult'
                })
        
        # Thyroid Storm (Very Low TSH + Very High T4)
        if 'tsh' in results and 't4' in results:
            if results['tsh']['status'] == 'Very Low' and results['t4']['status'] == 'Very High':
                risks.append({
                    'disease': 'Thyroid Storm',
                    'confidence': 'High',
                    'reason': 'Very low TSH and very high T4',
                    'recommendation': 'Medical emergency! Immediate endocrinology consult, consider beta-blockers, antithyroid drugs'
                })
        
        return risks
