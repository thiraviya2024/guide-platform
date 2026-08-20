# app/engines/clinical_engine/lft_engine.py
"""LFT Clinical Engine"""

from typing import Dict, List, Any
from sqlalchemy import text
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class LFTEngine:
    """Evaluates LFT parameters against clinical rules."""
    
    def evaluate(self, values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """Evaluate LFT parameters."""
        results = {}
        
        with SessionLocal() as db:
            for param, value in values.items():
                query = text("""
                    SELECT status, recommendation
                    FROM lft_rules
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
                        'category': 'lft'
                    }
                else:
                    results[param] = {
                        'value': value,
                        'status': 'Unknown',
                        'recommendation': 'No rule found',
                        'category': 'lft'
                    }
        
        return results
    
    def get_disease_risks(self, results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify disease risks based on LFT results."""
        risks = []
        
        # Hepatitis risk (High ALT + High AST)
        if 'alt' in results and 'ast' in results:
            if results['alt']['status'] in ['High', 'Very High'] and results['ast']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Hepatitis',
                    'confidence': 'High',
                    'reason': 'Elevated ALT and AST (liver enzymes)',
                    'recommendation': 'Check for viral hepatitis (A, B, C) and autoimmune hepatitis'
                })
        
        # Biliary Obstruction (High ALP + High GGT)
        if 'alp' in results and 'ggt' in results:
            if results['alp']['status'] in ['High', 'Very High'] and results['ggt']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Biliary Obstruction',
                    'confidence': 'High',
                    'reason': 'Elevated ALP and GGT (bile duct enzymes)',
                    'recommendation': 'Consider imaging (ultrasound, MRCP) to check bile ducts'
                })
        
        # Alcohol-Related Liver Disease (High GGT + High AST)
        if 'ggt' in results and 'ast' in results:
            if results['ggt']['status'] in ['High', 'Very High'] and results['ast']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Alcohol-Related Liver Disease',
                    'confidence': 'Medium',
                    'reason': 'Elevated GGT and AST',
                    'recommendation': 'Assess alcohol intake, consider cessation program'
                })
        
        # Liver Synthetic Failure (Low Albumin + High Total Bilirubin)
        if 'albumin' in results and 'total_bilirubin' in results:
            if results['albumin']['status'] in ['Low', 'Very Low'] and results['total_bilirubin']['status'] in ['High', 'Very High']:
                risks.append({
                    'disease': 'Liver Synthetic Failure',
                    'confidence': 'High',
                    'reason': 'Low albumin and high bilirubin',
                    'recommendation': 'Evaluate for cirrhosis or acute liver failure'
                })
        
        # Jaundice (High Total Bilirubin)
        if 'total_bilirubin' in results and results['total_bilirubin']['status'] in ['High', 'Very High']:
            risks.append({
                'disease': 'Jaundice',
                'confidence': 'High',
                'reason': 'Elevated total bilirubin',
                'recommendation': 'Evaluate for liver disease, biliary obstruction, or hemolysis'
            })
        
        # Malnutrition (Low Total Protein + Low Albumin)
        if 'total_protein' in results and 'albumin' in results:
            if results['total_protein']['status'] in ['Low', 'Very Low'] and results['albumin']['status'] in ['Low', 'Very Low']:
                risks.append({
                    'disease': 'Malnutrition or Protein-Losing Enteropathy',
                    'confidence': 'Medium',
                    'reason': 'Low protein and albumin',
                    'recommendation': 'Nutritional assessment and dietary consultation'
                })
        
        return risks
