# app/engines/clinical_engine/vitamins_engine.py
"""Vitamins Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class VitaminsEngine:
    """Evaluates Vitamins parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate Vitamins parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM vitamins_rules
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
                        'category': 'vitamins'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'vitamins'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on Vitamins results."""
        risks = []
        
        # Vitamin B12 Deficiency
        if 'vitamin_b12' in results:
            if results['vitamin_b12']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Vitamin B12 Deficiency',
                    'confidence': 'High' if results['vitamin_b12']['status'] == 'Very Low' else 'Medium',
                    'reason': f"Low Vitamin B12 ({results['vitamin_b12']['status']})",
                    'recommendation': 'B12 supplementation, dietary changes (meat, fish, dairy), monitor levels'
                })
        
        # Vitamin D Deficiency
        if 'vitamin_d' in results:
            if results['vitamin_d']['status'] in ['Deficient', 'Very Deficient']:
                risks.append({
                    'disease': 'Vitamin D Deficiency',
                    'confidence': 'High' if results['vitamin_d']['status'] == 'Very Deficient' else 'High',
                    'reason': f"Vitamin D {results['vitamin_d']['status']}",
                    'recommendation': 'Vitamin D3 supplementation, sun exposure, monitor levels'
                })
        
        # Vitamin D Toxicity
        if 'vitamin_d' in results:
            if results['vitamin_d']['status'] == 'Toxic':
                risks.append({
                    'disease': 'Vitamin D Toxicity',
                    'confidence': 'High',
                    'reason': 'Very high Vitamin D level',
                    'recommendation': 'Stop supplementation, hydration, monitor calcium levels, consult physician'
                })
        
        # Iron Deficiency Anemia (Low Iron + Low Ferritin)
        if 'iron' in results and 'ferritin' in results:
            if results['iron']['status'] in ['Low', 'Very Low'] and results['ferritin']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Iron Deficiency Anemia',
                    'confidence': 'High',
                    'reason': 'Low iron and ferritin',
                    'recommendation': 'Iron supplementation, dietary changes (red meat, spinach), monitor levels'
                })
        
        # Hemochromatosis (High Iron + High Ferritin)
        if 'iron' in results and 'ferritin' in results:
            if results['iron']['status'] in ['High', 'Very High'] and results['ferritin']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Hemochromatosis',
                    'confidence': 'High',
                    'reason': 'High iron and ferritin (iron overload)',
                    'recommendation': 'Genetic testing, phlebotomy, iron chelation, hepatology consult'
                })
        
        # Folate Deficiency
        if 'folate' in results:
            if results['folate']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Folate Deficiency',
                    'confidence': 'High' if results['folate']['status'] == 'Very Low' else 'Medium',
                    'reason': f"Low Folate ({results['folate']['status']})",
                    'recommendation': 'Folic acid supplementation, dietary changes (leafy greens, legumes), monitor levels'
                })
        
        # Megaloblastic Anemia (Low B12 + Low Folate)
        if 'vitamin_b12' in results and 'folate' in results:
            if results['vitamin_b12']['status'] in ['Low', 'Very Low'] and results['folate']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Megaloblastic Anemia',
                    'confidence': 'High',
                    'reason': 'Low B12 and folate',
                    'recommendation': 'B12 and folate supplementation, dietary changes, hematology consult'
                })
        
        return risks
