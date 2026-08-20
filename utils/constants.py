# utils/constants.py
from enum import Enum

class RiskLevel(str, Enum):
    NORMAL = "Normal"
    BORDERLINE = "Borderline"
    HIGH = "High"
    VERY_HIGH = "Very High"
    CRITICAL = "Critical"