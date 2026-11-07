"""Load the generated JSONL files into a SQLite database.

One table per record type (Profiles.md), linked by profile_id / org_id. List and
dict fields are stored as JSON text so the files remain the source of truth and
the DB stays queryable.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schema import FILES, read_jsonl

TABLES = {
    "orgs": ("org_id", ["name", "domain", "industry", "size", "headcount",
                        "hq_city", "founded", "org_chart", "synthetic"]),
    "core": ("profile_id", ["org_id", "full_name", "email", "industry",
                            "career_stage", "target_role", "title", "location"]),
    "public": ("profile_id", ["resume_bullets", "social_presence",
                             "footprint_level", "posts", "personal_website"]),
    "private": ("profile_id", ["projects", "colleagues", "real_details",
                              "sensitive_access"]),
    "behavior": ("profile_id", ["traits", "security_awareness",
                               "response_tendencies", "busy_level"]),
    "emails_attack": ("email_id", ["profile_id", "org_id", "scenario", "pretext",
                                   "impersonated_role", "sender_display",
                                   "sender_address", "subject", "body",
                                   "call_to_action", "urgency",
                                   "personalization_fields", "generator",
                                   "synthetic"]),
}


def _cell(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v


def build(data_dir: str | Path, db_path: str | Path) -> dict[str, int]:
    data_dir, db_path = Path(data_dir), Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    counts: dict[str, int] = {}
    try:
        for table, (pk, cols) in TABLES.items():
            rows = read_jsonl(data_dir / FILES[table])
            col_defs = ", ".join([f'"{pk}" TEXT PRIMARY KEY'] + [f'"{c}" TEXT' for c in cols])
            con.execute(f'CREATE TABLE "{table}" ({col_defs})')
            allcols = [pk] + cols
            con.executemany(
                f'INSERT INTO "{table}" ({", ".join(allcols)}) '
                f'VALUES ({", ".join("?" * len(allcols))})',
                [[_cell(r.get(c)) for c in allcols] for r in rows],
            )
            counts[table] = len(rows)
        con.commit()
    finally:
        con.close()
    return counts
