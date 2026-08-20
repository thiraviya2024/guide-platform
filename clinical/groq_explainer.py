"""
Groq AI Explainer for LipidAI
"""

import logging
import json
from typing import Dict, List, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import groq, but handle gracefully if not installed
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq library not installed. AI explanations disabled.")


class GroqExplainer:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        
        if not GROQ_AVAILABLE:
            logger.warning("Groq library not available. AI explanations disabled.")
            self.client = None
            return
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found. AI explanations disabled.")
            self.client = None
        else:
            try:
                # Create httpx client without proxies (fixed version)
                import httpx
                http_client = httpx.Client()
                self.client = Groq(
                    api_key=self.api_key,
                    http_client=http_client
                )
                logger.info("✅ Groq client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self.client = None
    
    def generate_explanation(self, 
                            rule_results: Dict[str, Any],
                            disease_predictions: List[Dict[str, Any]],
                            exercise_data: Dict[str, Any],
                            medication_data: List[Dict[str, Any]],
                            followup_tests: List[Dict[str, Any]],
                            guidelines: List[Dict[str, Any]],
                            confidence: Dict[str, Any],
                            patient_context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        
        if not self.client or not GROQ_AVAILABLE:
            return {
                'summary': 'AI explanation unavailable. Please check Groq API configuration.',
                'detailed_explanation': '',
                'recommendations': '',
                'disclaimer': ''
            }
        
        try:
            prompt = self._build_prompt(
                rule_results,
                disease_predictions,
                exercise_data,
                medication_data,
                followup_tests,
                guidelines,
                confidence,
                patient_context
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            explanation = response.choices[0].message.content
            return self._parse_explanation(explanation)
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return {
                'summary': f'AI explanation temporarily unavailable: {str(e)}',
                'detailed_explanation': '',
                'recommendations': '',
                'disclaimer': ''
            }
    
    def _get_system_prompt(self) -> str:
        return """
        You are a helpful, compassionate, and expert medical AI assistant explaining lipid profile results to a patient.
        
        CRITICAL RULES:
        1. ONLY explain what is provided in the structured data
        2. NEVER invent lab values, diseases, or recommendations
        3. ALWAYS cite clinical guidelines when making recommendations
        4. Use patient-friendly, simple language
        5. Be compassionate and supportive
        6. Include the required medical disclaimer
        7. NEVER tell patients to start or stop any medication
        8. ALWAYS recommend consulting a healthcare provider
        
        Format your response in clear sections:
        1. SUMMARY: Brief overview (2-3 sentences)
        2. DETAILED EXPLANATION: What the results mean
        3. RECOMMENDATIONS: Lifestyle and follow-up suggestions
        4. DISCLAIMER: Medical disclaimer
        """
    
    def _build_prompt(self,
                     rule_results: Dict[str, Any],
                     disease_predictions: List[Dict[str, Any]],
                     exercise_data: Dict[str, Any],
                     medication_data: List[Dict[str, Any]],
                     followup_tests: List[Dict[str, Any]],
                     guidelines: List[Dict[str, Any]],
                     confidence: Dict[str, Any],
                     patient_context: Optional[Dict[str, Any]] = None) -> str:
        
        rule_summary = []
        for param, data in rule_results.items():
            if isinstance(data, dict):
                status = data.get('status', 'Unknown')
                value = data.get('value', 'N/A')
                rec = data.get('recommendation', '')
                rule_summary.append(f"- {param}: {value} mg/dL - {status}")
                if rec and status != 'Normal':
                    rule_summary.append(f"  Recommendation: {rec}")
        
        disease_summary = []
        for disease in disease_predictions:
            disease_summary.append(
                f"- {disease.get('disease_name')} "
                f"(Confidence: {disease.get('confidence_score', 0):.1f}%)"
            )
            if disease.get('management_strategy'):
                disease_summary.append(f"  Management: {disease.get('management_strategy')}")
        
        exercise_summary = []
        for disease, data in exercise_data.items():
            if data.get('found', False):
                exercise_summary.append(f"- {disease}:")
                exercise_summary.append(f"  - Exercise: {data.get('exercise_type')}")
                exercise_summary.append(f"  - Frequency: {data.get('frequency')}")
                exercise_summary.append(f"  - Duration: {data.get('duration')}")
        
        med_summary = []
        for med in medication_data:
            med_summary.append(f"- {med.get('medication_class')}: {med.get('mechanism_of_action', 'N/A')[:100]}...")
            if med.get('drug_names'):
                med_summary.append(f"  Drugs: {', '.join(med.get('drug_names', [])[:3])}")
        
        test_summary = []
        for test in followup_tests:
            test_summary.append(
                f"- {test.get('test_name')} "
                f"(Frequency: {test.get('frequency')}, "
                f"Priority: {test.get('priority')})"
            )
            if test.get('rationale'):
                test_summary.append(f"  Why: {test.get('rationale')}")
        
        guideline_summary = []
        for g in guidelines[:3]:
            guideline_summary.append(
                f"- {g.get('guideline_name')}: {g.get('recommendation')[:100]}..."
            )
        
        confidence_text = f"Overall confidence: {confidence.get('overall', {}).get('score', 0):.1f}%"
        if confidence.get('overall', {}).get('confidence_level'):
            confidence_text += f" ({confidence['overall']['confidence_level']})"
        
        prompt = f"""
        Please explain the following lipid profile results to a patient:
        
        PATIENT CONTEXT:
        {json.dumps(patient_context or {}, indent=2)}
        
        LAB RESULTS (from Rule Engine):
        {chr(10).join(rule_summary)}
        
        DETECTED DISEASES (from Disease Engine):
        {chr(10).join(disease_summary)}
        
        EXERCISE RECOMMENDATIONS:
        {chr(10).join(exercise_summary)}
        
        MEDICATION INFORMATION (EDUCATIONAL ONLY):
        {chr(10).join(med_summary)}
        
        FOLLOW-UP TESTS RECOMMENDED:
        {chr(10).join(test_summary)}
        
        CLINICAL GUIDELINES CITED:
        {chr(10).join(guideline_summary)}
        
        CONFIDENCE SCORE:
        {confidence_text}
        
        Please provide:
        1. A compassionate summary for the patient
        2. Detailed explanation of what their results mean
        3. Clear, actionable recommendations (lifestyle, tests, follow-up)
        4. The required medical disclaimer
        """
        
        return prompt
    
    def _parse_explanation(self, response: str) -> Dict[str, str]:
        sections = {
            'summary': '',
            'detailed_explanation': '',
            'recommendations': '',
            'disclaimer': ''
        }
        
        current_section = None
        lines = response.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'summary' in line_lower and ':' in line_lower:
                current_section = 'summary'
                if ':' in line:
                    sections['summary'] += line.split(':', 1)[1].strip() + '\n'
                continue
            elif 'detailed explanation' in line_lower or 'what this means' in line_lower:
                current_section = 'detailed_explanation'
                continue
            elif 'recommendation' in line_lower or 'what you can do' in line_lower:
                current_section = 'recommendations'
                continue
            elif 'disclaimer' in line_lower or 'important note' in line_lower:
                current_section = 'disclaimer'
                continue
            
            if current_section and line.strip():
                sections[current_section] += line + '\n'
        
        for key in sections:
            sections[key] = sections[key].strip()
        
        if not any(sections.values()):
            sections['summary'] = response.strip()
        
        return sections


_groq_explainer = None

def get_groq_explainer() -> GroqExplainer:
    global _groq_explainer
    if _groq_explainer is None:
        _groq_explainer = GroqExplainer()
    return _groq_explainer