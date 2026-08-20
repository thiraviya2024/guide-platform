# report/report_generator.py
from typing import Dict
from pathlib import Path
from datetime import datetime

def generate_summary_report(lipid_data: Dict, explanation: str, original_filename: str) -> str:
    """Simple placeholder for PDF generation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/LipidAI_Report_{timestamp}.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== LipidAI Report ===\n\n")
        f.write(f"Original File: {original_filename}\n")
        f.write(f"Generated: {datetime.now()}\n\n")
        f.write("Results:\n")
        for k, v in lipid_data.items():
            if k != "overall_risk":
                f.write(f"{k}: {v}\n")
        f.write(f"\nOverall Risk: {lipid_data.get('overall_risk', 'Unknown')}\n\n")
        f.write(explanation)
    
    return output_path