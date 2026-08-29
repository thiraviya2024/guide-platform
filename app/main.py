# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.rule_version_service import ensure_schema
from app.api.routes import (
    upload, analyze, report, admin,
    cbc, lft, kft, thyroid, diabetes, vitamins, electrolytes, lipid,
    analytics, auth, disease, doctor, guideline, health, mimic, patient, clinical, care
)

# Import AI router directly
try:
    from app.api.routes.ai import router as ai_router
    AI_ROUTER_AVAILABLE = True
except (ImportError, AttributeError):
    AI_ROUTER_AVAILABLE = False
    ai_router = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LifeSaver - Intelligent Medical AI Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================
# CORS MIDDLEWARE
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# API Prefix
# ============================================================
API_V1_PREFIX = "/api/v1"

# ============================================================
# REGISTER ROUTERS
# ============================================================

# Core Routes
app.include_router(upload.router, prefix=API_V1_PREFIX, tags=["Upload"])
app.include_router(analyze.router, prefix=API_V1_PREFIX, tags=["Analysis"])
app.include_router(report.router, prefix=API_V1_PREFIX, tags=["Report"])
app.include_router(admin.router, prefix=API_V1_PREFIX, tags=["Admin"])

# 8 Clinical Modules
app.include_router(cbc.router, prefix=API_V1_PREFIX, tags=["CBC"])
app.include_router(lft.router, prefix=API_V1_PREFIX, tags=["LFT"])
app.include_router(kft.router, prefix=API_V1_PREFIX, tags=["KFT"])
app.include_router(thyroid.router, prefix=API_V1_PREFIX, tags=["Thyroid"])
app.include_router(diabetes.router, prefix=API_V1_PREFIX, tags=["Diabetes"])
app.include_router(vitamins.router, prefix=API_V1_PREFIX, tags=["Vitamins"])
app.include_router(electrolytes.router, prefix=API_V1_PREFIX, tags=["Electrolytes"])
app.include_router(lipid.router, prefix=API_V1_PREFIX, tags=["Lipid"])

# Advanced Features
app.include_router(analytics.router, prefix=API_V1_PREFIX, tags=["Analytics"])
app.include_router(auth.router, prefix=API_V1_PREFIX, tags=["Auth"])
app.include_router(disease.router, prefix=API_V1_PREFIX, tags=["Disease"])
app.include_router(doctor.router, prefix=API_V1_PREFIX, tags=["Doctor"])
app.include_router(guideline.router, prefix=API_V1_PREFIX, tags=["Guideline"])
app.include_router(health.router, prefix=API_V1_PREFIX, tags=["Health"])
app.include_router(mimic.router, prefix=API_V1_PREFIX, tags=["MIMIC"])
app.include_router(patient.router, prefix=API_V1_PREFIX, tags=["Patient"])
app.include_router(clinical.router, prefix=API_V1_PREFIX)
app.include_router(care.router, prefix=API_V1_PREFIX)

# AI Orchestrator - Direct import
if AI_ROUTER_AVAILABLE and ai_router is not None:
    app.include_router(ai_router, prefix=API_V1_PREFIX, tags=["AI"])
    logger.info("✅ AI Orchestrator router registered")
else:
    logger.warning("⚠️ AI Orchestrator not available")


@app.on_event("startup")
async def startup_event():
    # Additive initialization only; legacy clinical modules remain available
    # even if the optional versioned-rule storage cannot be reached.
    try:
        with SessionLocal() as db:
            ensure_schema(db)
            db.commit()
        logger.info("Versioned clinical-rule schema is ready")
    except Exception as exc:
        logger.warning("Versioned clinical-rule schema is unavailable: %s", exc)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("✅ LifeSaver Medical AI Platform is READY! 🎉")
    logger.info("📊 8 Clinical Modules: Lipid, CBC, LFT, KFT, Thyroid, Diabetes, Vitamins, Electrolytes")
    if AI_ROUTER_AVAILABLE:
        logger.info("🤖 AI Orchestrator: Groq + Gemini (Multi-AI Consensus)")
    logger.info("🏥 Doctor Portal: Dataset Upload & Column Mapping")
    logger.info(f"📡 Total Routes: {len(app.routes)}")
    logger.info("🔓 CORS: All origins allowed (development mode)")


@app.get("/")
async def root():
    endpoints = {
        "upload": ["/api/v1/upload/report"],
        "analysis": ["/api/v1/analyze/manual", "/api/v1/analyze/file"],
        "cbc": ["/api/v1/cbc/analyze", "/api/v1/cbc/analyze-values", "/api/v1/cbc/reference-ranges"],
        "lft": ["/api/v1/lft/analyze", "/api/v1/lft/analyze-values", "/api/v1/lft/reference-ranges"],
        "kft": ["/api/v1/kft/analyze", "/api/v1/kft/analyze-values", "/api/v1/kft/reference-ranges"],
        "thyroid": ["/api/v1/thyroid/analyze", "/api/v1/thyroid/analyze-values", "/api/v1/thyroid/reference-ranges"],
        "diabetes": ["/api/v1/diabetes/analyze", "/api/v1/diabetes/analyze-values", "/api/v1/diabetes/reference-ranges"],
        "vitamins": ["/api/v1/vitamins/analyze", "/api/v1/vitamins/analyze-values", "/api/v1/vitamins/reference-ranges"],
        "electrolytes": ["/api/v1/electrolytes/analyze", "/api/v1/electrolytes/analyze-values", "/api/v1/electrolytes/reference-ranges"],
        "lipid": ["/api/v1/lipid/analyze-values"],
        "report": ["/api/v1/report/generate"],
        "admin": ["/api/v1/admin/rules", "/api/v1/admin/stats", "/api/v1/admin/seed"],
        "analytics": ["/api/v1/analytics/", "/api/v1/analytics/summary"],
        "auth": ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/firebase", "/api/v1/auth/demo-login", "/api/v1/auth/logout"],
        "disease": ["/api/v1/disease/", "/api/v1/disease/{disease_id}"],
        "doctor": [
            "/api/v1/doctor/datasets/upload",
            "/api/v1/doctor/datasets/confirm",
            "/api/v1/doctor/datasets/versions",
            "/api/v1/doctor/datasets/activate/{version_id}",
            "/api/v1/doctor/datasets/categories"
        ],
        "guideline": ["/api/v1/guideline/", "/api/v1/guideline/{guideline_id}"],
        "health": ["/api/v1/health/", "/api/v1/health/metrics"],
        "mimic": ["/api/v1/mimic/", "/api/v1/mimic/{patient_id}"],
        "patient": ["/api/v1/patient/", "/api/v1/patient/{patient_id}"]
    }
    
    if AI_ROUTER_AVAILABLE:
        endpoints["ai"] = [
            "/api/v1/ai/status",
            "/api/v1/ai/analyze",
            "/api/v1/ai/consensus",
            "/api/v1/ai/audit-logs"
        ]
    
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "endpoints": endpoints
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/status")
async def status_check():
    return {"status": "running", "version": settings.APP_VERSION}


@app.get("/api/v1/status")
async def api_status():
    modules = {
        "lipid": "✅ active",
        "cbc": "✅ active",
        "lft": "✅ active",
        "kft": "✅ active",
        "thyroid": "✅ active",
        "diabetes": "✅ active",
        "vitamins": "✅ active",
        "electrolytes": "✅ active",
        "ocr": "✅ active",
        "reporting": "✅ active",
        "analytics": "✅ active",
        "auth": "✅ active",
        "disease": "✅ active",
        "doctor": "✅ active",
        "guideline": "✅ active",
        "health": "✅ active",
        "mimic": "✅ active",
        "patient": "✅ active"
    }
    
    if AI_ROUTER_AVAILABLE:
        modules["ai_orchestrator"] = "✅ active (Groq + Gemini)"
    
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "modules": modules,
        "total_modules": 19 if AI_ROUTER_AVAILABLE else 18,
        "endpoints_count": 66 if AI_ROUTER_AVAILABLE else 62,
        "docs": "/docs",
        "message": "🎉 All modules are complete! System ready for production!"
    }
