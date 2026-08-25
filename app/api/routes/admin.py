"""Administrator rule-management endpoints."""
from datetime import date
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.rule_version_service import activate_version, ensure_schema, import_rules_excel

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> str:
    """Require a configured shared admin token until the app has role-based auth."""
    expected = os.getenv("ADMIN_RULES_TOKEN")
    if not expected:
        raise HTTPException(503, "ADMIN_RULES_TOKEN must be configured for rule administration")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "Administrator access required")
    return "admin-token"


class RuleUpdate(BaseModel):
    min_value: float
    max_value: float
    status: str
    recommendation: Optional[str] = None


@router.get("/rules")
async def get_rules(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    """Return active versioned rules, falling back to the legacy lipid list."""
    try:
        ensure_schema(db)
        versioned = db.execute(text("""SELECT r.*, v.rule_version, v.effective_from, v.effective_to, v.status AS version_status
            FROM clinical_reference_rules r JOIN clinical_rule_versions v ON v.id=r.version_id
            WHERE v.status='active' AND v.effective_from<=CURRENT_DATE AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE)
            ORDER BY r.category, r.parameter, r.min_value""")).mappings().all()
        if versioned:
            return {"rules": [dict(row) for row in versioned]}
        legacy = db.execute(text("SELECT * FROM lipid_rules WHERE is_active=TRUE ORDER BY parameter, min_value")).mappings().all()
        return {"rules": [dict(row) for row in legacy]}
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Unable to retrieve rules") from exc


@router.post("/rules/import", status_code=201)
async def import_rules(
    file: UploadFile = File(...), rule_version: str = Form(...), effective_from: date = Form(...),
    db: Session = Depends(get_db), actor: str = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Rules must be supplied as an Excel .xlsx or .xls file")
    try:
        version_id = import_rules_excel(db, await file.read(), rule_version, effective_from, actor)
        status = "active" if effective_from <= date.today() else "inactive"
        return {"success": True, "version_id": version_id, "rule_version": rule_version, "status": status}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Rule import failed; active rules were not changed") from exc


@router.get("/rules/versions")
async def get_rule_versions(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    try:
        ensure_schema(db)
        versions = db.execute(text("""SELECT v.*, COUNT(r.id) AS rule_count FROM clinical_rule_versions v
            LEFT JOIN clinical_reference_rules r ON r.version_id=v.id GROUP BY v.id ORDER BY v.effective_from DESC, v.id DESC""")).mappings().all()
        return {"versions": [dict(row) for row in versions]}
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Unable to retrieve rule versions") from exc


@router.post("/rules/versions/{version}/activate")
async def activate_rule_version(version: str, db: Session = Depends(get_db), actor: str = Depends(require_admin)):
    try:
        activate_version(db, version, actor)
        return {"success": True, "rule_version": version, "status": "active"}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "Unable to activate rule version") from exc


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, rule: RuleUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    """Retained legacy endpoint; versioned changes should use Excel import instead."""
    if rule.min_value > rule.max_value:
        raise HTTPException(400, "min_value must be <= max_value")
    try:
        db.execute(text("""UPDATE lipid_rules SET min_value=:min_val, max_value=:max_val, status=:status,
            recommendation=:rec WHERE id=:id"""), {"min_val": rule.min_value, "max_val": rule.max_value, "status": rule.status, "rec": rule.recommendation, "id": rule_id})
        db.commit()
        return {"success": True, "message": f"Rule {rule_id} updated"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    tables = ["lipid_rules", "combination_rules", "food_rules", "exercise_rules", "mimic_mapping"]
    stats = {}
    for table in tables:
        try:
            stats[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        except Exception:
            stats[table] = 0
    return stats
