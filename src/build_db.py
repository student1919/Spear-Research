"""Load the generated JSONL files into a SQLite database.

One table per record type (Profiles.md), linked by profile_id / org_id. Columns are
taken from the dataclasses in schema.py, so the DB always matches the written records.
List and dict fields are stored as JSON text so the files remain the source of truth
and the DB stays queryable.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import fields
from pathlib import Path

from .schema import (FILES, AttackEmail, Org, ProfileBehavior, ProfileCore, ProfilePrivate, ProfilePublic,
                     read_jsonl)

TABLES = {
    "orgs": ("org_id", Org),
    "core": ("profile_id", ProfileCore),
    "public": ("profile_id", ProfilePublic),
    "private": ("profile_id", ProfilePrivate),
    "behavior": ("profile_id", ProfileBehavior),
    "emails_attack": ("email_id", AttackEmail),
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
        for table, (pk, cls) in TABLES.items():
            rows = read_jsonl(data_dir / FILES[table])
            cols = [f.name for f in fields(cls) if f.name != pk]
            col_defs = ", ".join([f'"{pk}" TEXT PRIMARY KEY'] + [f'"{c}"' for c in cols])
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
