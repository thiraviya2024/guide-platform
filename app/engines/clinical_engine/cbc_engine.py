# app/engines/clinical_engine/cbc_engine.py
"""
CBC Clinical Engine
"""

from typing import Dict, List, Any, Optional
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class CBCEngine:
    """Evaluates CBC parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float], gender: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Evaluate CBC parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM cbc_rules
                    WHERE parameter = :param
                    AND (
                        (level_name LIKE '%Male%' AND :gender = 'Male')
                        OR (level_name LIKE '%Female%' AND :gender = 'Female')
                        OR (level_name NOT LIKE '%Male%' AND level_name NOT LIKE '%Female%')
                    )
                    AND min_value <= :value
                    AND max_value >= :value
                    AND is_active = TRUE
                    ORDER BY id
                    LIMIT 1
                """)
                
                row = db.execute(query, {"param": param, "value": value, "gender": gender or "None"}).fetchone()
                
                if not row:
                    query_no_gender = text("""
                        SELECT status, recommendation
                        FROM cbc_rules
                        WHERE parameter = :param
                        AND level_name NOT LIKE '%Male%' 
                        AND level_name NOT LIKE '%Female%'
                        AND min_value <= :value
                        AND max_value >= :value
                        AND is_active = TRUE
                        ORDER BY id
                        LIMIT 1
                    """)
                    row = db.execute(query_no_gender, {"param": param, "value": value}).fetchone()
                
                if row:
                    results[param] = {
                        'value': value,
                        'status': row.status,
                        'recommendation': row.recommendation,
                        'category': 'cbc'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'cbc'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on CBC results."""
        risks = []
        
        # Anemia risk
        if 'hemoglobin' in results and 'rbc' in results:
            if results['hemoglobin']['status'] == 'Low' and results['rbc']['status'] == 'Low':
                risks.append({
                    'disease': 'Anemia',
                    'confidence': 'High',
                    'reason': 'Low hemoglobin and low RBC count',
                    'recommendation': 'Check iron, B12, and folate levels'
                })
        
        # Bacterial infection
        if 'wbc' in results and 'neutrophils' in results:
            if results['wbc']['status'] == 'High' and results['neutrophils']['status'] == 'High':
                risks.append({
                    'disease': 'Bacterial Infection',
                    'confidence': 'High',
                    'reason': 'Elevated WBC and neutrophils',
                    'recommendation': 'Clinical correlation needed'
                })
        
        # Viral infection
        if 'wbc' in results and 'lymphocytes' in results:
            if results['wbc']['status'] == 'High' and results['lymphocytes']['status'] == 'High':
                risks.append({
                    'disease': 'Viral Infection',
                    'confidence': 'Medium',
                    'reason': 'Elevated WBC and lymphocytes',
                    'recommendation': 'Clinical correlation needed'
                })
        
        # Thrombocytopenia
        if 'platelets' in results and results['platelets']['status'] == 'Low':
            risks.append({
                'disease': 'Thrombocytopenia',
                'confidence': 'High',
                'reason': 'Low platelet count',
                'recommendation': 'Consult hematologist'
            })
        
        # Leukopenia
        if 'wbc' in results and results['wbc']['status'] == 'Low':
            risks.append({
                'disease': 'Leukopenia',
                'confidence': 'Medium',
                'reason': 'Low WBC count',
                'recommendation': 'Check immunity status'
            })
        
        return risks