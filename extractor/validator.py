from utils.logger import logger


def is_lipid_report(raw_text: str) -> bool:
    """
    Detect whether uploaded report is a lipid profile.
    """

    if not raw_text:
        return False

    text = raw_text.lower()

    keywords = [
        "lipid profile",
        "lipid",
        "cholesterol",
        "total cholesterol",
        "hdl",
        "ldl",
        "triglycerides",
        "serum triglycerides",
        "vldl",
        "chol/hdl",
        "non-hdl"
    ]

    matches = [k for k in keywords if k in text]

    logger.info(f"Lipid keywords found: {matches}")

    return len(matches) >= 2