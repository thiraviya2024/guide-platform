# clinical/recommendation_engine.py
from typing import Dict

def get_lifestyle_recommendations(risk_data: Dict) -> str:
    """Return general lifestyle suggestions."""
    recommendations = [
        "• Eat more vegetables, fruits, and whole grains",
        "• Exercise regularly (at least 30 minutes most days)",
        "• Maintain a healthy weight",
        "• Avoid smoking and limit alcohol",
        "• Get enough good sleep"
    ]
    
    if risk_data.get("overall_risk") in ["High Risk", "Very High Risk"]:
        recommendations.insert(0, "⚠️ Consider discussing these results with your doctor soon.")
    
    return "\n".join(recommendations)