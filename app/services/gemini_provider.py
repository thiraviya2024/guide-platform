# app/services/gemini_provider.py
"""
Google Gemini AI Provider
"""

import google.generativeai as genai
from typing import Dict, Any
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Google Gemini AI provider."""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        # ✅ Updated to use the working model
        self.model_name = settings.GEMINI_MODEL or "models/gemini-3.6-flash"

        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Gemini features disabled.")
            self.client = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                logger.info(f"✅ Gemini initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.client = None
    
    def analyze(self, context: str) -> Dict[str, Any]:
        """Analyze clinical context using Gemini."""
        if not self.client:
            return {
                'success': False,
                'error': 'Gemini API key not configured or initialization failed',
                'provider': 'gemini'
            }
        
        try:
            prompt = self._build_prompt(context)
            response = self.client.generate_content(prompt)
            
            return {
                'success': True,
                'provider': 'gemini',
                'model': self.model_name,
                'response': response.text,
                'raw': response
            }
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'gemini'
            }
    
    def _build_prompt(self, context: str) -> str:
        """Build prompt for Gemini."""
        return f"""
        You are a medical AI assistant. Analyze these lab results:
        
        {context}
        
        Provide a clear, professional analysis including:
        1. Brief summary of findings
        2. Abnormal results and their meaning
        3. Possible causes
        4. Recommendations for next steps
        5. Lifestyle suggestions
        
        Keep it professional but easy to understand.
        Include a disclaimer that this is not medical advice.
        """
