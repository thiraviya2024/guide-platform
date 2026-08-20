"""
MIMIC-IV Direct Query Engine
For RESEARCH/EDUCATIONAL purposes only.
Queries the MIMIC-IV demo database directly.
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

# MIMIC database connection (separate from main database)
MIMIC_DATABASE_URL = os.getenv("MIMIC_DATABASE_URL", 
    "postgresql://postgres:Thiya%402020@localhost:5432/mimic_demo")


class MIMICQueryEngine:
    """
    Direct query engine for MIMIC-IV demo data.
    For RESEARCH/EDUCATIONAL purposes only.
    """
    
    def __init__(self):
        """Initialize the MIMIC query engine."""
        self.engine = create_engine(MIMIC_DATABASE_URL, pool_pre_ping=True)
        self._connected = False
    
    def test_connection(self):
        """Test connection to MIMIC database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                self._connected = True
                print("✅ Connected to MIMIC-IV demo database")
                return True
        except Exception as e:
            print(f"❌ MIMIC connection failed: {e}")
            self._connected = False
            return False
    
    def get_disease_prevalence(self):
        """
        Get prevalence of lipid-related conditions from MIMIC-IV.
        RESEARCH USE ONLY.
        """
        if not self._connected:
            return []
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        icd_code,
                        COUNT(DISTINCT subject_id) as patient_count,
                        COUNT(*) as diagnosis_count,
                        ROUND(COUNT(DISTINCT subject_id) * 100.0 / (
                            SELECT COUNT(DISTINCT subject_id) FROM patients
                        ), 2) as prevalence_percent
                    FROM diagnoses_icd
                    WHERE icd_code IN ('E78.5', 'E78.01', 'E88.81', 'I25.10', 'E78.2', 'E78.1', 'E78.6')
                    GROUP BY icd_code
                    ORDER BY patient_count DESC
                """)
                
                results = conn.execute(query)
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting prevalence: {e}")
            return []
    
    def get_patient_characteristics(self, icd_code: str, limit: int = 100):
        """
        Get patient characteristics for a specific ICD code.
        RESEARCH USE ONLY.
        """
        if not self._connected:
            return []
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        p.subject_id,
                        p.gender,
                        p.anchor_age,
                        a.admittime,
                        a.dischtime,
                        a.hospital_expire_flag,
                        a.admission_type
                    FROM patients p
                    JOIN admissions a ON p.subject_id = a.subject_id
                    JOIN diagnoses_icd d ON a.hadm_id = d.hadm_id
                    WHERE d.icd_code = :icd_code
                    LIMIT :limit
                """)
                
                results = conn.execute(query, {"icd_code": icd_code, "limit": limit})
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting patient characteristics: {e}")
            return []
    
    def get_common_lab_results(self, icd_code: str, limit: int = 10):
        """
        Get common lab results for patients with a specific ICD code.
        RESEARCH USE ONLY.
        """
        if not self._connected:
            return []
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    WITH index_patients AS (
                        SELECT DISTINCT subject_id
                        FROM diagnoses_icd
                        WHERE icd_code = :icd_code
                    )
                    SELECT 
                        l.itemid,
                        li.label,
                        COUNT(*) as test_count,
                        ROUND(AVG(l.valuenum), 2) as avg_value,
                        MIN(l.valuenum) as min_value,
                        MAX(l.valuenum) as max_value
                    FROM labevents l
                    JOIN index_patients ip ON l.subject_id = ip.subject_id
                    JOIN d_labitems li ON l.itemid = li.itemid
                    WHERE l.valuenum IS NOT NULL
                    GROUP BY l.itemid, li.label
                    ORDER BY test_count DESC
                    LIMIT :limit
                """)
                
                results = conn.execute(query, {"icd_code": icd_code, "limit": limit})
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting lab results: {e}")
            return []


# Singleton
_mimic_query_engine = None

def get_mimic_query_engine() -> MIMICQueryEngine:
    """Get or create MIMICQueryEngine singleton."""
    global _mimic_query_engine
    if _mimic_query_engine is None:
        _mimic_query_engine = MIMICQueryEngine()
    return _mimic_query_engine