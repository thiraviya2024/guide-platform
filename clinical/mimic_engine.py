"""
MIMIC-IV Integration Engine for LipidAI
Queries the pre-aggregated mimic_mapping table from PostgreSQL
For RESEARCH/EDUCATIONAL purposes only.
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

# MIMIC database connection
MIMIC_DATABASE_URL = os.getenv("MIMIC_DATABASE_URL")

# If MIMIC_DATABASE_URL is not set, use DATABASE_URL
if not MIMIC_DATABASE_URL:
    MIMIC_DATABASE_URL = os.getenv("DATABASE_URL")
    print("⚠️ MIMIC_DATABASE_URL not set, using DATABASE_URL")

# If still not set, use default
if not MIMIC_DATABASE_URL:
    MIMIC_DATABASE_URL = "postgresql://postgres:password@localhost:5432/lipidai"
    print("⚠️ Using default MIMIC_DATABASE_URL")


class MIMICEngine:
    """
    Queries the pre-aggregated MIMIC-IV data from mimic_mapping table.
    For RESEARCH/EDUCATIONAL purposes only.
    """
    
    def __init__(self):
        """Initialize the MIMIC engine."""
        self.engine = create_engine(MIMIC_DATABASE_URL, pool_pre_ping=True)
        self._connected = False
    
    def _check_connection(self):
        """Check if MIMIC database is accessible."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                self._connected = True
                logger.info("✅ Connected to MIMIC database")
                return True
        except Exception as e:
            logger.error(f"MIMIC connection failed: {e}")
            self._connected = False
            return False
    
    def get_evidence(self, disease_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get MIMIC-IV supporting evidence for a list of diseases.
        Queries the pre-aggregated mimic_mapping table.
        """
        if not disease_names:
            return {}
        
        if not self._check_connection():
            return {d: {'found': False, 'message': 'MIMIC database not connected'} 
                    for d in disease_names}
        
        results = {}
        
        with self.engine.connect() as conn:
            for disease in disease_names:
                try:
                    # Clean the disease name
                    clean_disease = disease.strip()
                    
                    # Query the mimic_mapping table
                    query = text("""
                        SELECT 
                            disease_name,
                            mimic_diagnosis_code,
                            mimic_diagnosis_description,
                            prevalence_in_mimic,
                            common_complications,
                            typical_lab_abnormalities,
                            common_medications,
                            mortality_rate,
                            average_length_of_stay_days,
                            supporting_evidence
                        FROM mimic_mapping
                        WHERE LOWER(TRIM(disease_name)) = LOWER(TRIM(:disease_name))
                        AND is_active = TRUE
                        LIMIT 1
                    """)
                    
                    result = conn.execute(query, {"disease_name": clean_disease}).first()
                    
                    if result:
                        results[disease] = {
                            'disease_name': result.disease_name,
                            'mimic_diagnosis_code': result.mimic_diagnosis_code,
                            'mimic_diagnosis_description': result.mimic_diagnosis_description,
                            'prevalence_in_mimic': float(result.prevalence_in_mimic) if result.prevalence_in_mimic else None,
                            'common_complications': result.common_complications or [],
                            'typical_lab_abnormalities': result.typical_lab_abnormalities or [],
                            'common_medications': result.common_medications or [],
                            'mortality_rate': float(result.mortality_rate) if result.mortality_rate else None,
                            'average_length_of_stay_days': float(result.average_length_of_stay_days) if result.average_length_of_stay_days else None,
                            'supporting_evidence': result.supporting_evidence,
                            'found': True
                        }
                        logger.info(f"Found MIMIC evidence for disease: {disease}")
                    else:
                        results[disease] = {
                            'disease_name': disease,
                            'found': False,
                            'message': f'No MIMIC evidence found for: {disease}'
                        }
                        
                except Exception as e:
                    logger.error(f"Error querying MIMIC for {disease}: {e}")
                    results[disease] = {
                        'disease_name': disease,
                        'found': False,
                        'message': f'Query error: {str(e)}'
                    }
        
        return results


# Module-level singleton
_mimic_engine = None


def get_mimic_engine() -> MIMICEngine:
    """Get or create the singleton MIMICEngine instance."""
    global _mimic_engine
    if _mimic_engine is None:
        _mimic_engine = MIMICEngine()
    return _mimic_engine


# Module-level instance for easy import
mimic_engine = get_mimic_engine()