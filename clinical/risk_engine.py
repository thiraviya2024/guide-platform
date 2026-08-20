"""
Risk Engine for LipidAI.
Aggregates already-decided statuses into an overall risk level.
Does NOT re-classify anything itself - only uses existing statuses.
"""

from typing import Dict, Any

# Internal aggregation weights (not clinical thresholds)
STATUS_WEIGHTS = {
    "Very High": 4,
    "High": 3,
    "Borderline High": 2,
    "Unknown": 1,
    "Normal": 0
}


def calculate_overall_risk(rule_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate overall risk based on per-parameter statuses.
    Returns the original data with 'overall_risk' and 'risk_score' added.
    """
    # Make a copy to avoid modifying original
    analyzed_data = rule_results.copy()
    
    total_weight = 0
    count = 0
    
    for param, data in rule_results.items():
        if isinstance(data, dict):
            status = data.get('status', 'Unknown')
            weight = STATUS_WEIGHTS.get(status, 0)
            total_weight += weight
            count += 1
    
    # Calculate average risk score
    risk_score = total_weight / count if count > 0 else 0
    
    # Determine overall risk level
    if risk_score >= 3.5:
        overall_risk = "Very High Risk"
    elif risk_score >= 2.5:
        overall_risk = "High Risk"
    elif risk_score >= 1.5:
        overall_risk = "Moderate Risk"
    elif risk_score >= 0.5:
        overall_risk = "Low Risk"
    else:
        overall_risk = "Normal"
    
    analyzed_data['overall_risk'] = overall_risk
    analyzed_data['risk_score'] = risk_score
    
    return analyzed_data