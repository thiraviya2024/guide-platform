"""
ai/explanation.py

Groq-powered explanation generator.
The AI ONLY explains rule-based findings.
It never classifies values or determines thresholds.
"""

from __future__ import annotations

from typing import Dict, Any

from utils.logger import logger

try:
    from groq import Groq
except ImportError:
    Groq = None

from config.settings import GROQ_API_KEY, MODEL_NAME


def _get_groq_client():

    if not Groq or not GROQ_API_KEY:
        return None

    try:
        return Groq(api_key=GROQ_API_KEY)

    except Exception as e:

        logger.error(
            f"Groq client init failed: {e}"
        )

        return None


def generate_clinical_explanation(
    analyzed_data: Dict[str, Any]
) -> str:
    """
    Generate patient-friendly explanation.
    """

    client = _get_groq_client()

    if not client:
        return _offline_fallback(
            analyzed_data
        )

    prompt = _build_safe_prompt(
        analyzed_data
    )

    try:

        response = (
            client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a clinical explanation assistant. "
                            "You must ONLY explain supplied findings. "
                            "Do not recalculate risk. "
                            "Do not change statuses. "
                            "Do not create new diagnoses."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.3,
                max_tokens=800,
            )
        )

        return (
            response
            .choices[0]
            .message.content
            .strip()
        )

    except Exception as e:

        logger.error(
            f"Groq call failed: {e}"
        )

        return _offline_fallback(
            analyzed_data
        )


def _build_safe_prompt(
    analyzed_data: Dict[str, Any]
) -> str:

    overall_risk = analyzed_data.get(
        "overall_risk",
        "Unknown"
    )

    risk_score = analyzed_data.get(
        "risk_score",
        "Unknown"
    )

    lines = [
        f"Overall Risk: {overall_risk}",
        f"Risk Score: {risk_score}",
        ""
    ]

    for name, data in analyzed_data.items():

        if name in (
            "overall_risk",
            "risk_score"
        ):
            continue

        if not isinstance(data, dict):
            continue

        lines.append(
            f"- {name}"
            f" | Value: {data.get('value')}"
            f" | Status: {data.get('status')}"
            f" | Recommendation: {data.get('recommendation')}"
        )

    return f"""
Explain these lipid profile findings in simple,
patient-friendly language.

Include:

1. Summary
2. Abnormal parameters
3. Lifestyle advice
4. Diet suggestions
5. Exercise suggestions
6. When to consult a doctor
7. Disclaimer

Data:

{chr(10).join(lines)}

Do NOT change statuses.
Do NOT recalculate risk.
Do NOT invent diagnoses.
"""


def _offline_fallback(
    analyzed_data: Dict[str, Any]
) -> str:

    overall_risk = analyzed_data.get(
        "overall_risk",
        "Unknown"
    )

    risk_score = analyzed_data.get(
        "risk_score",
        "Unknown"
    )

    text = [
        f"## Overall Risk",
        f"**{overall_risk}**",
        "",
        f"Risk Score: {risk_score}",
        "",
        "## Findings"
    ]

    for name, data in analyzed_data.items():

        if name in (
            "overall_risk",
            "risk_score"
        ):
            continue

        if not isinstance(data, dict):
            continue

        text.append(
            f"- **{name.replace('_', ' ').title()}** "
            f"({data.get('value')}) → "
            f"{data.get('status')} "
            f"({data.get('recommendation')})"
        )

    text.extend([
        "",
        "## Recommendations",
        "- Maintain a balanced diet.",
        "- Engage in regular exercise.",
        "- Consult a physician if abnormal values persist.",
        "",
        "## Disclaimer",
        "This report is educational and does not replace professional medical advice."
    ])

    return "\n".join(text)