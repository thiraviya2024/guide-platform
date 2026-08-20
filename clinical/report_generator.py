"""
Enhanced Report Generator for LipidAI
Generates comprehensive patient report with all modules integrated.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates the final patient report from all analysis components.
    """
    
    def __init__(self):
        """Initialize the report generator."""
        pass
    
    def generate_report(self,
                       patient_info: Dict[str, Any],
                       rule_results: Dict[str, Any],
                       disease_predictions: List[Dict[str, Any]],
                       exercise_data: Dict[str, Any],
                       medication_data: List[Dict[str, Any]],
                       followup_tests: List[Dict[str, Any]],
                       guidelines: List[Dict[str, Any]],
                       mimic_evidence: Dict[str, Any],
                       confidence: Dict[str, Any],
                       ai_explanation: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate the complete patient report.
        
        Returns:
            Dictionary with all report sections
        """
        report = {
            'report_id': f"LIPID-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'patient_info': patient_info,
            'sections': {
                'summary': self._generate_summary(rule_results, disease_predictions, confidence),
                'abnormal_parameters': self._generate_abnormal_parameters(rule_results),
                'disease_predictions': self._generate_disease_section(disease_predictions),
                'clinical_evidence': self._generate_evidence_section(guidelines, mimic_evidence),
                'medications': self._generate_medication_section(medication_data),
                'diet_recommendations': self._generate_diet_section(rule_results),
                'exercise_plan': self._generate_exercise_section(exercise_data),
                'lifestyle_changes': self._generate_lifestyle_section(rule_results, disease_predictions),
                'followup_tests': self._generate_followup_section(followup_tests),
                'confidence_score': self._generate_confidence_section(confidence),
                'ai_explanation': self._generate_ai_section(ai_explanation),
                'disclaimer': self._generate_disclaimer()
            }
        }
        
        return report
    
    def _generate_summary(self, rule_results: Dict, disease_predictions: List, confidence: Dict) -> str:
        """Generate the summary section."""
        total_params = 0
        abnormal_params = 0
        
        for param, data in rule_results.items():
            if isinstance(data, dict):
                total_params += 1
                status = data.get('status', 'Unknown')
                if status not in ['Normal', 'Unknown', 'No rule found']:
                    abnormal_params += 1
        
        disease_count = len(disease_predictions)
        confidence_level = confidence.get('overall', {}).get('confidence_level', 'Unknown')
        confidence_score = confidence.get('overall', {}).get('score', 0)
        
        summary = f"""
**Patient Lipid Profile Summary**

- **Total Parameters Analyzed:** {total_params}
- **Abnormal Parameters Found:** {abnormal_params}
- **Diseases Identified:** {disease_count}
- **Overall Confidence Level:** {confidence_level} ({confidence_score:.1f}%)

**Overview:**
This report analyzes your lipid profile and provides personalized recommendations based on established clinical guidelines. The analysis identified {abnormal_params} parameters outside the normal range and predicted {disease_count} potential conditions.

**Key Findings:**
"""
        for disease in disease_predictions[:3]:
            summary += f"\n- **{disease.get('disease_name')}** - {disease.get('description', '')[:100]}..."
        
        if not disease_predictions:
            summary += "\n- No significant disease patterns detected. Continue maintaining a healthy lifestyle."
        
        return summary
    
    def _generate_abnormal_parameters(self, rule_results: Dict) -> str:
        """Generate the abnormal parameters section."""
        abnormal = []
        normal = []
        
        for param, data in rule_results.items():
            if isinstance(data, dict):
                status = data.get('status', 'Unknown')
                value = data.get('value', 'N/A')
                recommendation = data.get('recommendation', '')
                
                param_info = {
                    'name': param.replace('_', ' ').title(),
                    'value': value,
                    'status': status,
                    'recommendation': recommendation
                }
                
                if status not in ['Normal', 'Unknown', 'No rule found']:
                    abnormal.append(param_info)
                else:
                    normal.append(param_info)
        
        text = "### Abnormal Parameters\n\n"
        
        if abnormal:
            for param in abnormal:
                text += f"**{param['name']}:** {param['value']} mg/dL - **{param['status']}**\n"
                if param['recommendation']:
                    text += f"  - Recommendation: {param['recommendation']}\n"
                text += "\n"
        else:
            text += "✅ All parameters are within normal range. Great job!\n\n"
        
        text += "### Normal Parameters\n\n"
        for param in normal[:5]:
            text += f"- {param['name']}: {param['value']} mg/dL ({param['status']})\n"
        
        if len(normal) > 5:
            text += f"\n... and {len(normal) - 5} other parameters are normal.\n"
        
        return text
    
    def _generate_disease_section(self, disease_predictions: List) -> str:
        """Generate the disease predictions section."""
        if not disease_predictions:
            return "### Disease Predictions\n\nNo significant disease patterns identified in this analysis.\n"
        
        text = "### Disease Predictions\n\n"
        text += "Based on your lipid profile, the following conditions have been identified:\n\n"
        
        for disease in disease_predictions:
            text += f"**{disease.get('disease_name')}**\n"
            text += f"- **Severity:** {disease.get('severity_level', 'Unknown')}\n"
            text += f"- **Confidence:** {disease.get('confidence_score', 0):.1f}%\n"
            text += f"- **Description:** {disease.get('description', 'N/A')}\n"
            
            if disease.get('management_strategy'):
                text += f"- **Management:** {disease.get('management_strategy')}\n"
            
            if disease.get('referral_needed', False):
                text += f"- **⚠️ Specialist Referral Recommended:** {disease.get('specialist_type', 'Cardiologist')}\n"
            
            text += "\n---\n\n"
        
        return text
    
    def _generate_evidence_section(self, guidelines: List, mimic_evidence: Dict) -> str:
        """Generate the clinical evidence section."""
        text = "### Supporting Clinical Evidence\n\n"
        
        if guidelines:
            text += "#### Clinical Guidelines Cited\n\n"
            for g in guidelines[:3]:
                text += f"**{g.get('guideline_name')}** ({g.get('guideline_year', 'N/A')})\n"
                text += f"- Organization: {g.get('guideline_organization', 'N/A')}\n"
                text += f"- Recommendation: {g.get('recommendation', 'N/A')[:150]}...\n"
                if g.get('recommendation_class'):
                    text += f"- Class: {g.get('recommendation_class')} | Evidence: {g.get('evidence_level', 'N/A')}\n"
                text += "\n"
        else:
            text += "No specific clinical guidelines cited for this analysis.\n\n"
        
        text += "#### Population Evidence\n\n"
        found_evidence = False
        for disease, data in mimic_evidence.items():
            if data.get('found', False):
                found_evidence = True
                text += f"**{disease}:**\n"
                if data.get('prevalence_in_mimic'):
                    text += f"- Prevalence in hospitalized patients: {data['prevalence_in_mimic']}%\n"
                if data.get('mortality_rate'):
                    text += f"- Mortality rate: {data['mortality_rate']}%\n"
                if data.get('common_complications'):
                    complications = data['common_complications'][:3]
                    text += f"- Common complications: {', '.join(complications)}\n"
                if data.get('supporting_evidence'):
                    text += f"- {data['supporting_evidence']}\n"
                text += "\n"
        
        if not found_evidence:
            text += "Population-level evidence is limited for this specific profile.\n"
        
        text += "\n*Note: MIMIC-IV data is for educational/supporting purposes only.*\n"
        
        return text
    
    def _generate_medication_section(self, medication_data: List) -> str:
        """Generate the medication education section."""
        if not medication_data:
            return "### Medication Information\n\nNo medication information available for this profile.\n"
        
        text = "### Medication Categories (Educational Only)\n\n"
        text += "⚠️ **IMPORTANT:** This information is for educational purposes only. "
        text += "Never start, stop, or change medications without consulting your healthcare provider.\n\n"
        
        for med in medication_data:
            text += f"**{med.get('medication_class')}**\n"
            if med.get('drug_names'):
                text += f"- **Drugs:** {', '.join(med['drug_names'][:4])}\n"
            if med.get('mechanism_of_action'):
                text += f"- **Mechanism:** {med['mechanism_of_action']}\n"
            if med.get('common_indications'):
                text += f"- **Common Indications:** {', '.join(med['common_indications'][:3])}\n"
            if med.get('side_effects'):
                text += f"- **Common Side Effects:** {', '.join(med['side_effects'][:4])}\n"
            if med.get('safety_note'):
                text += f"- **Safety Note:** {med['safety_note']}\n"
            text += "\n"
        
        return text
    
    def _generate_diet_section(self, rule_results: Dict) -> str:
        """Generate the diet recommendations section."""
        text = "### Diet Recommendations\n\n"
        
        food_suggestions = []
        for param, data in rule_results.items():
            if isinstance(data, dict):
                if 'food' in data and data['food']:
                    food_suggestions.extend(data['food'].split(', '))
        
        if food_suggestions:
            unique_foods = list(set(food_suggestions))
            text += "Based on your lipid profile, consider incorporating:\n\n"
            for food in unique_foods[:10]:
                text += f"- {food}\n"
        else:
            text += """
**General Dietary Recommendations:**

- **Mediterranean Diet:** Rich in fruits, vegetables, whole grains, legumes, and olive oil
- **Limit Saturated Fats:** Reduce red meat, full-fat dairy, processed foods
- **Increase Fiber:** Aim for 25-30g of fiber daily
- **Healthy Fats:** Include avocados, nuts, seeds, and fatty fish
- **Limit Added Sugars:** Reduce sugary beverages, desserts, and processed snacks
"""
        
        text += "\n*Consult a dietitian for personalized advice.*\n"
        
        return text
    
    def _generate_exercise_section(self, exercise_data: Dict) -> str:
        """Generate the exercise plan section."""
        text = "### Exercise Plan\n\n"
        
        found_exercise = False
        for disease, data in exercise_data.items():
            if data.get('found', False):
                found_exercise = True
                text += f"**For {disease}:**\n"
                text += f"- **Exercise Type:** {data.get('exercise_type', 'N/A')}\n"
                text += f"- **Frequency:** {data.get('frequency', 'N/A')}\n"
                text += f"- **Intensity:** {data.get('intensity', 'N/A')}\n"
                text += f"- **Duration:** {data.get('duration', 'N/A')}\n"
                if data.get('precautions'):
                    text += f"- **Precautions:** {data.get('precautions')}\n"
                text += "\n"
        
        if not found_exercise:
            text += """
**General Exercise Recommendations:**

- **Aerobic Exercise:** 150 minutes moderate-intensity OR 75 minutes vigorous-intensity per week
- **Resistance Training:** 2-3 days per week
- **Safety:** Warm up before exercise and cool down after
"""
        
        text += "\n*Consult your healthcare provider before starting any new exercise program.*\n"
        
        return text
    
    def _generate_lifestyle_section(self, rule_results: Dict, disease_predictions: List) -> str:
        """Generate the lifestyle changes section."""
        text = "### Lifestyle Changes\n\n"
        
        lifestyle_tips = [
            "**Smoking Cessation:** Seek support to quit smoking",
            "**Alcohol Moderation:** Limit alcohol to 1 drink/day (women) or 2 drinks/day (men)",
            "**Weight Management:** Maintain healthy BMI (18.5-24.9)",
            "**Stress Management:** Practice mindfulness, meditation, or yoga",
            "**Sleep:** Aim for 7-9 hours of quality sleep per night",
            "**Hydration:** Drink adequate water (8-10 glasses daily)"
        ]
        
        for disease in disease_predictions:
            disease_name = disease.get('disease_name', '').lower()
            if 'metabolic' in disease_name:
                lifestyle_tips.insert(0, "**Blood Sugar Control:** Monitor blood glucose; follow diabetic-friendly diet")
        
        for tip in lifestyle_tips:
            text += f"- {tip}\n\n"
        
        return text
    
    def _generate_followup_section(self, followup_tests: List) -> str:
        """Generate the follow-up tests section."""
        if not followup_tests:
            return "### Follow-up Tests\n\nNo specific follow-up tests recommended.\n"
        
        text = "### Recommended Follow-up Tests\n\n"
        
        high_priority = [t for t in followup_tests if t.get('priority') == 'High']
        medium_priority = [t for t in followup_tests if t.get('priority') == 'Medium']
        
        if high_priority:
            text += "#### High Priority\n\n"
            for test in high_priority:
                text += f"**{test.get('test_name')}**\n"
                text += f"- **Frequency:** {test.get('frequency', 'N/A')}\n"
                if test.get('rationale'):
                    text += f"- **Why:** {test.get('rationale')}\n"
                if test.get('target_range'):
                    text += f"- **Target Range:** {test.get('target_range')}\n"
                text += "\n"
        
        if medium_priority:
            text += "#### Medium Priority\n\n"
            for test in medium_priority[:5]:
                text += f"- **{test.get('test_name')}** ({test.get('frequency', 'N/A')})\n"
                if test.get('rationale'):
                    text += f"  - {test.get('rationale')}\n"
                text += "\n"
        
        text += "\n*Follow-up with your healthcare provider to schedule these tests.*\n"
        
        return text
    
    def _generate_confidence_section(self, confidence: Dict) -> str:
        """Generate the confidence score section."""
        overall = confidence.get('overall', {})
        rule_conf = confidence.get('rule_confidence', {})
        disease_conf = confidence.get('disease_confidence', {})
        evidence_conf = confidence.get('evidence_confidence', {})
        
        text = "### Confidence Score\n\n"
        text += f"**Overall Confidence:** {overall.get('score', 0):.1f}% "
        text += f"({overall.get('confidence_level', 'Unknown')})\n\n"
        text += f"{overall.get('confidence_emoji', '')}\n\n"
        
        text += "**Component Breakdown:**\n\n"
        text += f"- **Rule Confidence:** {rule_conf.get('score', 0):.1f}%\n"
        text += f"- **Disease Confidence:** {disease_conf.get('score', 0):.1f}%\n"
        text += f"- **Evidence Confidence:** {evidence_conf.get('score', 0):.1f}%\n"
        
        return text
    
    def _generate_ai_section(self, ai_explanation: Dict) -> str:
        """Generate the AI explanation section."""
        text = "### AI-Powered Explanation\n\n"
        
        if ai_explanation.get('summary'):
            text += f"**Summary:**\n{ai_explanation['summary']}\n\n"
        
        if ai_explanation.get('detailed_explanation'):
            text += f"**Detailed Analysis:**\n{ai_explanation['detailed_explanation']}\n\n"
        
        if ai_explanation.get('recommendations'):
            text += f"**Recommendations:**\n{ai_explanation['recommendations']}\n\n"
        
        if not any(ai_explanation.values()):
            text += "AI explanation is not available. Please consult your healthcare provider.\n"
        
        return text
    
    def _generate_disclaimer(self) -> str:
        """Generate the medical disclaimer section."""
        return """
⚠️ **MEDICAL DISCLAIMER**

This report is for **educational and informational purposes only** and does not constitute medical advice.

**Important Notes:**
1. **Not a Diagnosis:** This report does not diagnose or treat any medical condition.
2. **Not a Replacement:** This report is not a replacement for professional medical advice.
3. **Consult Your Doctor:** Always consult your healthcare provider before making health decisions.
4. **Emergency:** If you are experiencing a medical emergency, call emergency services.

**By using this report, you agree to the above terms.**

**Always prioritize the advice of your healthcare provider.**
"""


# Module-level singleton
_report_generator = None


def get_report_generator() -> ReportGenerator:
    """Get or create the singleton ReportGenerator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


# Module-level instance
report_generator = get_report_generator()