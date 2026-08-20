"""
Confidence Score Calculator for LipidAI

Calculates confidence scores for:
1. Rule confidence - How well lipid values match established rules
2. Disease confidence - How well disease criteria are met
3. Evidence confidence - Quality of supporting evidence
4. Overall confidence - Aggregate confidence score for the report

No database table needed - scores are calculated dynamically.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """
    Engine for calculating confidence scores across the system.
    
    Key design decisions:
    - Scores are calculated dynamically, not stored
    - Multiple confidence dimensions combined into overall score
    - Transparent calculation with explanation
    - No hardcoded medical thresholds in scoring logic
    """
    
    def __init__(self):
        """Initialize the confidence engine."""
        pass
    
    def calculate_rule_confidence(self, rule_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence in individual rule evaluations.
        
        Args:
            rule_results: Dictionary from rule_engine.evaluate()
            
        Returns:
            {
                'score': float (0-100),
                'detail': {
                    'total_parameters': int,
                    'matched_parameters': int,
                    'unmatched_parameters': int,
                    'unknown_statuses': int,
                    'parameter_scores': dict
                },
                'explanation': str
            }
        """
        if not rule_results:
            return {
                'score': 0,
                'detail': {'total_parameters': 0, 'matched_parameters': 0},
                'explanation': 'No rule results available to calculate confidence.'
            }
        
        total_params = 0
        matched_params = 0
        unknown_statuses = 0
        parameter_scores = {}
        
        for param, data in rule_results.items():
            if isinstance(data, dict):
                total_params += 1
                status = data.get('status', 'Unknown')
                
                # Check if status was found in rules
                if status and status != 'Unknown' and status != 'No rule found':
                    matched_params += 1
                    parameter_scores[param] = {
                        'status': status,
                        'confidence': 100,
                        'matched': True
                    }
                else:
                    unknown_statuses += 1
                    parameter_scores[param] = {
                        'status': status,
                        'confidence': 0,
                        'matched': False
                    }
        
        # Calculate score
        if total_params == 0:
            score = 0
            detail = {'total_parameters': 0, 'matched_parameters': 0}
        else:
            score = (matched_params / total_params) * 100
            detail = {
                'total_parameters': total_params,
                'matched_parameters': matched_params,
                'unknown_statuses': unknown_statuses,
                'parameter_scores': parameter_scores
            }
        
        explanation = f"""
        Rule confidence: {score:.1f}%
        - {matched_params} out of {total_params} parameters matched to established rules
        - {unknown_statuses} parameters had no matching rule
        Higher confidence indicates better alignment with clinical guidelines.
        """
        
        return {
            'score': round(score, 1),
            'detail': detail,
            'explanation': explanation.strip()
        }
    
    def calculate_disease_confidence(self, disease_predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate confidence in disease predictions.
        
        Args:
            disease_predictions: List from disease_engine.predict()
            
        Returns:
            {
                'score': float (0-100),
                'detail': {
                    'total_diseases': int,
                    'average_confidence': float,
                    'disease_scores': dict
                },
                'explanation': str
            }
        """
        if not disease_predictions:
            return {
                'score': 0,
                'detail': {'total_diseases': 0, 'average_confidence': 0},
                'explanation': 'No disease predictions available.'
            }
        
        total_diseases = len(disease_predictions)
        disease_scores = {}
        
        for prediction in disease_predictions:
            disease_name = prediction.get('disease_name', 'Unknown')
            confidence = prediction.get('confidence_score', 0)
            matched_criteria = prediction.get('matched_criteria', [])
            
            disease_scores[disease_name] = {
                'confidence': confidence,
                'matched_criteria_count': sum(1 for m in matched_criteria if m.get('matched', False)),
                'total_criteria': len(matched_criteria)
            }
        
        # Calculate average confidence
        avg_confidence = sum(d['confidence'] for d in disease_scores.values()) / total_diseases
        
        explanation = f"""
        Disease confidence: {avg_confidence:.1f}%
        - {total_diseases} diseases predicted
        - Average confidence across diseases: {avg_confidence:.1f}%
        Higher confidence indicates stronger match to disease criteria.
        """
        
        return {
            'score': round(avg_confidence, 1),
            'detail': {
                'total_diseases': total_diseases,
                'average_confidence': avg_confidence,
                'disease_scores': disease_scores
            },
            'explanation': explanation.strip()
        }
    
    def calculate_evidence_confidence(self, 
                                     guidelines: List[Dict[str, Any]],
                                     mimic_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence in supporting evidence.
        
        Args:
            guidelines: List from guidelines_engine.get_guidelines()
            mimic_evidence: Dict from mimic_engine.get_evidence()
            
        Returns:
            {
                'score': float (0-100),
                'detail': {
                    'guidelines_count': int,
                    'mimic_evidence_count': int,
                    'evidence_sources': list
                },
                'explanation': str
            }
        """
        evidence_sources = []
        
        # Check guidelines
        if guidelines:
            guideline_count = len(guidelines)
            evidence_sources.append(f"{guideline_count} clinical guidelines")
        else:
            guideline_count = 0
        
        # Check MIMIC evidence
        mimic_found = False
        if mimic_evidence:
            # Check if any evidence was found
            for disease, data in mimic_evidence.items():
                if data.get('found', False):
                    mimic_found = True
                    break
        
        if mimic_found:
            evidence_sources.append("MIMIC-IV supporting evidence")
        
        # Calculate score based on available evidence
        total_sources = len(evidence_sources)
        max_possible_sources = 2  # Guidelines + MIMIC
        
        if total_sources == 0:
            score = 0
        else:
            score = (total_sources / max_possible_sources) * 100
        
        explanation = f"""
        Evidence confidence: {score:.1f}%
        - Found {len(evidence_sources)} sources of supporting evidence
        - {', '.join(evidence_sources)}
        Higher confidence indicates stronger supporting evidence.
        """
        
        return {
            'score': round(score, 1),
            'detail': {
                'guidelines_count': guideline_count,
                'mimic_evidence_found': mimic_found,
                'evidence_sources': evidence_sources
            },
            'explanation': explanation.strip()
        }
    
    def calculate_overall_confidence(self,
                                    rule_confidence: Dict[str, Any],
                                    disease_confidence: Dict[str, Any],
                                    evidence_confidence: Dict[str, Any],
                                    weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Calculate overall confidence score by combining individual scores.
        
        Args:
            rule_confidence: Result from calculate_rule_confidence()
            disease_confidence: Result from calculate_disease_confidence()
            evidence_confidence: Result from calculate_evidence_confidence()
            weights: Optional custom weights for each component
                    Default: {'rule': 0.35, 'disease': 0.40, 'evidence': 0.25}
            
        Returns:
            {
                'score': float (0-100),
                'components': dict,
                'breakdown': dict,
                'explanation': str,
                'confidence_level': str
            }
        """
        if weights is None:
            weights = {
                'rule': 0.35,
                'disease': 0.40,
                'evidence': 0.25
            }
        
        # Extract scores
        rule_score = rule_confidence.get('score', 0)
        disease_score = disease_confidence.get('score', 0)
        evidence_score = evidence_confidence.get('score', 0)
        
        # Calculate weighted average
        overall_score = (
            (rule_score * weights['rule']) +
            (disease_score * weights['disease']) +
            (evidence_score * weights['evidence'])
        )
        
        # Determine confidence level
        if overall_score >= 85:
            confidence_level = "Very High"
            confidence_emoji = "⭐⭐⭐⭐⭐"
        elif overall_score >= 70:
            confidence_level = "High"
            confidence_emoji = "⭐⭐⭐⭐"
        elif overall_score >= 55:
            confidence_level = "Moderate"
            confidence_emoji = "⭐⭐⭐"
        elif overall_score >= 40:
            confidence_level = "Low"
            confidence_emoji = "⭐⭐"
        else:
            confidence_level = "Very Low"
            confidence_emoji = "⭐"
        
        breakdown = {
            'rule_confidence': {
                'score': rule_score,
                'weight': weights['rule'],
                'contribution': rule_score * weights['rule']
            },
            'disease_confidence': {
                'score': disease_score,
                'weight': weights['disease'],
                'contribution': disease_score * weights['disease']
            },
            'evidence_confidence': {
                'score': evidence_score,
                'weight': weights['evidence'],
                'contribution': evidence_score * weights['evidence']
            }
        }
        
        explanation = f"""
        Overall confidence: {overall_score:.1f}% ({confidence_level})
        {confidence_emoji}
        
        Component Breakdown:
        - Rule confidence: {rule_score:.1f}% (weight: {weights['rule']*100:.0f}%)
        - Disease confidence: {disease_score:.1f}% (weight: {weights['disease']*100:.0f}%)
        - Evidence confidence: {evidence_score:.1f}% (weight: {weights['evidence']*100:.0f}%)
        
        This confidence score reflects the strength of the lipid analysis,
        disease predictions, and supporting evidence.
        """
        
        return {
            'score': round(overall_score, 1),
            'confidence_level': confidence_level,
            'confidence_emoji': confidence_emoji,
            'components': {
                'rule': rule_score,
                'disease': disease_score,
                'evidence': evidence_score
            },
            'breakdown': breakdown,
            'explanation': explanation.strip()
        }
    
    def calculate_full_confidence(self,
                                 rule_results: Dict[str, Any],
                                 disease_predictions: List[Dict[str, Any]],
                                 guidelines: List[Dict[str, Any]],
                                 mimic_evidence: Dict[str, Any],
                                 weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Calculate all confidence scores in one call.
        
        Args:
            rule_results: From rule_engine.evaluate()
            disease_predictions: From disease_engine.predict()
            guidelines: From guidelines_engine.get_guidelines()
            mimic_evidence: From mimic_engine.get_evidence()
            weights: Optional custom weights for overall confidence
            
        Returns:
            Complete confidence report
        """
        # Calculate individual confidences
        rule_conf = self.calculate_rule_confidence(rule_results)
        disease_conf = self.calculate_disease_confidence(disease_predictions)
        evidence_conf = self.calculate_evidence_confidence(guidelines, mimic_evidence)
        
        # Calculate overall confidence
        overall_conf = self.calculate_overall_confidence(
            rule_conf,
            disease_conf,
            evidence_conf,
            weights
        )
        
        return {
            'overall': overall_conf,
            'rule_confidence': rule_conf,
            'disease_confidence': disease_conf,
            'evidence_confidence': evidence_conf,
            'calculated_at': datetime.now().isoformat()
        }


# Module-level singleton
_confidence_engine = None


def get_confidence_engine() -> ConfidenceEngine:
    """
    Get or create the singleton ConfidenceEngine instance.
    """
    global _confidence_engine
    if _confidence_engine is None:
        _confidence_engine = ConfidenceEngine()
    return _confidence_engine