# app/services/analysis_service.py
"""
Analysis Service Factory
"""

from typing import Optional
from app.services.lipid_service import LipidService
from app.services.cbc_service import CBCService
from app.services.lft_service import LFTService
from app.services.kft_service import KFTService
from app.services.thyroid_service import ThyroidService
from app.services.diabetes_service import DiabetesService
from app.services.vitamins_service import VitaminsService
from app.services.electrolytes_service import ElectrolytesService


def get_analysis_service(module: str):
    """Get analysis service for a specific module."""
    services = {
        'lipid': LipidService,
        'cbc': CBCService,
        'lft': LFTService,
        'kft': KFTService,
        'thyroid': ThyroidService,
        'diabetes': DiabetesService,
        'vitamins': VitaminsService,
        'electrolytes': ElectrolytesService,
    }
    
    service_class = services.get(module.lower())
    if service_class:
        return service_class()
    return None