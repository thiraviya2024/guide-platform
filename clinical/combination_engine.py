"""
PostgreSQL-based Combination Engine for LipidAI.
Reads multi-parameter rules from combination_rules table.
Session-per-call pattern for thread safety.
"""

import json
from typing import Dict, List, Any
from sqlalchemy import text
from database.connection import SessionLocal
from utils.logger import logger


class CombinationEngine:
    """Stateless combination engine - session-per-call."""

    def evaluate(self, rule_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate combination rules based on parameter statuses."""
        findings = []
        
        # Extract statuses
        status_map = {}
        for param, data in rule_results.items():
            if isinstance(data, dict) and 'status' in data:
                status_map[param] = data['status']
        
        if not status_map:
            return findings
        
        with SessionLocal() as db:
            query = text("""
                SELECT conditions, result, recommendation
                FROM combination_rules
                WHERE is_active = TRUE
            """)
            
            try:
                rows = db.execute(query).fetchall()
                
                for row in rows:
                    conditions = row.conditions
                    if not isinstance(conditions, list):
                        try:
                            conditions = json.loads(conditions) if isinstance(conditions, str) else []
                        except:
                            conditions = []
                    
                    # Check if all conditions match
                    all_match = True
                    for condition in conditions:
                        param = condition.get('parameter')
                        required_status = condition.get('status')
                        
                        if param not in status_map:
                            all_match = False
                            break
                        
                        actual_status = status_map[param]
                        if actual_status.lower() != required_status.lower():
                            all_match = False
                            break
                    
                    if all_match and conditions:
                        findings.append({
                            'result': row.result,
                            'recommendation': row.recommendation,
                            'triggered_by': conditions
                        })
                        
            except Exception as e:
                logger.error(f"CombinationEngine error: {e}")
                db.rollback()
        
        return findings


_combination_engine = None

def get_combination_engine() -> CombinationEngine:
    global _combination_engine
    if _combination_engine is None:
        _combination_engine = CombinationEngine()
    return _combination_engine

combination_engine = get_combination_engine()