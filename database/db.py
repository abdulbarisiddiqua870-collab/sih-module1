"""
SQLite persistence for inspection history.

Every normalized inspection is stored as one row: the key summary
columns used for fast search/sort/filter, plus the complete
normalized JSON so the full result can be redisplayed or re-rendered
into a PDF later without recomputation.
"""

import json
import sqlite3
from contextlib import contextmanager

import config


class DatabaseError(Exception):
    pass


@contextmanager
def _connect():
    conn = None
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database error: {exc}")
    finally:
        if conn:
            conn.close()


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inspections (
                inspection_id  TEXT PRIMARY KEY,
                timestamp      TEXT NOT NULL,
                product_name   TEXT,
                score          INTEGER,
                status         TEXT,
                finding_count  INTEGER,
                is_demo        INTEGER DEFAULT 0,
                raw_json       TEXT NOT NULL
            )
            """
        )


def insert_inspection(normalized: dict, is_demo: bool = False):
    """Insert or replace one normalized inspection record."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO inspections
                (inspection_id, timestamp, product_name, score, status,
                 finding_count, is_demo, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(inspection_id) DO UPDATE SET
                timestamp=excluded.timestamp,
                product_name=excluded.product_name,
                score=excluded.score,
                status=excluded.status,
                finding_count=excluded.finding_count,
                raw_json=excluded.raw_json
            """,
            (
                normalized["inspection_id"],
                normalized["timestamp"],
                normalized["product"].get("name"),
                normalized["assessment"].get("score"),
                normalized["assessment"].get("status"),
                normalized.get("finding_count", 0),
                1 if is_demo else 0,
                json.dumps(normalized),
            ),
        )


def get_all_inspections():
    """Return every inspection's normalized dict, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT raw_json FROM inspections ORDER BY timestamp DESC"
        ).fetchall()
    return [json.loads(r["raw_json"]) for r in rows]


def get_inspection(inspection_id: str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT raw_json FROM inspections WHERE inspection_id = ?",
            (inspection_id,),
        ).fetchone()
    return json.loads(row["raw_json"]) if row else None


def count_inspections() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM inspections").fetchone()
    return row["c"] if row else 0


def has_demo_data() -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM inspections WHERE is_demo = 1"
        ).fetchone()
    return bool(row and row["c"] > 0)


def seed_if_empty():
    """Populate the database with labeled demo records on first run."""
    from mock.mock_data import get_all_seed_samples
    from services.normalizer import normalize_inspection

    if count_inspections() > 0:
        return
    for raw in get_all_seed_samples():
        normalized = normalize_inspection(raw)
        insert_inspection(normalized, is_demo=True)
