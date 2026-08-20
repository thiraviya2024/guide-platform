# app/engines/clinical_engine/diabetes_engine.py
"""Diabetes Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class DiabetesEngine:
    """Evaluates Diabetes parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate Diabetes parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM diabetes_rules
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
                        'category': 'diabetes'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'diabetes'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on Diabetes results."""
        risks = []
        
        # Type 2 Diabetes (High Fasting Glucose + High HOMA-IR)
        if 'fasting_glucose' in results and 'homa_ir' in results:
            if results['fasting_glucose']['status'] in ['High', 'Very High'] and results['homa_ir']['status'] in ['Insulin Resistance', 'High', 'Very High']:
                risks.append({
                    'disease': 'Type 2 Diabetes',
                    'confidence': 'High',
                    'reason': 'High fasting glucose with insulin resistance',
                    'recommendation': 'Start metformin, lifestyle changes, monitor glucose regularly'
                })
        
        # Prediabetes (Impaired Fasting Glucose)
        if 'fasting_glucose' in results:
            if results['fasting_glucose']['status'] == 'Impaired':
                risks.append({
                    'disease': 'Prediabetes',
                    'confidence': 'High',
                    'reason': 'Impaired fasting glucose',
                    'recommendation': 'Lifestyle modification, weight loss, exercise, monitor glucose'
                })
        
        # Type 1 Diabetes (High Glucose + Low Insulin)
        if 'fasting_glucose' in results and 'insulin' in results:
            if results['fasting_glucose']['status'] in ['High', 'Very High'] and results['insulin']['status'] == 'Low':
                risks.append({
                    'disease': 'Type 1 Diabetes',
                    'confidence': 'High',
                    'reason': 'High glucose with low insulin',
                    'recommendation': 'Insulin therapy, endocrinology consult, monitor glucose'
                })
        
        # Insulin Resistance (High Insulin + Normal Fasting Glucose)
        if 'insulin' in results and 'fasting_glucose' in results:
            if results['insulin']['status'] in ['High', 'Very High'] and results['fasting_glucose']['status'] in ['Normal', 'Impaired']:
                risks.append({
                    'disease': 'Insulin Resistance',
                    'confidence': 'High',
                    'reason': 'High insulin with normal/impaired glucose',
                    'recommendation': 'Lifestyle modification, metformin, monitor glucose, weight loss'
                })
        
        # Poor Glycemic Control (High HbA1c)
        if 'hba1c' in results:
            if results['hba1c']['status'] in ['Poor Control', 'Diabetes']:
                risks.append({
                    'disease': 'Poor Glycemic Control',
                    'confidence': 'High',
                    'reason': f"HbA1c {results['hba1c']['status']} ({results['hba1c']['value']}%)",
                    'recommendation': 'Optimize medications, endocrinology consult, dietary changes, exercise'
                })
        
        # Diabetic Ketoacidosis Risk (Very High Glucose + Very Low Insulin)
        if 'fasting_glucose' in results and 'insulin' in results:
            if results['fasting_glucose']['status'] == 'Very High' and results['insulin']['status'] == 'Low':
                risks.append({
                    'disease': 'Diabetic Ketoacidosis Risk',
                    'confidence': 'High',
                    'reason': 'Very high glucose with low insulin',
                    'recommendation': 'MEDICAL EMERGENCY! Check ketones, insulin therapy, hydration, ER immediately'
                })
        
        # Hypoglycemia (Low Fasting Glucose)
        if 'fasting_glucose' in results and results['fasting_glucose']['status'] in ['Low', 'Very Low']:
            risks.append({
                'disease': 'Hypoglycemia',
                'confidence': 'High' if results['fasting_glucose']['status'] == 'Very Low' else 'Medium',
                'reason': f"Low fasting glucose ({results['fasting_glucose']['value']})",
                'recommendation': 'Consume 15g quick sugar, monitor glucose, adjust insulin/medications'
            })
        
        return risks
