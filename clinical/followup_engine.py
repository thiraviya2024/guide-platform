"""
Follow-up Tests Recommendation Engine for LipidAI

Recommends appropriate follow-up tests based on detected diseases and
lipid profile abnormalities. Keyed by disease_name for comprehensive
test recommendations.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from database.connection import SessionLocal

logger = logging.getLogger(__name__)


class FollowupEngine:
    """
    Engine for recommending follow-up tests based on detected diseases.
    
    Key design decisions:
    - Session-per-call pattern
    - Case-insensitive matching
    - Test recommendations categorized by priority
    - Includes rationale and guideline citations
    """
    
    def __init__(self):
        """Initialize the followup engine."""
        self._table_exists = None
    
    def _check_table_exists(self, db) -> bool:
        """Check if followup_tests table exists."""
        try:
            result = db.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'followup_tests'"
                ")"
            ))
            exists = result.scalar()
            self._table_exists = exists
            return exists
        except Exception as e:
            logger.error(f"Error checking followup_tests table existence: {e}")
            return False
    
    def get_recommendations(self, diseases: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get follow-up test recommendations for a list of diseases.
        
        Args:
            diseases: List of disease names
            
        Returns:
            Dictionary mapping disease_name -> list of test recommendations
        """
        if not diseases:
            return {}
        
        results = {}
        
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    logger.warning("followup_tests table does not exist")
                    return {}
                
                for disease in diseases:
                    clean_disease = disease.strip()
                    disease_tests = []
                    
                    # Query for disease-specific tests
                    query = text("""
                        SELECT 
                            disease_name,
                            test_name,
                            test_category,
                            frequency,
                            priority,
                            rationale,
                            baseline_value_needed,
                            target_range,
                            abnormal_threshold,
                            clinical_guideline_citation
                        FROM followup_tests
                        WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                        AND is_active = TRUE
                        ORDER BY 
                            CASE priority
                                WHEN 'High' THEN 1
                                WHEN 'Medium' THEN 2
                                WHEN 'Low' THEN 3
                            END,
                            test_category,
                            test_name
                    """)
                    
                    result = db.execute(query, {"disease_name": clean_disease}).fetchall()
                    
                    for row in result:
                        disease_tests.append({
                            'disease_name': row.disease_name,
                            'test_name': row.test_name,
                            'test_category': row.test_category,
                            'frequency': row.frequency,
                            'priority': row.priority,
                            'rationale': row.rationale,
                            'baseline_value_needed': row.baseline_value_needed,
                            'target_range': row.target_range,
                            'abnormal_threshold': row.abnormal_threshold,
                            'clinical_guideline_citation': row.clinical_guideline_citation,
                            'found': True
                        })
                    
                    if disease_tests:
                        results[disease] = disease_tests
                        logger.info(f"Found {len(disease_tests)} follow-up tests for {disease}")
                    else:
                        # Check if disease exists in general recommendations
                        general_query = text("""
                            SELECT 
                                disease_name,
                                test_name,
                                test_category,
                                frequency,
                                priority,
                                rationale,
                                baseline_value_needed,
                                target_range,
                                abnormal_threshold,
                                clinical_guideline_citation
                            FROM followup_tests
                            WHERE LOWER(TRIM(disease_name)) = 'general lipid management'
                            AND is_active = TRUE
                            ORDER BY 
                                CASE priority
                                    WHEN 'High' THEN 1
                                    WHEN 'Medium' THEN 2
                                    WHEN 'Low' THEN 3
                                END
                        """)
                        
                        general_result = db.execute(general_query).fetchall()
                        
                        for row in general_result:
                            disease_tests.append({
                                'disease_name': row.disease_name,
                                'test_name': row.test_name,
                                'test_category': row.test_category,
                                'frequency': row.frequency,
                                'priority': row.priority,
                                'rationale': row.rationale,
                                'baseline_value_needed': row.baseline_value_needed,
                                'target_range': row.target_range,
                                'abnormal_threshold': row.abnormal_threshold,
                                'clinical_guideline_citation': row.clinical_guideline_citation,
                                'found': True
                            })
                        
                        if disease_tests:
                            results[disease] = disease_tests
                            logger.info(f"Using general follow-up tests for {disease}")
                        else:
                            logger.info(f"No follow-up tests found for disease: {disease}")
                
            except Exception as e:
                logger.error(f"Error in FollowupEngine.get_recommendations(): {e}")
                return {}
        
        return results
    
    def get_all_recommendations(self, diseases: List[str]) -> List[Dict[str, Any]]:
        """
        Get all follow-up test recommendations across diseases, deduplicated.
        
        Args:
            diseases: List of disease names
            
        Returns:
            List of unique test recommendations with highest priority
        """
        if not diseases:
            return []
        
        # Get recommendations for each disease
        disease_recommendations = self.get_recommendations(diseases)
        
        # Deduplicate by test_name
        unique_tests = {}
        
        for disease, tests in disease_recommendations.items():
            for test in tests:
                test_name = test['test_name']
                
                # Keep the highest priority version
                if test_name not in unique_tests:
                    unique_tests[test_name] = test
                else:
                    # Compare priorities
                    priority_order = {'High': 1, 'Medium': 2, 'Low': 3}
                    existing_priority = priority_order.get(unique_tests[test_name]['priority'], 4)
                    new_priority = priority_order.get(test['priority'], 4)
                    
                    if new_priority < existing_priority:
                        unique_tests[test_name] = test
        
        # Convert to list and sort by priority
        result = list(unique_tests.values())
        result.sort(key=lambda x: {'High': 1, 'Medium': 2, 'Low': 3}.get(x['priority'], 4))
        
        return result
    
    def get_tests_by_category(self, diseases: List[str], category: str) -> List[Dict[str, Any]]:
        """
        Get follow-up test recommendations filtered by category.
        
        Args:
            diseases: List of disease names
            category: Test category ('Lab', 'Imaging', 'Clinical', 'Screening')
            
        Returns:
            List of test recommendations in the specified category
        """
        all_tests = self.get_all_recommendations(diseases)
        return [test for test in all_tests if test['test_category'].lower() == category.lower()]
    
    def get_high_priority_tests(self, diseases: List[str]) -> List[Dict[str, Any]]:
        """
        Get only high-priority follow-up tests.
        
        Args:
            diseases: List of disease names
            
        Returns:
            List of high-priority test recommendations
        """
        all_tests = self.get_all_recommendations(diseases)
        return [test for test in all_tests if test['priority'] == 'High']
    
    def get_tests_by_parameter(self, parameter: str) -> List[Dict[str, Any]]:
        """
        Get follow-up tests relevant to a specific parameter.
        
        Args:
            parameter: Parameter name (ldl, triglycerides, etc.)
            
        Returns:
            List of tests that monitor this parameter
        """
        # Map parameters to their monitoring tests
        parameter_tests = {
            'ldl': ['Lipid Profile (LDL)'],
            'triglycerides': ['Lipid Profile (Triglycerides)'],
            'hdl': ['Lipid Profile (HDL)'],
            'total_cholesterol': ['Lipid Profile (Total Cholesterol)'],
            'glucose': ['Fasting Blood Glucose', 'HbA1c'],
            'liver': ['Liver Function Tests (ALT, AST, Alkaline Phosphatase)'],
            'blood_pressure': ['Blood Pressure Measurement'],
            'weight': ['Body Mass Index (BMI) and Waist Circumference']
        }
        
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                test_names = parameter_tests.get(parameter, [])
                if not test_names:
                    return []
                
                # Build query for test names
                test_conditions = " OR ".join([
                    f"test_name ILIKE '%{test_name}%'" 
                    for test_name in test_names
                ])
                
                query = text(f"""
                    SELECT 
                        disease_name,
                        test_name,
                        test_category,
                        frequency,
                        priority,
                        rationale,
                        target_range,
                        abnormal_threshold,
                        clinical_guideline_citation
                    FROM followup_tests
                    WHERE ({test_conditions})
                    AND is_active = TRUE
                    ORDER BY priority
                """)
                
                result = db.execute(query).fetchall()
                
                tests = []
                for row in result:
                    tests.append({
                        'disease_name': row.disease_name,
                        'test_name': row.test_name,
                        'test_category': row.test_category,
                        'frequency': row.frequency,
                        'priority': row.priority,
                        'rationale': row.rationale,
                        'target_range': row.target_range,
                        'abnormal_threshold': row.abnormal_threshold,
                        'clinical_guideline_citation': row.clinical_guideline_citation,
                        'found': True
                    })
                
                return tests
                
            except Exception as e:
                logger.error(f"Error in FollowupEngine.get_tests_by_parameter(): {e}")
                return []


# Module-level singleton
_followup_engine = None


def get_followup_engine() -> FollowupEngine:
    """
    Get or create the singleton FollowupEngine instance.
    """
    global _followup_engine
    if _followup_engine is None:
        _followup_engine = FollowupEngine()
    return _followup_engine