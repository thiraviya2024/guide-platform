# app/services/ai_service.py
"""
Groq AI Explanation Service
"""

from typing import Dict, Any, List, Optional
import logging

from app.services.ai_orchestrator import AIOrchestrator
from app.services.clinical_evidence import build_clinical_evidence

logger = logging.getLogger(__name__)


class AIProviderUnavailable(RuntimeError):
    """Raised when no configured AI provider produces a verified response."""


class AIService:
    """Compatibility facade over the report-grounded AI orchestrator."""
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
    
    def explain_results(self, results: Dict[str, Any], disease_risks: List[Dict[str, Any]]) -> str:
        """
        Generate AI explanation for test results.
        
        Args:
            results: All test results
            disease_risks: Detected disease risks
            
        Returns:
            AI-generated explanation
        """
        evidence = build_clinical_evidence({"results": results, "disease_risks": disease_risks})
        generated = self.orchestrator.generate_response(evidence, "Explain these report findings.", require_provider=True)
        if not generated.get("success"):
            raise AIProviderUnavailable(generated.get("details", "AI providers unavailable"))
        return generated["response"]
    
    def _prepare_context(self, results: Dict[str, Any], disease_risks: List[Dict[str, Any]]) -> str:
        """Prepare context for AI prompt."""
        context = "LAB RESULTS:\n"
        
        # Handle different result formats
        for category, params in results.items():
            if isinstance(params, list):
                for param in params:
                    if isinstance(param, dict):
                        value = param.get('value', 'N/A')
                        status = param.get('status', 'N/A')
                        param_name = param.get('parameter', param.get('name', 'N/A'))
                        context += f"- {param_name}: {value} ({status})\n"
            elif isinstance(params, dict):
                for param_name, param_data in params.items():
                    if isinstance(param_data, dict):
                        value = param_data.get('value', 'N/A')
                        status = param_data.get('status', 'N/A')
                        context += f"- {param_name}: {value} ({status})\n"
                    else:
                        context += f"- {param_name}: {param_data}\n"
            else:
                context += f"- {category}: {params}\n"
        
        if disease_risks:
            context += "\nDISEASE RISKS DETECTED:\n"
            for risk in disease_risks:
                context += f"- {risk.get('disease', 'N/A')} (Confidence: {risk.get('confidence', 'N/A')})\n"
                context += f"  Reason: {risk.get('reason', 'N/A')}\n"
                context += f"  Recommendation: {risk.get('recommendation', 'N/A')}\n"
        
        return context
    
    def generate_lifestyle_recommendations(self, results: Dict[str, Any]) -> str:
        """
        Generate personalized lifestyle recommendations.
        
        Args:
            results: All test results
            
        Returns:
            AI-generated lifestyle recommendations
        """
        evidence = build_clinical_evidence({"results": results})
        generated = self.orchestrator.generate_response(
            evidence, "What lifestyle and food guidance follows from these report findings?", require_provider=True
        )
        if not generated.get("success"):
            raise AIProviderUnavailable(generated.get("details", "AI providers unavailable"))
        return generated["response"]
    
    def generate_health_summary(self, patient_info: Dict[str, Any], results: Dict[str, Any]) -> str:
        """
        Generate a comprehensive health summary.
        
        Args:
            patient_info: Patient demographics
            results: All test results
            
        Returns:
            AI-generated health summary
        """
        evidence = build_clinical_evidence({"results": results}, patient_info)
        generated = self.orchestrator.generate_response(evidence, "Summarize these report findings.", require_provider=True)
        if not generated.get("success"):
            raise AIProviderUnavailable(generated.get("details", "AI providers unavailable"))
        return generated["response"]
