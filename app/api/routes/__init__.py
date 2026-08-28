# app/api/routes/__init__.py
"""
API Routes Package
"""

from . import upload
from . import analyze
from . import report
from . import admin
from . import cbc
from . import lft
from . import kft
from . import thyroid
from . import diabetes
from . import vitamins
from . import electrolytes
from . import analytics
from . import auth
from . import disease
from . import doctor
from . import guideline
from . import health
from . import mimic
from . import patient
from . import clinical
from . import care

# Conditional import for AI to avoid circular import
try:
    from . import ai
except ImportError:
    ai = None

__all__ = [
    'upload',
    'analyze',
    'report',
    'admin',
    'cbc',
    'lft',
    'kft',
    'thyroid',
    'diabetes',
    'vitamins',
    'electrolytes',
    'analytics',
    'auth',
    'disease',
    'doctor',
    'guideline',
    'health',
    'mimic',
    'patient',
    'clinical',
    'care',
    'ai'
]
