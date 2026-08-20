from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


class RuleUpdate(BaseModel):
    min_value: float
    max_value: float
    status: str
    recommendation: Optional[str] = None


@router.get("/rules")
async def get_rules(db: Session = Depends(get_db)):
    from sqlalchemy import text
    result = db.execute(text("SELECT * FROM lipid_rules WHERE is_active = TRUE ORDER BY parameter, min_value"))
    return {"rules": [dict(row) for row in result]}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, rule: RuleUpdate, db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        db.execute(
            text("""
                UPDATE lipid_rules 
                SET min_value = :min_val, max_value = :max_val, 
                    status = :status, recommendation = :rec
                WHERE id = :id
            """),
            {
                "min_val": rule.min_value,
                "max_val": rule.max_value,
                "status": rule.status,
                "rec": rule.recommendation,
                "id": rule_id
            }
        )
        db.commit()
        return {"success": True, "message": f"Rule {rule_id} updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    from sqlalchemy import text
    tables = ['lipid_rules', 'combination_rules', 'food_rules', 'exercise_rules', 'mimic_mapping']
    stats = {}
    for table in tables:
        try:
            stats[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        except:
            stats[table] = 0
    return stats