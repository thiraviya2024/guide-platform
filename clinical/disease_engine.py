"""
Disease Prediction Engine for LipidAI

Predicts diseases based on combination_engine results and per-parameter statuses.
Follows the same session-per-call pattern as other engines.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from database.connection import SessionLocal

logger = logging.getLogger(__name__)


class DiseaseEngine:
    """
    Engine for predicting diseases based on lipid profile patterns.
    
    Key design decisions:
    - Session-per-call pattern
    - Case-insensitive matching for disease names
    - Uses diagnosis_criteria JSONB to match against rule_results
    - Returns structured disease data with confidence scores
    """
    
    def __init__(self):
        """Initialize the disease engine."""
        self._table_exists = None
    
    def _check_table_exists(self, db) -> bool:
        """Check if disease_rules table exists."""
        try:
            result = db.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'disease_rules'"
                ")"
            ))
            exists = result.scalar()
            self._table_exists = exists
            return exists
        except Exception as e:
            logger.error(f"Error checking disease_rules table existence: {e}")
            return False
    
    def predict(self, rule_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Predict diseases based on rule evaluation results.
        
        Args:
            rule_results: Dictionary from rule_engine.evaluate() containing per-parameter results
                         Expected format: {'parameter_name': {'status': 'High', 'value': 150, ...}}
        
        Returns:
            List of predicted diseases with details:
            [
                {
                    'disease_name': str,
                    'description': str,
                    'severity_level': str,
                    'diagnosis_criteria': list,
                    'clinical_guidelines': str,
                    'management_strategy': str,
                    'referral_needed': bool,
                    'specialist_type': str,
                    'matched_criteria': list,  # Which criteria matched
                    'confidence_score': float,  # % of criteria matched
                    'found': bool
                }
            ]
        """
        if not rule_results:
            return []
        
        # Extract statuses from rule_results
        status_map = {}
        for param, data in rule_results.items():
            if isinstance(data, dict) and 'status' in data:
                status_map[param] = data['status']
        
        if not status_map:
            logger.warning("No statuses found in rule_results")
            return []
        
        predictions = []
        
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    logger.warning("disease_rules table does not exist")
                    return []
                
                # Get all active disease rules
                query = text("""
                    SELECT 
                        disease_name,
                        description,
                        severity_level,
                        diagnosis_criteria,
                        clinical_guidelines,
                        management_strategy,
                        referral_needed,
                        specialist_type,
                        is_active
                    FROM disease_rules
                    WHERE is_active = TRUE
                """)
                
                diseases = db.execute(query).fetchall()
                
                for disease in diseases:
                    # Parse diagnosis criteria
                    criteria = disease.diagnosis_criteria
                    if not criteria:
                        continue
                    
                    # Check which criteria match
                    matched = []
                    total_criteria = len(criteria)
                    
                    for criterion in criteria:
                        param = criterion.get('parameter')
                        required_status = criterion.get('status')
                        
                        if param in status_map:
                            actual_status = status_map[param]
                            if actual_status.lower() == required_status.lower():
                                matched.append({
                                    'parameter': param,
                                    'required': required_status,
                                    'actual': actual_status,
                                    'matched': True
                                })
                            else:
                                matched.append({
                                    'parameter': param,
                                    'required': required_status,
                                    'actual': actual_status,
                                    'matched': False
                                })
                    
                    # Calculate confidence (percentage of criteria met)
                    matched_count = sum(1 for m in matched if m['matched'])
                    confidence = (matched_count / total_criteria) * 100 if total_criteria > 0 else 0
                    
                    # Only include disease if at least 50% of criteria match
                    # (This threshold can be adjusted)
                    if confidence >= 50:
                        predictions.append({
                            'disease_name': disease.disease_name,
                            'description': disease.description,
                            'severity_level': disease.severity_level,
                            'diagnosis_criteria': criteria,
                            'clinical_guidelines': disease.clinical_guidelines,
                            'management_strategy': disease.management_strategy,
                            'referral_needed': disease.referral_needed,
                            'specialist_type': disease.specialist_type,
                            'matched_criteria': matched,
                            'confidence_score': round(confidence, 1),
                            'found': True
                        })
                        logger.info(f"Predicted disease: {disease.disease_name} (confidence: {confidence:.1f}%)")
                
            except Exception as e:
                logger.error(f"Error in DiseaseEngine.predict(): {e}")
                return []
        
        # Sort by confidence score (highest first)
        predictions.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return predictions
    
    def get_all_diseases(self) -> List[Dict[str, Any]]:
        """
        Get all active diseases with their criteria.
        
        Returns:
            List of disease definitions
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                query = text("""
                    SELECT 
                        disease_name,
                        description,
                        severity_level,
                        diagnosis_criteria,
                        clinical_guidelines,
                        management_strategy,
                        referral_needed,
                        specialist_type
                    FROM disease_rules
                    WHERE is_active = TRUE
                    ORDER BY severity_level DESC, disease_name
                """)
                
                results = db.execute(query).fetchall()
                
                diseases = []
                for row in results:
                    diseases.append({
                        'disease_name': row.disease_name,
                        'description': row.description,
                        'severity_level': row.severity_level,
                        'diagnosis_criteria': row.diagnosis_criteria,
                        'clinical_guidelines': row.clinical_guidelines,
                        'management_strategy': row.management_strategy,
                        'referral_needed': row.referral_needed,
                        'specialist_type': row.specialist_type
                    })
                
                return diseases
                
            except Exception as e:
                logger.error(f"Error in DiseaseEngine.get_all_diseases(): {e}")
                return []
    
    def get_disease_by_name(self, disease_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific disease by name.
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            Disease definition dict or None if not found
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return None
                
                query = text("""
                    SELECT 
                        disease_name,
                        description,
                        severity_level,
                        diagnosis_criteria,
                        clinical_guidelines,
                        management_strategy,
                        referral_needed,
                        specialist_type
                    FROM disease_rules
                    WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                    AND is_active = TRUE
                """)
                
                result = db.execute(query, {"disease_name": disease_name}).first()
                
                if result:
                    return {
                        'disease_name': result.disease_name,
                        'description': result.description,
                        'severity_level': result.severity_level,
                        'diagnosis_criteria': result.diagnosis_criteria,
                        'clinical_guidelines': result.clinical_guidelines,
                        'management_strategy': result.management_strategy,
                        'referral_needed': result.referral_needed,
                        'specialist_type': result.specialist_type
                    }
                
                return None
                
            except Exception as e:
                logger.error(f"Error in DiseaseEngine.get_disease_by_name(): {e}")
                return None


# Module-level singleton
_disease_engine = None


def get_disease_engine() -> DiseaseEngine:
    """
    Get or create the singleton DiseaseEngine instance.
    """
    global _disease_engine
    if _disease_engine is None:
        _disease_engine = DiseaseEngine()
    return _disease_engine