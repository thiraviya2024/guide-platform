# app/services/groq_provider.py
"""
Groq AI Provider
"""

from groq import Groq
from typing import Dict, Any
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqProvider:
    """Groq AI provider."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set. Groq features disabled.")
            self.client = None
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info(f"✅ Groq initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")
                self.client = None
    
    def analyze(self, context: str) -> Dict[str, Any]:
        """Analyze clinical context using Groq."""
        if not self.client:
            return {
                'success': False,
                'error': 'Groq API key not configured',
                'provider': 'groq'
            }
        
        try:
            prompt = self._build_prompt(context)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable medical AI assistant. Provide accurate, helpful, and professional health explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            return {
                'success': True,
                'provider': 'groq',
                'model': self.model,
                'response': response.choices[0].message.content,
                'raw': response
            }
            
        except Exception as e:
            logger.error(f"Groq analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'groq'
            }
    
    def _build_prompt(self, context: str) -> str:
        """Build prompt for Groq."""
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