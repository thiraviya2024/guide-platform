"""
Clinical Guidelines Engine for LipidAI

Provides clinical guideline recommendations from major organizations:
- AHA/ACC (American Heart Association / American College of Cardiology)
- ESC/EAS (European Society of Cardiology / European Atherosclerosis Society)
- NICE (National Institute for Health and Care Excellence)
- Indian Guidelines (CSI/API)
- IDF (International Diabetes Federation)

Follows the same session-per-call pattern as other engines.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from database.connection import SessionLocal

logger = logging.getLogger(__name__)


class GuidelinesEngine:
    """
    Engine for retrieving clinical guideline recommendations.
    
    Key design decisions:
    - Session-per-call pattern
    - Case-insensitive matching for disease names
    - Returns structured guideline data
    - Guidelines are cited, not invented by AI
    """
    
    def __init__(self):
        """Initialize the guidelines engine."""
        self._table_exists = None
    
    def _check_table_exists(self, db) -> bool:
        """Check if clinical_guidelines table exists."""
        try:
            result = db.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'clinical_guidelines'"
                ")"
            ))
            exists = result.scalar()
            self._table_exists = exists
            return exists
        except Exception as e:
            logger.error(f"Error checking clinical_guidelines table existence: {e}")
            return False
    
    def get_guidelines(self, disease_name: str, organization: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get clinical guidelines for a specific disease.
        
        Args:
            disease_name: Name of the disease
            organization: Optional filter by organization (AHA/ACC, ESC/EAS, NICE, etc.)
            
        Returns:
            List of guideline recommendations
        """
        if not disease_name:
            return []
        
        results = []
        
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    logger.warning("clinical_guidelines table does not exist")
                    return []
                
                # Build query with optional organization filter
                query = """
                    SELECT 
                        guideline_name,
                        guideline_organization,
                        disease_name,
                        recommendation,
                        recommendation_class,
                        evidence_level,
                        guideline_year,
                        key_parameters,
                        threshold_values,
                        citation,
                        url,
                        is_active
                    FROM clinical_guidelines
                    WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                    AND is_active = TRUE
                """
                
                params = {"disease_name": disease_name}
                
                if organization:
                    query += " AND LOWER(TRIM(guideline_organization)) = LOWER(TRIM(:organization))"
                    params["organization"] = organization
                
                query += " ORDER BY guideline_year DESC, guideline_organization"
                
                result = db.execute(text(query), params).fetchall()
                
                for row in result:
                    results.append({
                        'guideline_name': row.guideline_name,
                        'guideline_organization': row.guideline_organization,
                        'disease_name': row.disease_name,
                        'recommendation': row.recommendation,
                        'recommendation_class': row.recommendation_class,
                        'evidence_level': row.evidence_level,
                        'guideline_year': row.guideline_year,
                        'key_parameters': row.key_parameters or [],
                        'threshold_values': row.threshold_values or {},
                        'citation': row.citation,
                        'url': row.url,
                        'found': True
                    })
                    logger.info(f"Found guideline: {row.guideline_name} for {disease_name}")
                
                if not results:
                    logger.info(f"No guidelines found for disease: {disease_name}")
                
            except Exception as e:
                logger.error(f"Error in GuidelinesEngine.get_guidelines(): {e}")
                return []
        
        return results
    
    def get_guidelines_by_organization(self, organization: str) -> List[Dict[str, Any]]:
        """
        Get all guidelines from a specific organization.
        
        Args:
            organization: Organization name (AHA/ACC, ESC/EAS, NICE, etc.)
            
        Returns:
            List of all guidelines from that organization
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                query = text("""
                    SELECT 
                        guideline_name,
                        guideline_organization,
                        disease_name,
                        recommendation,
                        recommendation_class,
                        evidence_level,
                        guideline_year,
                        citation
                    FROM clinical_guidelines
                    WHERE LOWER(TRIM(guideline_organization)) = LOWER(TRIM(:organization))
                    AND is_active = TRUE
                    ORDER BY disease_name, guideline_year DESC
                """)
                
                result = db.execute(query, {"organization": organization}).fetchall()
                
                guidelines = []
                for row in result:
                    guidelines.append({
                        'guideline_name': row.guideline_name,
                        'guideline_organization': row.guideline_organization,
                        'disease_name': row.disease_name,
                        'recommendation': row.recommendation,
                        'recommendation_class': row.recommendation_class,
                        'evidence_level': row.evidence_level,
                        'guideline_year': row.guideline_year,
                        'citation': row.citation,
                        'found': True
                    })
                
                return guidelines
                
            except Exception as e:
                logger.error(f"Error in GuidelinesEngine.get_guidelines_by_organization(): {e}")
                return []
    
    def get_organizations(self) -> List[str]:
        """
        Get all unique guideline organizations.
        
        Returns:
            List of organization names
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                query = text("""
                    SELECT DISTINCT guideline_organization
                    FROM clinical_guidelines
                    WHERE is_active = TRUE
                    ORDER BY guideline_organization
                """)
                
                result = db.execute(query)
                organizations = [row[0] for row in result]
                logger.info(f"Found {len(organizations)} guideline organizations")
                return organizations
                
            except Exception as e:
                logger.error(f"Error in GuidelinesEngine.get_organizations(): {e}")
                return []
    
    def get_latest_guideline(self, disease_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent guideline for a disease.
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            Most recent guideline recommendation
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return None
                
                query = text("""
                    SELECT 
                        guideline_name,
                        guideline_organization,
                        disease_name,
                        recommendation,
                        recommendation_class,
                        evidence_level,
                        guideline_year,
                        key_parameters,
                        threshold_values,
                        citation,
                        url
                    FROM clinical_guidelines
                    WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                    AND is_active = TRUE
                    ORDER BY guideline_year DESC
                    LIMIT 1
                """)
                
                result = db.execute(query, {"disease_name": disease_name}).first()
                
                if result:
                    return {
                        'guideline_name': result.guideline_name,
                        'guideline_organization': result.guideline_organization,
                        'disease_name': result.disease_name,
                        'recommendation': result.recommendation,
                        'recommendation_class': result.recommendation_class,
                        'evidence_level': result.evidence_level,
                        'guideline_year': result.guideline_year,
                        'key_parameters': result.key_parameters or [],
                        'threshold_values': result.threshold_values or {},
                        'citation': result.citation,
                        'url': result.url,
                        'found': True
                    }
                else:
                    logger.info(f"No guidelines found for disease: {disease_name}")
                    return None
                
            except Exception as e:
                logger.error(f"Error in GuidelinesEngine.get_latest_guideline(): {e}")
                return None
    
    def get_recommendations_for_parameters(self, parameters: List[str]) -> List[Dict[str, Any]]:
        """
        Get guidelines relevant to specific parameters.
        
        Args:
            parameters: List of parameter names
            
        Returns:
            Guidelines that reference these parameters
        """
        if not parameters:
            return []
        
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                # Build query with multiple parameter matches
                # This uses JSONB containment to check if any parameter matches
                param_conditions = " OR ".join([
                    f"key_parameters @> '[\"{param}\"]'::jsonb" 
                    for param in parameters
                ])
                
                query = text(f"""
                    SELECT 
                        guideline_name,
                        guideline_organization,
                        disease_name,
                        recommendation,
                        recommendation_class,
                        evidence_level,
                        guideline_year,
                        key_parameters,
                        citation
                    FROM clinical_guidelines
                    WHERE ({param_conditions})
                    AND is_active = TRUE
                    ORDER BY guideline_year DESC
                    LIMIT 20
                """)
                
                result = db.execute(query).fetchall()
                
                recommendations = []
                for row in result:
                    recommendations.append({
                        'guideline_name': row.guideline_name,
                        'guideline_organization': row.guideline_organization,
                        'disease_name': row.disease_name,
                        'recommendation': row.recommendation,
                        'recommendation_class': row.recommendation_class,
                        'evidence_level': row.evidence_level,
                        'guideline_year': row.guideline_year,
                        'key_parameters': row.key_parameters or [],
                        'citation': row.citation,
                        'found': True
                    })
                
                return recommendations
                
            except Exception as e:
                logger.error(f"Error in GuidelinesEngine.get_recommendations_for_parameters(): {e}")
                return []


# Module-level singleton
_guidelines_engine = None


def get_guidelines_engine() -> GuidelinesEngine:
    """
    Get or create the singleton GuidelinesEngine instance.
    """
    global _guidelines_engine
    if _guidelines_engine is None:
        _guidelines_engine = GuidelinesEngine()
    return _guidelines_engine