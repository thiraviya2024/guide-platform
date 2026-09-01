# app/services/lipid_service.py
"""
Lipid Analysis Service
"""

from typing import Dict, Any, Optional
from app.engines.clinical_engine.lipid_engine import LipidEngine
from app.services.clinical_evidence import is_abnormal
import logging

logger = logging.getLogger(__name__)


class LipidService:
    """Lipid analysis service."""
    
    def __init__(self):
        self.engine = LipidEngine()
    
    def analyze_values(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze lipid values - API compatibility method."""
        return self.analyze(values)
    
    def analyze(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze lipid values."""
        results = self.engine.evaluate(values)
        risks = self.engine.get_disease_risks(results)
        
        total_params = len(results)
        # This list is the canonical source for both the compatibility count
        # and downstream report evidence. OPTIMAL and NORMAL are explicitly
        # non-abnormal.
        abnormal_results = [
            {"parameter": name, **details}
            for name, details in results.items()
            if is_abnormal(details.get("status"))
        ]
        abnormal_count = len(abnormal_results)
        normal_count = total_params - abnormal_count
        
        if abnormal_count == 0:
            overall_status = "Normal"
            status_color = "green"
        elif abnormal_count <= 2:
            overall_status = "Minor Abnormalities"
            status_color = "yellow"
        else:
            overall_status = "Significant Abnormalities"
            status_color = "red"
        
        return {
            'success': True,
            'message': 'Lipid analysis completed',
            'overall_status': overall_status,
            'status_color': status_color,
            'total_parameters': total_params,
            'abnormal_count': abnormal_count,
            'normal_count': normal_count,
            'results': results,
            'abnormal_results': abnormal_results,
            'physician_review_required': bool(abnormal_results),
            'disease_risks': risks,
            'category': 'lipid'
        }
    
    def analyze_with_risk(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze lipid values with disease risk detection."""
        return self.analyze(values)
