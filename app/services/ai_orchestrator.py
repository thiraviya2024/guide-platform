# app/services/ai_orchestrator.py
"""
AI Orchestrator - Coordinates multiple AI models
"""

from typing import Dict, Any, List
import uuid
import logging
from datetime import datetime

from app.services.groq_provider import GroqProvider
from app.services.consensus_engine import ConsensusEngine
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Orchestrates multiple AI models for clinical analysis."""
    
    def __init__(self):
        self.providers = {}
        self.consensus_engine = ConsensusEngine()
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available AI providers."""
        # Groq is always available
        self.providers['groq'] = GroqProvider()
        
        # Gemini if API key is set
        try:
            from app.services.gemini_provider import GeminiProvider
            if settings.GEMINI_API_KEY:
                self.providers['gemini'] = GeminiProvider()
                logger.info("✅ Gemini provider initialized")
        except ImportError:
            logger.warning("Gemini provider not available")
    
    def analyze(self, clinical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run analysis through all available AI providers.
        
        Args:
            clinical_data: Clinical data to analyze
            
        Returns:
            Consensus analysis results
        """
        analysis_id = str(uuid.uuid4())
        
        # 1. Prepare context
        context = self._prepare_context(clinical_data)
        
        # 2. Get responses from all providers
        responses = {}
        for name, provider in self.providers.items():
            try:
                start_time = datetime.now()
                responses[name] = provider.analyze(context)
                end_time = datetime.now()
                if responses[name].get('success'):
                    responses[name]['response_time_ms'] = (end_time - start_time).total_seconds() * 1000
            except Exception as e:
                logger.error(f"Provider {name} failed: {e}")
                responses[name] = {
                    'success': False,
                    'error': str(e),
                    'provider': name
                }
        
        # 3. Run consensus engine
        consensus = self.consensus_engine.evaluate(responses, clinical_data, analysis_id)
        
        # 4. Log results
        self._log_analysis(responses, consensus)
        
        return consensus
    
    def _prepare_context(self, data: Dict) -> str:
        """Prepare clinical context for AI providers."""
        context = "CLINICAL DATA:\n"
        
        # Add patient info
        if 'patient_info' in data:
            info = data['patient_info']
            context += f"Patient: {info.get('name', 'Unknown')}\n"
            context += f"Age: {info.get('age', 'Unknown')}\n"
            context += f"Gender: {info.get('gender', 'Unknown')}\n"
        
        # Add lab results
        if 'results' in data:
            context += "\nLAB RESULTS:\n"
            for param, details in data['results'].items():
                if isinstance(details, dict):
                    value = details.get('value', 'N/A')
                    status = details.get('status', 'N/A')
                    context += f"- {param}: {value} ({status})\n"
        
        # Add disease risks
        if 'disease_risks' in data and data['disease_risks']:
            context += "\nDETECTED RISKS:\n"
            for risk in data['disease_risks']:
                context += f"- {risk.get('disease')}: {risk.get('confidence')} confidence\n"
                context += f"  Reason: {risk.get('reason')}\n"
        
        # Add overall status
        if 'overall_status' in data:
            context += f"\nOVERALL STATUS: {data.get('overall_status')}\n"
        
        return context
    
    def _log_analysis(self, responses: Dict, consensus: Dict):
        """Log analysis results for audit."""
        try:
            from app.core.database import SessionLocal
            from sqlalchemy import text
            
            with SessionLocal() as db:
                analysis_id = consensus.get('analysis_id', str(uuid.uuid4()))
                
                # Log each provider response
                for provider, response in responses.items():
                    db.execute(text("""
                        INSERT INTO ai_analysis_logs 
                        (analysis_id, model_provider, model_name, input_data, output_data, confidence, response_time_ms, created_at)
                        VALUES (:analysis_id, :provider, :model, :input, :output, :confidence, :response_time, NOW())
                    """), {
                        'analysis_id': analysis_id,
                        'provider': provider,
                        'model': response.get('model', 'unknown'),
                        'input': consensus.get('input_data', {}),
                        'output': response,
                        'confidence': response.get('confidence', 0),
                        'response_time': response.get('response_time_ms', 0)
                    })
                
                # Log consensus result
                db.execute(text("""
                    INSERT INTO ai_consensus_results 
                    (analysis_id, models_used, agreement_score, disagreements, final_result, physician_review_required, created_at)
                    VALUES (:analysis_id, :models, :agreement, :disagreements, :result, :review_required, NOW())
                """), {
                    'analysis_id': analysis_id,
                    'models': list(responses.keys()),
                    'agreement': consensus.get('agreement_score', 0),
                    'disagreements': consensus.get('disagreements', {}),
                    'result': consensus.get('final_response', {}),
                    'review_required': consensus.get('physician_review_required', False)
                })
                
                db.commit()
        except Exception as e:
            logger.error(f"Failed to log AI analysis: {e}")