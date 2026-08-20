# clinical/classifier.py
from typing import Dict

def classify_value(param: str, value: float) -> Dict:
    if param == "hdl":
        if value < 40:
            return {"status": "Low"}
        elif value >= 60:
            return {"status": "High"}
        else:
            return {"status": "Normal"}
    
    elif param == "ldl":
        if value < 100:
            return {"status": "Optimal"}
        elif value < 130:
            return {"status": "Near Optimal"}
        elif value < 160:
            return {"status": "Borderline"}
        elif value < 190:
            return {"status": "High"}
        else:
            return {"status": "Very High"}
    
    elif param == "triglycerides":
        if value < 150:
            return {"status": "Normal"}
        elif value < 200:
            return {"status": "Borderline"}
        elif value < 500:
            return {"status": "High"}
        else:
            return {"status": "Very High"}
    
    else:  # total_cholesterol
        if value < 200:
            return {"status": "Normal"}
        elif value < 240:
            return {"status": "Borderline"}
        else:
            return {"status": "High"}