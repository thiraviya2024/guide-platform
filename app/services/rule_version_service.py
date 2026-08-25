"""Additive versioned rules layered over legacy module rule tables."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from math import isfinite
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

MODULE_TABLES = {"cbc": "cbc_rules", "lft": "lft_rules", "kft": "kft_rules", "thyroid": "thyroid_rules", "diabetes": "diabetes_rules", "vitamins": "vitamins_rules", "electrolytes": "electrolytes_rules", "lipid": "lipid_rules"}
REQUIRED_COLUMNS = {"category", "parameter", "min_value", "max_value", "clinical_status", "recommendation"}
_DDL = """
CREATE TABLE IF NOT EXISTS clinical_rule_versions (id BIGSERIAL PRIMARY KEY, rule_version VARCHAR(100) NOT NULL UNIQUE, effective_from DATE NOT NULL, effective_to DATE NULL, status VARCHAR(20) NOT NULL DEFAULT 'inactive' CHECK (status IN ('active', 'inactive', 'archived')), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_by VARCHAR(255));
CREATE TABLE IF NOT EXISTS clinical_reference_rules (id BIGSERIAL PRIMARY KEY, version_id BIGINT NOT NULL REFERENCES clinical_rule_versions(id), category VARCHAR(50) NOT NULL, parameter VARCHAR(100) NOT NULL, min_value DOUBLE PRECISION NOT NULL, max_value DOUBLE PRECISION NOT NULL, level VARCHAR(100), clinical_status VARCHAR(100) NOT NULL, recommendation TEXT, population VARCHAR(100), sex VARCHAR(30), min_age INTEGER, max_age INTEGER, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), CHECK (min_value <= max_value), CHECK (min_age IS NULL OR max_age IS NULL OR min_age <= max_age));
CREATE TABLE IF NOT EXISTS clinical_rule_audit_log (id BIGSERIAL PRIMARY KEY, version_id BIGINT REFERENCES clinical_rule_versions(id), action VARCHAR(50) NOT NULL, actor VARCHAR(255), details TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX IF NOT EXISTS ix_clinical_reference_rules_lookup ON clinical_reference_rules(category, parameter, min_value, max_value);
"""


def ensure_schema(db: Session) -> None:
    for statement in _DDL.split(";"):
        if statement.strip():
            db.execute(text(statement))


def lookup_active_rule(db: Session, category: str, parameter: str, value: float, *, population: str | None = None, sex: str | None = None, age: int | None = None) -> Any | None:
    """Return an active applicable rule, or None to preserve legacy fallback."""
    try:
        return db.execute(text("""SELECT r.clinical_status AS status, r.recommendation, r.level
            FROM clinical_reference_rules r JOIN clinical_rule_versions v ON v.id=r.version_id
            WHERE lower(r.category)=lower(:category) AND lower(r.parameter)=lower(:parameter)
              AND r.min_value<=:value AND r.max_value>=:value AND v.status='active'
              AND v.effective_from<=CURRENT_DATE AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE)
              AND (r.population IS NULL OR r.population=:population)
              AND (r.sex IS NULL OR lower(r.sex)=lower(:sex))
              AND (r.min_age IS NULL OR :age IS NULL OR r.min_age<=:age)
              AND (r.max_age IS NULL OR :age IS NULL OR r.max_age>=:age)
            ORDER BY v.effective_from DESC, r.id LIMIT 1"""), {"category": category, "parameter": parameter, "value": value, "population": population, "sex": sex, "age": age}).fetchone()
    except Exception:
        # PostgreSQL marks a transaction failed after a missing-table/query
        # error.  Clear it before the engine performs its legacy lookup.
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _validate_rows(rows: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str, str | None, str | None], list[dict[str, Any]]] = {}
    for number, row in enumerate(rows, 2):
        category, parameter = str(row.get("category", "")).strip().lower(), str(row.get("parameter", "")).strip().lower()
        if category not in MODULE_TABLES:
            raise ValueError(f"Row {number}: unsupported category '{row.get('category')}'")
        if not parameter:
            raise ValueError(f"Row {number}: parameter is required")
        try:
            minimum, maximum = float(row["min_value"]), float(row["max_value"])
        except (TypeError, ValueError):
            raise ValueError(f"Row {number}: min_value and max_value must be numeric") from None
        if not isfinite(minimum) or not isfinite(maximum) or minimum > maximum:
            raise ValueError(f"Row {number}: invalid numeric range")
        if not str(row.get("clinical_status", "")).strip() or row.get("recommendation") is None or not str(row["recommendation"]).strip():
            raise ValueError(f"Row {number}: clinical_status and recommendation are required")
        for key in ("min_age", "max_age"):
            if row.get(key) is not None:
                try:
                    row[key] = int(row[key])
                    if row[key] < 0: raise ValueError
                except (TypeError, ValueError):
                    raise ValueError(f"Row {number}: {key} must be a non-negative integer") from None
        if row.get("min_age") is not None and row.get("max_age") is not None and row["min_age"] > row["max_age"]:
            raise ValueError(f"Row {number}: min_age must be <= max_age")
        row["category"], row["parameter"] = category, parameter
        groups.setdefault((category, parameter, row.get("population"), row.get("sex")), []).append(row)
    for rules in groups.values():
        rules.sort(key=lambda r: float(r["min_value"]))
        if any(float(right["min_value"]) <= float(left["max_value"]) for left, right in zip(rules, rules[1:])):
            raise ValueError("Overlapping ranges in imported rules")


def _validate_supported_parameters(db: Session, rows: list[dict[str, Any]]) -> None:
    for category, parameter in {(r["category"], r["parameter"]) for r in rows}:
        table = MODULE_TABLES[category]
        try:
            exists = db.execute(text(f"SELECT 1 FROM {table} WHERE lower(parameter)=:parameter LIMIT 1"), {"parameter": parameter}).scalar()
        except Exception as exc:
            raise ValueError(f"Could not validate parameters for category '{category}'") from exc
        if not exists:
            raise ValueError(f"Unsupported parameter '{parameter}' for category '{category}'")


def import_rules_excel(db: Session, content: bytes, rule_version: str, effective_from: date, created_by: str | None = None) -> int:
    if not rule_version or not rule_version.strip():
        raise ValueError("rule_version is required")
    try:
        frame = pd.read_excel(BytesIO(content))
        frame.columns = [str(column).strip().lower() for column in frame.columns]
    except Exception as exc:
        raise ValueError("Unable to read the Excel workbook") from exc
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing: raise ValueError(f"Missing required rule columns: {', '.join(sorted(missing))}")
    if frame.empty: raise ValueError("The workbook contains no rules")
    rows = frame.where(pd.notna(frame), None).to_dict("records")
    _validate_rows(rows)
    try:
        ensure_schema(db)
        _validate_supported_parameters(db, rows)
        existing = db.execute(text("SELECT 1 FROM clinical_rule_versions WHERE rule_version=:version"), {"version": rule_version.strip()}).scalar()
        if existing:
            raise ValueError(f"Rule version '{rule_version.strip()}' already exists")
        version_id = db.execute(text("INSERT INTO clinical_rule_versions(rule_version,effective_from,status,created_by) VALUES(:version,:effective,'inactive',:actor) RETURNING id"), {"version": rule_version.strip(), "effective": effective_from, "actor": created_by}).scalar_one()
        insert = text("""INSERT INTO clinical_reference_rules(version_id,category,parameter,min_value,max_value,level,clinical_status,recommendation,population,sex,min_age,max_age) VALUES(:version_id,:category,:parameter,:min_value,:max_value,:level,:clinical_status,:recommendation,:population,:sex,:min_age,:max_age)""")
        for row in rows:
            db.execute(insert, {"version_id": version_id, **{key: row.get(key) for key in ("category", "parameter", "min_value", "max_value", "level", "clinical_status", "recommendation", "population", "sex", "min_age", "max_age")}})
        if effective_from <= date.today():
            db.execute(text("UPDATE clinical_rule_versions SET status='archived', effective_to=CURRENT_DATE, updated_at=NOW() WHERE status='active'"))
            db.execute(text("UPDATE clinical_rule_versions SET status='active', effective_to=NULL, updated_at=NOW() WHERE id=:id"), {"id": version_id})
            action = "imported_and_activated"
        else:
            # Do not make a future guideline displace the currently applicable
            # version before its effective date.
            action = "imported_pending_effective_date"
        db.execute(text("INSERT INTO clinical_rule_audit_log(version_id,action,actor,details) VALUES(:id,:action,:actor,:details)"), {"id": version_id, "action": action, "actor": created_by, "details": f"Imported {len(rows)} rules"})
        db.commit()
        return version_id
    except Exception:
        db.rollback()
        raise


def activate_version(db: Session, rule_version: str, actor: str | None = None) -> None:
    try:
        ensure_schema(db)
        version = db.execute(text("SELECT id, effective_from FROM clinical_rule_versions WHERE rule_version=:version"), {"version": rule_version}).mappings().fetchone()
        if not version:
            raise ValueError("Rule version not found")
        if version["effective_from"] > date.today():
            raise ValueError("Rule version cannot be activated before its effective_from date")
        version_id = version["id"]
        db.execute(text("UPDATE clinical_rule_versions SET status='archived', effective_to=CURRENT_DATE, updated_at=NOW() WHERE status='active'"))
        db.execute(text("UPDATE clinical_rule_versions SET status='active', effective_to=NULL, updated_at=NOW() WHERE id=:id"), {"id": version_id})
        db.execute(text("INSERT INTO clinical_rule_audit_log(version_id,action,actor) VALUES(:id,'activated',:actor)"), {"id": version_id, "actor": actor})
        db.commit()
    except Exception:
        db.rollback()
        raise
