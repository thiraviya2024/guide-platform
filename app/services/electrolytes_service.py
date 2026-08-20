# app/services/electrolytes_service.py
"""
Electrolytes Analysis Service
"""

from typing import Dict, Any, Optional
from app.engines.clinical_engine.electrolytes_engine import ElectrolytesEngine
import logging

logger = logging.getLogger(__name__)


class ElectrolytesService:
    """Electrolytes analysis service."""
    
    def __init__(self):
        self.engine = ElectrolytesEngine()
    
    def analyze_values(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze Electrolytes values - API compatibility method."""
        return self.analyze(values)
    
    def analyze(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze Electrolytes values."""
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
            'message': 'Electrolytes analysis completed',
            'overall_status': overall_status,
            'status_color': status_color,
            'total_parameters': total_params,
            'abnormal_count': abnormal_count,
            'normal_count': normal_count,
            'results': results,
            'disease_risks': risks,
            'category': 'electrolytes'
        }
