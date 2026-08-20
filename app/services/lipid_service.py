# app/services/lipid_service.py
"""
Lipid Analysis Service
"""

from typing import Dict, Any, Optional
from app.engines.clinical_engine.lipid_engine import LipidEngine
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
        abnormal_count = sum(1 for v in results.values() if v.get('status') not in ['Normal', 'Good result'])
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
            'disease_risks': risks,
            'category': 'lipid'
        }
    
    def analyze_with_risk(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze lipid values with disease risk detection."""
        return self.analyze(values)