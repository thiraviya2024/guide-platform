# ai/prompt.py
from typing import Dict

def create_explanation_prompt(lipid_data: Dict) -> str:
    """Create prompt for Ollama"""
    data_str = ""
    for k, v in lipid_data.items():
        if k != "overall_risk":
            data_str += f"{k.replace('_', ' ').title()}: {v.get('value', v)} mg/dL ({v.get('status', '')})\n"
    
    overall = lipid_data.get("overall_risk", "Unknown")
    
    prompt = f"""You are a helpful medical educator. Explain these lipid results in very simple language.

Results:
{data_str}
Overall Risk: {overall}

Rules:
- Use simple, easy words
- Do not diagnose disease
- Do not recommend medicine
- Always say to consult a doctor
- Keep it short and positive

Write a friendly summary:"""
    return prompt