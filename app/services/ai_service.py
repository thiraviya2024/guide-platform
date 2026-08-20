# app/services/ai_service.py
"""
Groq AI Explanation Service
"""

import os
from typing import Dict, Any, List, Optional
from groq import Groq
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Provides AI-powered explanations using Groq."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.provider = settings.DEFAULT_LLM_PROVIDER
        
        if not self.api_key:
            logger.warning("⚠️ GROQ_API_KEY not set. AI features will be disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
    
    def explain_results(self, results: Dict[str, Any], disease_risks: List[Dict[str, Any]]) -> str:
        """
        Generate AI explanation for test results.
        
        Args:
            results: All test results
            disease_risks: Detected disease risks
            
        Returns:
            AI-generated explanation
        """
        if not self.client:
            return "AI explanation unavailable. GROQ_API_KEY not configured. Please consult your healthcare provider."
        
        # Prepare context
        context = self._prepare_context(results, disease_risks)
        
        # Create prompt
        prompt = f"""
        You are a medical AI assistant. Provide a clear, professional explanation of these lab results.
        
        {context}
        
        Please provide:
        1. A brief summary of the findings
        2. What each abnormal result means
        3. Possible causes
        4. Recommendations for next steps
        5. Lifestyle suggestions
        
        Keep it professional but easy to understand. Include a disclaimer that this is not medical advice.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable medical AI assistant. Provide accurate, helpful, and professional health explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            explanation = response.choices[0].message.content
            logger.info("✅ AI explanation generated")
            return explanation
            
        except Exception as e:
            logger.error(f"❌ AI explanation failed: {e}")
            return f"AI explanation unavailable at this time. Error: {str(e)}"
    
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
        if not self.client:
            return "Lifestyle recommendations unavailable. GROQ_API_KEY not configured."
        
        context = self._prepare_context(results, [])
        
        prompt = f"""
        Based on these lab results, provide personalized lifestyle recommendations:
        
        {context}
        
        Please provide recommendations for:
        1. Diet and nutrition (specific foods to eat/avoid)
        2. Exercise and physical activity (type, frequency, intensity)
        3. Sleep and stress management
        4. Habits to avoid
        5. Habits to adopt
        6. When to follow up with a healthcare provider
        
        Be specific, actionable, and evidence-based.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a health and wellness expert. Provide practical, actionable lifestyle recommendations based on lab results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=800
            )
            
            recommendations = response.choices[0].message.content
            logger.info("✅ Lifestyle recommendations generated")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Lifestyle recommendations failed: {e}")
            return f"Lifestyle recommendations unavailable at this time. Error: {str(e)}"
    
    def generate_health_summary(self, patient_info: Dict[str, Any], results: Dict[str, Any]) -> str:
        """
        Generate a comprehensive health summary.
        
        Args:
            patient_info: Patient demographics
            results: All test results
            
        Returns:
            AI-generated health summary
        """
        if not self.client:
            return "Health summary unavailable. GROQ_API_KEY not configured."
        
        patient_text = f"""
        Patient Information:
        - Name: {patient_info.get('name', 'N/A')}
        - Age: {patient_info.get('age', 'N/A')}
        - Gender: {patient_info.get('gender', 'N/A')}
        - Date: {patient_info.get('date', 'N/A')}
        """
        
        context = self._prepare_context(results, [])
        
        prompt = f"""
        Provide a comprehensive health summary for this patient:
        
        {patient_text}
        
        Lab Results:
        {context}
        
        Please provide:
        1. Overall health assessment
        2. Key findings and concerns
        3. Areas of optimal health
        4. Risk factors identified
        5. Recommended follow-up actions
        6. Long-term health outlook with appropriate interventions
        
        Be professional, compassionate, and evidence-based.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior physician providing a comprehensive health summary. Be thorough, professional, and compassionate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1200
            )
            
            summary = response.choices[0].message.content
            logger.info("✅ Health summary generated")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Health summary failed: {e}")
            return f"Health summary unavailable at this time. Error: {str(e)}"