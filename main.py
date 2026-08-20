# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api.routes import upload, analyze, report, admin, blood_test

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LipidAI API - Intelligent Lipid Profile & Blood Test Analysis",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================
# CORS middleware - Allows frontend to communicate with backend
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(report.router)
app.include_router(admin.router)
app.include_router(blood_test.router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("✅ LipidAI API with Blood Test Analysis is ready!")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "/upload/report",
            "/analyze/manual",
            "/blood-test/analyze",
            "/report/generate",
            "/admin/rules",
            "/admin/stats"
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
