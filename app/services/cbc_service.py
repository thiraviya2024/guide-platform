# app/services/cbc_service.py
"""
CBC Analysis Service
"""

from typing import Dict, Any, Optional
from app.engines.clinical_engine.cbc_engine import CBCEngine
from app.engines.extraction_engine.cbc_extractor import CBCExtractor
import logging

logger = logging.getLogger(__name__)


class CBCService:
    """CBC analysis service."""
    
    def __init__(self):
        self.engine = CBCEngine()
        self.extractor = CBCExtractor()
    
    def analyze_values(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze CBC values - API compatibility method."""
        return self.analyze(values)
    
    def analyze(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze CBC values."""
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
            'message': 'CBC analysis completed',
            'overall_status': overall_status,
            'status_color': status_color,
            'total_parameters': total_params,
            'abnormal_count': abnormal_count,
            'normal_count': normal_count,
            'results': results,
            'disease_risks': risks,
            'category': 'cbc'
        }
    
    def analyze_text(self, text: str, gender: Optional[str] = None) -> Dict[str, Any]:
        """Analyze CBC from text."""
        values = self.extractor.extract(text)
        
        if not values:
            return {
                'success': False,
                'message': 'No CBC values found in the text',
                'results': {}
            }
        
        return self.analyze_values(values)