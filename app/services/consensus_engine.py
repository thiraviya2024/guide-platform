# app/services/consensus_engine.py
"""
Consensus Engine - Evaluates agreement between AI models
"""

from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


class ConsensusEngine:
    """Evaluates agreement between multiple AI models."""
    
    def __init__(self):
        self.agreement_threshold = 0.7  # 70% agreement required
    
    def evaluate(self, responses: Dict[str, Any], clinical_data: Dict, analysis_id: str) -> Dict[str, Any]:
        """
        Evaluate consensus between AI models.
        
        Args:
            responses: Responses from AI providers
            clinical_data: Original clinical data
            analysis_id: Unique analysis ID
            
        Returns:
            Consensus result with agreements and disagreements
        """
        # Filter successful responses
        successful = {
            name: resp for name, resp in responses.items()
            if resp.get('success', False)
        }
        
        if not successful:
            return {
                'analysis_id': analysis_id,
                'success': False,
                'error': 'No AI providers returned successful responses',
                'physician_review_required': True
            }
        
        # Extract key findings from each response
        findings = {}
        for name, resp in successful.items():
            findings[name] = self._extract_findings(resp.get('response', ''))
        
        # Calculate agreement
        agreement = self._calculate_agreement(findings)
        
        # Identify disagreements
        disagreements = self._find_disagreements(findings)
        
        # Build final response
        final_response = self._synthesize(findings, clinical_data)
        
        # Determine if physician review is needed
        physician_review_required = (
            len(successful) < 2 or
            agreement['overall_score'] < self.agreement_threshold or
            len(disagreements) > 0
        )
        
        return {
            'analysis_id': analysis_id,
            'success': True,
            'models_used': list(successful.keys()),
            'agreement_score': agreement['overall_score'],
            'agreements': agreement['agreements'],
            'disagreements': disagreements,
            'final_response': final_response,
            'physician_review_required': physician_review_required,
            'input_data': clinical_data
        }
    
    def _extract_findings(self, response: str) -> Dict[str, Any]:
        """Extract key findings from AI response."""
        findings = {
            'summary': '',
            'abnormal_results': [],
            'possible_causes': [],
            'recommendations': [],
            'lifestyle_suggestions': []
        }
        
        # Simple extraction
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            lower = line.lower()
            if 'summary' in lower or 'brief summary' in lower:
                current_section = 'summary'
            elif 'abnormal' in lower or 'result' in lower:
                current_section = 'abnormal'
            elif 'cause' in lower:
                current_section = 'causes'
            elif 'recommendation' in lower or 'next step' in lower:
                current_section = 'recommendations'
            elif 'lifestyle' in lower or 'suggest' in lower:
                current_section = 'lifestyle'
            elif current_section and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                item = line.lstrip('-•* ').strip()
                if current_section == 'summary':
                    findings['summary'] = item
                elif current_section == 'abnormal':
                    findings['abnormal_results'].append(item)
                elif current_section == 'causes':
                    findings['possible_causes'].append(item)
                elif current_section == 'recommendations':
                    findings['recommendations'].append(item)
                elif current_section == 'lifestyle':
                    findings['lifestyle_suggestions'].append(item)
        
        return findings
    
    def _calculate_agreement(self, findings: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate agreement between models."""
        if len(findings) < 2:
            return {
                'overall_score': 1.0,
                'agreements': {},
                'agreement_details': 'Only one model available'
            }
        
        model_names = list(findings.keys())
        agreements = {}
        
        # Compare abnormal results
        abnormal_sets = {}
        for name, f in findings.items():
            abnormal_sets[name] = set(f.get('abnormal_results', []))
        
        if len(abnormal_sets) >= 2:
            common = abnormal_sets[model_names[0]]
            for name in model_names[1:]:
                common = common.intersection(abnormal_sets[name])
            agreements['abnormal_results'] = list(common)
        
        # Calculate overall agreement score
        total_items = 0
        matched_items = 0
        
        # Compare recommendations
        for i, name1 in enumerate(model_names):
            recs1 = set(findings[name1].get('recommendations', []))
            for name2 in model_names[i+1:]:
                recs2 = set(findings[name2].get('recommendations', []))
                if recs1 and recs2:
                    total_items += 1
                    intersection = recs1.intersection(recs2)
                    if len(intersection) / max(len(recs1), len(recs2)) > 0.5:
                        matched_items += 1
        
        # Compare lifestyle suggestions
        for i, name1 in enumerate(model_names):
            life1 = set(findings[name1].get('lifestyle_suggestions', []))
            for name2 in model_names[i+1:]:
                life2 = set(findings[name2].get('lifestyle_suggestions', []))
                if life1 and life2:
                    total_items += 1
                    intersection = life1.intersection(life2)
                    if len(intersection) / max(len(life1), len(life2)) > 0.5:
                        matched_items += 1
        
        overall_score = matched_items / total_items if total_items > 0 else 1.0
        
        return {
            'overall_score': overall_score,
            'agreements': agreements,
            'agreement_details': f"{matched_items}/{total_items} items matched"
        }
    
    def _find_disagreements(self, findings: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Find disagreements between models."""
        disagreements = []
        
        if len(findings) < 2:
            return disagreements
        
        model_names = list(findings.keys())
        
        # Compare recommendations
        for i, name1 in enumerate(model_names):
            recs1 = set(findings[name1].get('recommendations', []))
            for name2 in model_names[i+1:]:
                recs2 = set(findings[name2].get('recommendations', []))
                if recs1 and recs2:
                    only_in_1 = recs1 - recs2
                    only_in_2 = recs2 - recs1
                    if only_in_1 or only_in_2:
                        disagreements.append({
                            'type': 'recommendation',
                            'model_1': name1,
                            'model_1_value': list(only_in_1),
                            'model_2': name2,
                            'model_2_value': list(only_in_2),
                            'severity': 'medium'
                        })
        
        return disagreements
    
    def _synthesize(self, findings: Dict[str, Dict], clinical_data: Dict) -> Dict[str, Any]:
        """Synthesize final response from multiple models."""
        first_model = list(findings.keys())[0]
        base = findings[first_model]
        
        return {
            'summary': base.get('summary', ''),
            'abnormal_results': base.get('abnormal_results', []),
            'possible_causes': base.get('possible_causes', []),
            'recommendations': base.get('recommendations', []),
            'lifestyle_suggestions': base.get('lifestyle_suggestions', []),
            'clinical_data': clinical_data,
            'model_consensus': 'Based on analysis from multiple AI models'
        }