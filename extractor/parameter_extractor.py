import re
from typing import Dict
from utils.logger import logger

SEARCH_WINDOW = 300


def _clean_text(text: str):
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _find_value(text: str, keywords):

    lower = text.lower()

    for key in keywords:

        pos = lower.find(key.lower())

        if pos == -1:
            continue

        section = text[pos:pos + SEARCH_WINDOW]

        # Prefer decimal numbers (real lab values)
        decimal_matches = re.findall(r"\d+\.\d+", section)

        candidates = []

        for n in decimal_matches:

            value = float(n)

            # Skip analyzer model numbers
            if value in [480.0, 580.0, 680.0]:
                continue

            if value > 1000:
                continue

            candidates.append(value)

        if candidates:
            return candidates[0]

        # Fallback to integers
        integer_matches = re.findall(r"\b\d+\b", section)

        for n in integer_matches:

            value = float(n)

            if value in [480, 580, 680]:
                continue

            if value > 1000:
                continue

            return value

    return None


def extract_lipid_parameters(raw_text: str, structured_data=None) -> Dict[str, float]:

    text = _clean_text(raw_text)

    parameters = {}

    parameter_map = {

        "total_cholesterol": [
            "total cholesterol"
        ],

        "triglycerides": [
            "serum triglycerides",
            "triglycerides",
            "tg"
        ],

        "hdl": [
            "serum hdl cholesterol",
            "hdl cholesterol"
        ],

        "ldl": [
            "ldl cholesterol calculated",
            "ldl cholesterol"
        ],

        "vldl": [
            "vldl cholesterol calculated",
            "vldl cholesterol"
        ],

        "non_hdl": [
            "non-hdl cholesterol"
        ]

    }

    for parameter, keywords in parameter_map.items():

        value = _find_value(text, keywords)

        if value is not None:
            parameters[parameter] = value

    logger.info(f"Extracted Lipid Parameters: {parameters}")

    return parameters