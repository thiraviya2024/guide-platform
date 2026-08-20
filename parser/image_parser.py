from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from utils.logger import logger

# Try to import pytesseract
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed. OCR will be disabled.")


def preprocess_image(image_path: Path):
    """
    Improve image quality before OCR.
    """
    try:
        img = Image.open(image_path).convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        return img
    except Exception as e:
        logger.error(f"Image preprocessing error: {e}")
        return None


def extract_text_from_image(file_path: Path) -> str:
    """
    Extract text using Tesseract OCR.
    """
    if not TESSERACT_AVAILABLE:
        logger.error("Tesseract not available. Install pytesseract and tesseract-ocr.")
        return ""

    try:
        img = preprocess_image(file_path)
        if img is None:
            return ""

        # Tesseract OCR
        text = pytesseract.image_to_string(
            img,
            lang='eng',
            config='--psm 6 --oem 3'
        )

        text = text.strip()
        logger.info(f"OCR Extracted Text:\n{text}")

        return text

    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return ""
