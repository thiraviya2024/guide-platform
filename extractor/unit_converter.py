# lipid-ai/extractor/unit_converter.py
"""
Handles unit normalization and conversion.
"""

def convert_to_mgdl(value: float, unit: str) -> float:
    """Convert common units to mg/dL (standard)."""
    if not unit or "mmol" in unit.lower():
        # Approximate conversion factor for lipids
        return value * 38.67  # Rough for cholesterol
    return value  # Assume already mg/dL