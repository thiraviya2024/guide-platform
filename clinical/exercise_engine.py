"""
Exercise Rules Engine for LipidAI

Provides disease-level exercise recommendations based on detected conditions
from the combination_engine. Follows the same session-per-call pattern as
rule_engine.py and food_engine.py to avoid connection pooling issues.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from database.connection import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)


class ExerciseEngine:
    """
    Engine for retrieving exercise recommendations from PostgreSQL.
    
    Key design decisions:
    - Session-per-call pattern: opens a new Session for each evaluate() call
    - Case-insensitive matching: uses LOWER(TRIM()) for disease_name matching
    - Returns structured exercise data matching the table columns
    - No hardcoded clinical thresholds
    """
    
    def __init__(self):
        """Initialize the exercise engine."""
        self._table_exists = None
    
    def _check_table_exists(self, db) -> bool:
        """Check if exercise_rules table exists in the database."""
        try:
            result = db.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'exercise_rules'"
                ")"
            ))
            exists = result.scalar()
            self._table_exists = exists
            return exists
        except Exception as e:
            logger.error(f"Error checking exercise_rules table existence: {e}")
            return False
    
    def evaluate(self, disease_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve exercise recommendations for a list of diseases.
        
        Args:
            disease_list: List of disease names (e.g., ['Hyperlipidemia', 'High LDL Cholesterol'])
            
        Returns:
            Dictionary mapping disease_name -> exercise_data dict with keys:
                - disease_name: str
                - exercise_type: str
                - frequency: str
                - intensity: str
                - duration: str
                - precautions: str
                - contraindications: str
                - special_considerations: str
                - is_active: bool
                - found: bool (indicates if rule was found)
            
            Example:
            {
                'Hyperlipidemia': {
                    'disease_name': 'Hyperlipidemia',
                    'exercise_type': 'Aerobic exercise...',
                    'frequency': '5 days per week',
                    'intensity': 'Moderate (40-60% of heart rate reserve)',
                    'duration': '30-45 minutes per session',
                    'precautions': 'Start gradually...',
                    'contraindications': 'Uncontrolled hypertension...',
                    'special_considerations': 'Can be split...',
                    'is_active': True,
                    'found': True
                }
            }
        """
        if not disease_list:
            return {}
        
        results = {}
        
        # Use session-per-call pattern to avoid "idle in transaction" connections
        with SessionLocal() as db:
            try:
                # Check if table exists
                if not self._check_table_exists(db):
                    logger.warning("exercise_rules table does not exist in the database")
                    # Return empty results for all diseases
                    for disease in disease_list:
                        results[disease] = self._create_empty_result(disease)
                    return results
                
                # Build the query with case-insensitive matching
                # We'll query for each disease individually to maintain the pattern
                for disease in disease_list:
                    # Clean the disease name
                    clean_disease = disease.strip()
                    
                    # Query with case-insensitive matching
                    query = text("""
                        SELECT 
                            disease_name,
                            exercise_type,
                            frequency,
                            intensity,
                            duration,
                            precautions,
                            contraindications,
                            special_considerations,
                            is_active
                        FROM exercise_rules
                        WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                        AND is_active = TRUE
                        LIMIT 1
                    """)
                    
                    result = db.execute(query, {"disease_name": clean_disease}).first()
                    
                    if result:
                        # Map column names to dict keys
                        results[disease] = {
                            'disease_name': result.disease_name,
                            'exercise_type': result.exercise_type,
                            'frequency': result.frequency,
                            'intensity': result.intensity,
                            'duration': result.duration,
                            'precautions': result.precautions,
                            'contraindications': result.contraindications,
                            'special_considerations': result.special_considerations,
                            'is_active': result.is_active,
                            'found': True
                        }
                        logger.info(f"Found exercise rule for disease: {disease}")
                    else:
                        # No rule found - return empty result
                        logger.info(f"No exercise rule found for disease: {disease}")
                        results[disease] = self._create_empty_result(disease)
                        
            except Exception as e:
                logger.error(f"Error in ExerciseEngine.evaluate(): {e}")
                # Return empty results for all diseases on error
                for disease in disease_list:
                    results[disease] = self._create_empty_result(disease)
        
        return results
    
    def _create_empty_result(self, disease_name: str) -> Dict[str, Any]:
        """
        Create an empty result structure when no exercise rule is found.
        
        This ensures consistent return shape even when data is missing.
        """
        return {
            'disease_name': disease_name,
            'exercise_type': 'No exercise recommendation available',
            'frequency': 'No exercise recommendation available',
            'intensity': 'No exercise recommendation available',
            'duration': 'No exercise recommendation available',
            'precautions': 'Consult your healthcare provider for personalized exercise advice',
            'contraindications': 'No specific contraindications identified',
            'special_considerations': 'No special considerations identified',
            'is_active': False,
            'found': False
        }
    
    def get_disease_list(self) -> List[str]:
        """
        Get a list of all active diseases in the exercise_rules table.
        
        Useful for populating UI dropdowns or for debugging.
        
        Returns:
            List of disease names (strings)
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                query = text("""
                    SELECT DISTINCT disease_name
                    FROM exercise_rules
                    WHERE is_active = TRUE
                    ORDER BY disease_name
                """)
                
                result = db.execute(query)
                diseases = [row[0] for row in result]
                logger.info(f"Retrieved {len(diseases)} active diseases from exercise_rules")
                return diseases
                
            except Exception as e:
                logger.error(f"Error in ExerciseEngine.get_disease_list(): {e}")
                return []
    
    def add_or_update_rule(
        self,
        disease_name: str,
        exercise_type: str,
        frequency: str,
        intensity: str,
        duration: str,
        precautions: Optional[str] = None,
        contraindications: Optional[str] = None,
        special_considerations: Optional[str] = None,
        is_active: bool = True
    ) -> bool:
        """
        Add or update an exercise rule in the database.
        
        This is a utility method for administrative purposes.
        
        Args:
            disease_name: The disease name (will be trimmed and normalized)
            exercise_type: Type of exercise recommended
            frequency: How often to exercise
            intensity: Exercise intensity levels
            duration: How long each session should be
            precautions: Safety precautions
            contraindications: When to avoid exercise
            special_considerations: Patient-specific considerations
            is_active: Whether this rule is active
            
        Returns:
            True if successful, False otherwise
        """
        if not disease_name or not exercise_type:
            logger.error("disease_name and exercise_type are required")
            return False
        
        # Clean the disease name
        clean_disease = disease_name.strip()
        
        with SessionLocal() as db:
            try:
                # Check if table exists
                if not self._check_table_exists(db):
                    logger.error("exercise_rules table does not exist")
                    return False
                
                # Check if rule already exists
                check_query = text("""
                    SELECT id FROM exercise_rules
                    WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                """)
                existing = db.execute(check_query, {"disease_name": clean_disease}).first()
                
                if existing:
                    # Update existing rule
                    update_query = text("""
                        UPDATE exercise_rules
                        SET 
                            exercise_type = :exercise_type,
                            frequency = :frequency,
                            intensity = :intensity,
                            duration = :duration,
                            precautions = :precautions,
                            contraindications = :contraindications,
                            special_considerations = :special_considerations,
                            is_active = :is_active,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, {
                        'exercise_type': exercise_type,
                        'frequency': frequency,
                        'intensity': intensity,
                        'duration': duration,
                        'precautions': precautions,
                        'contraindications': contraindications,
                        'special_considerations': special_considerations,
                        'is_active': is_active,
                        'id': existing[0]
                    })
                    logger.info(f"Updated exercise rule for disease: {clean_disease}")
                else:
                    # Insert new rule
                    insert_query = text("""
                        INSERT INTO exercise_rules (
                            disease_name,
                            exercise_type,
                            frequency,
                            intensity,
                            duration,
                            precautions,
                            contraindications,
                            special_considerations,
                            is_active,
                            created_at,
                            updated_at
                        ) VALUES (
                            :disease_name,
                            :exercise_type,
                            :frequency,
                            :intensity,
                            :duration,
                            :precautions,
                            :contraindications,
                            :special_considerations,
                            :is_active,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                    """)
                    
                    db.execute(insert_query, {
                        'disease_name': clean_disease,
                        'exercise_type': exercise_type,
                        'frequency': frequency,
                        'intensity': intensity,
                        'duration': duration,
                        'precautions': precautions,
                        'contraindications': contraindications,
                        'special_considerations': special_considerations,
                        'is_active': is_active
                    })
                    logger.info(f"Inserted new exercise rule for disease: {clean_disease}")
                
                db.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error in ExerciseEngine.add_or_update_rule(): {e}")
                db.rollback()
                return False


# Module-level singleton
_exercise_engine = None


def get_exercise_engine() -> ExerciseEngine:
    """
    Get or create the singleton ExerciseEngine instance.
    
    This follows the same pattern as rule_engine.py and combination_engine.py.
    The engine itself is stateless (all state is in the database),
    so a singleton is safe and efficient.
    """
    global _exercise_engine
    if _exercise_engine is None:
        _exercise_engine = ExerciseEngine()
    return _exercise_engine