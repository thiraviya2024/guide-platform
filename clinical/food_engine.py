"""
PostgreSQL-based Food Engine for LipidAI.
Provides disease-level food recommendations based on combination findings.
"""

from typing import List, Dict, Any
from sqlalchemy import text
from database.connection import SessionLocal
from utils.logger import logger


class FoodEngine:
    """Stateless food engine - session-per-call."""

    def evaluate(self, combination_findings: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Get food recommendations based on combination findings."""
        if not combination_findings:
            return []
        
        advice = []
        diseases = [f.get('result') for f in combination_findings if f.get('result')]
        
        if not diseases:
            return advice
        
        with SessionLocal() as db:
            # Try to get disease-level food advice
            query = text("""
                SELECT disease_name, food_suggestions
                FROM food_rules
                WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                AND is_active = TRUE
            """)
            
            for disease in diseases:
                try:
                    row = db.execute(query, {"disease_name": disease}).fetchone()
                    if row:
                        advice.append({
                            'disease': row.disease_name,
                            'food_suggestions': row.food_suggestions
                        })
                except Exception as e:
                    logger.error(f"FoodEngine error for {disease}: {e}")
        
        return advice


_food_engine = None

def get_food_engine() -> FoodEngine:
    global _food_engine
    if _food_engine is None:
        _food_engine = FoodEngine()
    return _food_engine

food_engine = get_food_engine()