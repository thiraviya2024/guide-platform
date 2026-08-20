"""
database/migrate_combination_excel_to_db.py

One-off migration: reads your EXISTING config/combination_rules.xlsx
(Parameter1/Status1/Parameter2/Status2/.../Result/Recommendation columns)
and loads it into the `combination_rules` PostgreSQL table, converting
each row's Parameter/Status pairs into a JSONB conditions array, e.g.:

    Parameter1=LDL, Status1=High, Parameter2=Triglycerides, Status2=High
    -> conditions = [{"parameter": "ldl", "status": "High"},
                      {"parameter": "triglycerides", "status": "High"}]

This JSONB approach (vs. fixed Parameter1/Status1/Parameter2/Status2
columns) is what lets a single database row support ANY number of
conditions -- a 2-parameter or 5-parameter rule is just a longer JSON
array, no schema change needed.

Run once, after applying database/schema.sql:

    python -m database.migrate_combination_excel_to_db

Safe to re-run: it truncates combination_rules before re-inserting, so
re-running after fixing the Excel file just re-syncs it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from database.connection import SessionLocal
from utils.logger import logger

CONFIG_DIR = Path("config")
EXCEL_FILE = "combination_rules.xlsx"

PARAM_COL_PATTERN = re.compile(r"^Parameter(\d+)$")
STATUS_COL_PATTERN = re.compile(r"^Status(\d+)$")


def _normalize_parameter(name: str) -> str:
    """Match the same normalization rule_engine.py uses, e.g. 'LDL' ->
    'ldl', 'Total Cholesterol' -> 'total_cholesterol'."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _detect_pair_columns(df: pd.DataFrame) -> int:
    param_indices = set()
    status_indices = set()
    for col in df.columns:
        m = PARAM_COL_PATTERN.match(str(col))
        if m:
            param_indices.add(int(m.group(1)))
        m = STATUS_COL_PATTERN.match(str(col))
        if m:
            status_indices.add(int(m.group(1)))
    valid_pairs = sorted(param_indices & status_indices)
    if not valid_pairs:
        raise ValueError(
            "combination_rules.xlsx has no matching Parameter*/Status* column pairs."
        )
    return max(valid_pairs)


def migrate() -> int:
    file_path = CONFIG_DIR / EXCEL_FILE
    if not file_path.exists():
        logger.warning(f"migrate_combination_excel_to_db: '{file_path}' not found, skipping")
        return 0

    df = pd.read_excel(file_path, engine="openpyxl")
    required = {"Result", "Recommendation"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"'{file_path}' is missing columns: {sorted(missing)}")

    pair_count = _detect_pair_columns(df)

    rows_to_insert = []
    for _, row in df.iterrows():
        conditions = []
        for i in range(1, pair_count + 1):
            param_col = f"Parameter{i}"
            status_col = f"Status{i}"
            if param_col not in row or status_col not in row:
                continue
            param_value = row[param_col]
            status_value = row[status_col]
            if pd.isna(param_value) or pd.isna(status_value):
                continue
            param_str = str(param_value).strip()
            status_str = str(status_value).strip()
            if not param_str or not status_str:
                continue
            conditions.append(
                {"parameter": _normalize_parameter(param_str), "status": status_str}
            )

        if not conditions:
            logger.warning(f"migrate_combination_excel_to_db: skipping row with no usable conditions: {row.to_dict()}")
            continue

        rows_to_insert.append(
            {
                "conditions": json.dumps(conditions),
                "result": str(row["Result"]).strip(),
                "recommendation": str(row["Recommendation"]).strip(),
            }
        )

    with SessionLocal() as db:
        db.execute(text("DELETE FROM combination_rules"))
        for r in rows_to_insert:
            db.execute(
                text(
                    """
                    INSERT INTO combination_rules (conditions, result, recommendation)
                    VALUES (:conditions, :result, :recommendation)
                    """
                ),
                {
                    "conditions": r["conditions"],
                    "result": r["result"],
                    "recommendation": r["recommendation"],
                },
            )
        db.commit()

    logger.info(
        f"migrate_combination_excel_to_db: migrated {len(rows_to_insert)} rows "
        f"from '{file_path}' into combination_rules"
    )
    return len(rows_to_insert)


if __name__ == "__main__":
    migrate()