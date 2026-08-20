"""
Medication Categories Engine for LipidAI

Provides EDUCATIONAL ONLY information about lipid-lowering medications.
NEVER instructs patients to start a specific medication.
For education and awareness purposes only.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from database.connection import SessionLocal

logger = logging.getLogger(__name__)


class MedicationEngine:
    """
    Engine for retrieving educational medication information.
    
    CRITICAL PRINCIPLES:
    - EDUCATIONAL ONLY - never instructs patients to start medications
    - Provides mechanisms, common uses, side effects
    - Always includes safety disclaimer
    - Does NOT replace clinical judgment
    """
    
    def __init__(self):
        """Initialize the medication engine."""
        self._table_exists = None
    
    def _check_table_exists(self, db) -> bool:
        """Check if medication_categories table exists."""
        try:
            result = db.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'medication_categories'"
                ")"
            ))
            exists = result.scalar()
            self._table_exists = exists
            return exists
        except Exception as e:
            logger.error(f"Error checking medication_categories table existence: {e}")
            return False
    
    def get_medication_info(self, medication_class: str) -> Optional[Dict[str, Any]]:
        """
        Get educational information for a medication class.
        
        Args:
            medication_class: Name of the medication class (Statins, Fibrates, etc.)
            
        Returns:
            Medication information dict with educational content
        """
        if not medication_class:
            return None
        
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    logger.warning("medication_categories table does not exist")
                    return None
                
                query = text("""
                    SELECT 
                        medication_class,
                        drug_names,
                        mechanism_of_action,
                        common_indications,
                        typical_dosing,
                        side_effects,
                        contraindications,
                        monitoring_required,
                        drug_interactions,
                        special_population_notes,
                        educational_summary,
                        safety_note
                    FROM medication_categories
                    WHERE LOWER(TRIM(medication_class)) = LOWER(TRIM(:medication_class))
                    AND is_active = TRUE
                    LIMIT 1
                """)
                
                result = db.execute(query, {"medication_class": medication_class}).first()
                
                if result:
                    return {
                        'medication_class': result.medication_class,
                        'drug_names': result.drug_names or [],
                        'mechanism_of_action': result.mechanism_of_action,
                        'common_indications': result.common_indications or [],
                        'typical_dosing': result.typical_dosing,
                        'side_effects': result.side_effects or [],
                        'contraindications': result.contraindications or [],
                        'monitoring_required': result.monitoring_required or [],
                        'drug_interactions': result.drug_interactions or [],
                        'special_population_notes': result.special_population_notes,
                        'educational_summary': result.educational_summary,
                        'safety_note': result.safety_note,
                        'found': True
                    }
                else:
                    logger.info(f"No medication info found for class: {medication_class}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error in MedicationEngine.get_medication_info(): {e}")
                return None
    
    def get_all_medications(self) -> List[Dict[str, Any]]:
        """
        Get all medication categories.
        
        Returns:
            List of all medication classes with basic info
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                query = text("""
                    SELECT 
                        medication_class,
                        drug_names,
                        mechanism_of_action,
                        common_indications,
                        educational_summary
                    FROM medication_categories
                    WHERE is_active = TRUE
                    ORDER BY medication_class
                """)
                
                result = db.execute(query).fetchall()
                
                medications = []
                for row in result:
                    medications.append({
                        'medication_class': row.medication_class,
                        'drug_names': row.drug_names or [],
                        'mechanism_of_action': row.mechanism_of_action,
                        'common_indications': row.common_indications or [],
                        'educational_summary': row.educational_summary,
                        'found': True
                    })
                
                return medications
                
            except Exception as e:
                logger.error(f"Error in MedicationEngine.get_all_medications(): {e}")
                return []
    
    def get_medications_by_indication(self, indication: str) -> List[Dict[str, Any]]:
        """
        Get medication classes relevant to a specific indication.
        
        Args:
            indication: Disease or condition (Hyperlipidemia, High LDL, etc.)
            
        Returns:
            List of medication classes used for that indication
        """
        with SessionLocal() as db:
            try:
                if not self._check_table_exists(db):
                    return []
                
                query = text("""
                    SELECT 
                        medication_class,
                        drug_names,
                        mechanism_of_action,
                        common_indications,
                        educational_summary
                    FROM medication_categories
                    WHERE array_to_string(common_indications, ',') ILIKE :indication
                    AND is_active = TRUE
                    ORDER BY medication_class
                """)
                
                result = db.execute(query, {"indication": f"%{indication}%"}).fetchall()
                
                medications = []
                for row in result:
                    medications.append({
                        'medication_class': row.medication_class,
                        'drug_names': row.drug_names or [],
                        'mechanism_of_action': row.mechanism_of_action,
                        'common_indications': row.common_indications or [],
                        'educational_summary': row.educational_summary,
                        'found': True
                    })
                
                return medications
                
            except Exception as e:
                logger.error(f"Error in MedicationEngine.get_medications_by_indication(): {e}")
                return []
    
    def get_disease_medication_recommendations(self, disease_name: str) -> List[Dict[str, Any]]:
        """
        Get medication information for a specific disease.
        Maps disease to relevant medication classes.
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            List of medication classes relevant to the disease
        """
        # Map diseases to medication classes
        # This is educational mapping, not prescribing advice
        disease_medication_map = {
            'hyperlipidemia': ['Statins', 'Ezetimibe', 'PCSK9 Inhibitors'],
            'high ldl cholesterol': ['Statins', 'Ezetimibe', 'PCSK9 Inhibitors', 'Bile Acid Sequestrants'],
            'high ldl': ['Statins', 'Ezetimibe', 'PCSK9 Inhibitors'],
            'familial hypercholesterolemia': ['Statins', 'PCSK9 Inhibitors', 'Ezetimibe'],
            'familial hypercholesterolemia': ['Statins', 'PCSK9 Inhibitors', 'Ezetimibe'],
            'hypertriglyceridemia': ['Fibrates', 'Omega-3 Fatty Acids', 'Niacin'],
            'high triglycerides': ['Fibrates', 'Omega-3 Fatty Acids', 'Niacin'],
            'metabolic syndrome': ['Statins', 'Fibrates', 'Omega-3 Fatty Acids'],
            'low hdl': ['Niacin', 'Fibrates', 'Statins'],
            'low hdl syndrome': ['Niacin', 'Fibrates', 'Statins'],
            'severe mixed dyslipidemia': ['Statins', 'Fibrates', 'PCSK9 Inhibitors', 'Ezetimibe']
        }
        
        results = []
        disease_lower = disease_name.lower()
        
        # Find matching disease in map
        for key, classes in disease_medication_map.items():
            if key in disease_lower:
                for med_class in classes:
                    info = self.get_medication_info(med_class)
                    if info:
                        results.append(info)
                break
        else:
            # No specific mapping found - return general lipid-lowering medications
            for med_class in ['Statins', 'Ezetimibe']:
                info = self.get_medication_info(med_class)
                if info:
                    results.append(info)
        
        return results


# Module-level singleton
_medication_engine = None


def get_medication_engine() -> MedicationEngine:
    """
    Get or create the singleton MedicationEngine instance.
    """
    global _medication_engine
    if _medication_engine is None:
        _medication_engine = MedicationEngine()
    return _medication_engine