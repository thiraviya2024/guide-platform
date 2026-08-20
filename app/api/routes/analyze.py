# app/api/routes/analyze.py
"""
Analysis API Routes - Full File Upload Support
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import Optional, Dict, Any
from pydantic import BaseModel
import os
import shutil
from datetime import datetime
import io
import re
import logging

from app.services.lipid_service import LipidService
from app.services.cbc_service import CBCService
from app.services.lft_service import LFTService
from app.services.kft_service import KFTService
from app.services.thyroid_service import ThyroidService
from app.services.diabetes_service import DiabetesService
from app.services.vitamins_service import VitaminsService
from app.services.electrolytes_service import ElectrolytesService
from app.engines.extraction_engine.cbc_extractor import CBCExtractor
from app.engines.extraction_engine.lipid_extractor import LipidExtractor

logger = logging.getLogger(__name__)

# ✅ THIS IS THE FIX - router must be defined
router = APIRouter()


class LipidValues(BaseModel):
    total_cholesterol: Optional[float] = None
    ldl: Optional[float] = None
    hdl: Optional[float] = None
    triglycerides: Optional[float] = None
    vldl: Optional[float] = None
    non_hdl: Optional[float] = None


class ManualEntryRequest(BaseModel):
    lipid_values: Optional[LipidValues] = None
    cbc_values: Optional[Dict[str, float]] = None
    lft_values: Optional[Dict[str, float]] = None
    kft_values: Optional[Dict[str, float]] = None
    thyroid_values: Optional[Dict[str, float]] = None
    diabetes_values: Optional[Dict[str, float]] = None
    vitamins_values: Optional[Dict[str, float]] = None
    electrolytes_values: Optional[Dict[str, float]] = None
    patient_info: Optional[Dict[str, Any]] = None


# ============================================================
# FILE EXTRACTION FUNCTIONS
# ============================================================

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF files."""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except ImportError:
        return "PDF parsing requires pdfplumber. Install: pip install pdfplumber"
    except Exception as e:
        return f"PDF parsing error: {str(e)}"


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files."""
    try:
        import docx
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except ImportError:
        return "DOCX parsing requires python-docx. Install: pip install python-docx"
    except Exception as e:
        return f"DOCX parsing error: {str(e)}"


def extract_text_from_excel(file_path: str) -> str:
    """Extract text from Excel files."""
    try:
        import pandas as pd
        df = pd.read_excel(file_path, engine='openpyxl')
        return df.to_string()
    except ImportError:
        return "Excel parsing requires pandas and openpyxl. Install: pip install pandas openpyxl"
    except Exception as e:
        return f"Excel parsing error: {str(e)}"


def extract_text_from_image(file_path: str) -> str:
    """Extract text from images using OCR."""
    try:
        from PIL import Image
        import pytesseract
        from pdf2image import convert_from_path
        
        # For images
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.tiff')):
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        
        # For PDF with images (requires pdf2image)
        elif file_path.lower().endswith('.pdf'):
            images = convert_from_path(file_path)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
            return text
            
    except ImportError:
        return "OCR requires pytesseract, Pillow, and pdf2image. Install: pip install pytesseract Pillow pdf2image"
    except Exception as e:
        return f"OCR error: {str(e)}"


def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """Extract text from various file types."""
    text_content = ""
    
    try:
        if file_extension in ['.txt', '.csv']:
            # Read text files directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
                
        elif file_extension == '.pdf':
            text_content = extract_text_from_pdf(file_path)
            
        elif file_extension in ['.docx', '.doc']:
            text_content = extract_text_from_docx(file_path)
            
        elif file_extension in ['.xlsx', '.xls']:
            text_content = extract_text_from_excel(file_path)
            
        elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.tiff']:
            text_content = extract_text_from_image(file_path)
            
        else:
            text_content = f"File uploaded. Manual analysis not available for {file_extension} files."
            
    except Exception as e:
        text_content = f"Error extracting text: {str(e)}"
    
    return text_content


def parse_lab_values(text: str, module: str) -> Dict[str, float]:
    """Parse lab values from text using regex patterns."""
    values = {}
    text_lower = text.lower()
    
    patterns = {
        'cbc': {
            'hemoglobin': r'(?:hemoglobin|hb|hgb)\s*[:]?\s*([\d.]+)',
            'wbc': r'(?:wbc|white blood cells?)\s*[:]?\s*([\d.]+)',
            'platelets': r'(?:platelets?|plt)\s*[:]?\s*([\d.]+)',
            'rbc': r'(?:rbc|red blood cells?)\s*[:]?\s*([\d.]+)',
            'neutrophils': r'(?:neutrophils?|neut)\s*[:]?\s*([\d.]+)',
            'lymphocytes': r'(?:lymphocytes?|lymph)\s*[:]?\s*([\d.]+)',
        },
        'lipid': {
            'total_cholesterol': r'(?:total cholesterol|tc)\s*[:]?\s*([\d.]+)',
            'ldl': r'(?:ldl|ldl cholesterol)\s*[:]?\s*([\d.]+)',
            'hdl': r'(?:hdl|hdl cholesterol)\s*[:]?\s*([\d.]+)',
            'triglycerides': r'(?:triglycerides|tg)\s*[:]?\s*([\d.]+)',
            'vldl': r'(?:vldl)\s*[:]?\s*([\d.]+)',
            'non_hdl': r'(?:non.hdl|non hdl)\s*[:]?\s*([\d.]+)',
        },
        'lft': {
            'alt': r'(?:alt|alanine transaminase|sgpt)\s*[:]?\s*([\d.]+)',
            'ast': r'(?:ast|aspartate transaminase|sgot)\s*[:]?\s*([\d.]+)',
            'alp': r'(?:alp|alkaline phosphatase)\s*[:]?\s*([\d.]+)',
            'total_bilirubin': r'(?:total bilirubin|t\.?bilirubin)\s*[:]?\s*([\d.]+)',
            'direct_bilirubin': r'(?:direct bilirubin|d\.?bilirubin)\s*[:]?\s*([\d.]+)',
            'total_protein': r'(?:total protein|t\.?protein)\s*[:]?\s*([\d.]+)',
            'albumin': r'(?:albumin|alb)\s*[:]?\s*([\d.]+)',
            'globulin': r'(?:globulin|glob)\s*[:]?\s*([\d.]+)',
            'ag_ratio': r'(?:a/g ratio|ag ratio)\s*[:]?\s*([\d.]+)',
            'ggt': r'(?:ggt|gamma-glutamyl transferase)\s*[:]?\s*([\d.]+)',
        },
        'kft': {
            'creatinine': r'(?:creatinine|creat)\s*[:]?\s*([\d.]+)',
            'bun': r'(?:bun|blood urea nitrogen|urea)\s*[:]?\s*([\d.]+)',
            'uric_acid': r'(?:uric acid|urate)\s*[:]?\s*([\d.]+)',
            'sodium': r'(?:sodium|na)\s*[:]?\s*([\d.]+)',
            'potassium': r'(?:potassium|k)\s*[:]?\s*([\d.]+)',
            'chloride': r'(?:chloride|cl)\s*[:]?\s*([\d.]+)',
            'bicarbonate': r'(?:bicarbonate|hco3)\s*[:]?\s*([\d.]+)',
            'egfr': r'(?:egfr|gfr|estimated gfr)\s*[:]?\s*([\d.]+)',
        },
        'thyroid': {
            'tsh': r'(?:tsh|thyroid stimulating hormone)\s*[:]?\s*([\d.]+)',
            't3': r'(?:t3|triiodothyronine)\s*[:]?\s*([\d.]+)',
            't4': r'(?:t4|thyroxine)\s*[:]?\s*([\d.]+)',
            'free_t3': r'(?:free t3|ft3)\s*[:]?\s*([\d.]+)',
            'free_t4': r'(?:free t4|ft4)\s*[:]?\s*([\d.]+)',
        },
        'diabetes': {
            'fasting_glucose': r'(?:fasting glucose|fbs|fbg)\s*[:]?\s*([\d.]+)',
            'hba1c': r'(?:hba1c|a1c|hemoglobin a1c)\s*[:]?\s*([\d.]+)',
            'insulin': r'(?:insulin)\s*[:]?\s*([\d.]+)',
            'homa_ir': r'(?:homa-ir|homa ir)\s*[:]?\s*([\d.]+)',
            'postprandial_glucose': r'(?:postprandial|ppbs)\s*[:]?\s*([\d.]+)',
        },
        'vitamins': {
            'vitamin_b12': r'(?:vitamin b12|b12)\s*[:]?\s*([\d.]+)',
            'vitamin_d': r'(?:vitamin d|vitamin d3|25-oh d)\s*[:]?\s*([\d.]+)',
            'folate': r'(?:folate|folic acid)\s*[:]?\s*([\d.]+)',
            'iron': r'(?:iron|serum iron)\s*[:]?\s*([\d.]+)',
            'ferritin': r'(?:ferritin)\s*[:]?\s*([\d.]+)',
        },
        'electrolytes': {
            'calcium': r'(?:calcium|ca)\s*[:]?\s*([\d.]+)',
            'magnesium': r'(?:magnesium|mg)\s*[:]?\s*([\d.]+)',
            'phosphorus': r'(?:phosphorus|phosphate)\s*[:]?\s*([\d.]+)',
        }
    }
    
    module_patterns = patterns.get(module, {})
    for param, pattern in module_patterns.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            try:
                values[param] = float(match.group(1))
            except ValueError:
                continue
    
    return values


# ============================================================
# API ENDPOINTS
# ============================================================

@router.post("/analyze/manual")
async def analyze_manual(
    module: str = Query(..., description="Module to analyze: lipid, cbc, lft, kft, thyroid, diabetes, vitamins, electrolytes"),
    request: ManualEntryRequest = None
):
    """Analyze manual entry for any module."""
    try:
        service_map = {
            "lipid": (LipidService, "lipid_values"),
            "cbc": (CBCService, "cbc_values"),
            "lft": (LFTService, "lft_values"),
            "kft": (KFTService, "kft_values"),
            "thyroid": (ThyroidService, "thyroid_values"),
            "diabetes": (DiabetesService, "diabetes_values"),
            "vitamins": (VitaminsService, "vitamins_values"),
            "electrolytes": (ElectrolytesService, "electrolytes_values"),
        }
        
        if module not in service_map:
            raise HTTPException(status_code=400, detail=f"Unknown module: {module}")
        
        service_class, values_field = service_map[module]
        values_data = getattr(request, values_field, None)
        
        if not values_data:
            raise HTTPException(status_code=400, detail=f"{values_field} required")
        
        service = service_class()
        
        if module == "lipid":
            values = values_data.dict(exclude_unset=True)
        else:
            values = values_data
        
        result = service.analyze_values(values)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/file")
async def analyze_file(
    file: UploadFile = File(...),
    module: str = Query("cbc", description="Module to analyze: lipid, cbc, lft, kft, thyroid, diabetes, vitamins, electrolytes"),
    patient_info: Optional[str] = None
):
    """
    Upload and analyze a file.
    
    Supports: PDF, DOCX, TXT, CSV, XLSX, PNG, JPG
    """
    try:
        # Create upload directory
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Extract text from file
        text_content = extract_text_from_file(file_path, file_extension)
        
        # Parse values from text
        values = parse_lab_values(text_content, module)
        
        # Determine which module to use
        service_map = {
            "lipid": LipidService,
            "cbc": CBCService,
            "lft": LFTService,
            "kft": KFTService,
            "thyroid": ThyroidService,
            "diabetes": DiabetesService,
            "vitamins": VitaminsService,
            "electrolytes": ElectrolytesService,
        }
        
        if module not in service_map:
            return {
                'success': False,
                'message': f'Unknown module: {module}',
                'file_info': {
                    'filename': safe_filename,
                    'size': os.path.getsize(file_path),
                    'module': module
                }
            }
        
        if values:
            service = service_map[module]()
            result = service.analyze_values(values)
            result['message'] = f'{module.upper()} analysis completed from file'
            result['file_info'] = {
                'filename': safe_filename,
                'size': os.path.getsize(file_path),
                'module': module
            }
            return result
        else:
            return {
                'success': False,
                'message': f'No {module.upper()} values found in the file. Please use Manual Entry.',
                'file_info': {
                    'filename': safe_filename,
                    'size': os.path.getsize(file_path),
                    'module': module
                },
                'extracted_text_preview': text_content[:500] if text_content else None
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))