from contextlib import contextmanager
import sqlite3

from .config import DATA


@contextmanager
def db(write=False):
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA / "cases.sqlite", timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA secure_delete=ON")
        if write:
            conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, state TEXT NOT NULL,
            created TEXT NOT NULL, progress TEXT NOT NULL DEFAULT '[]',
            result TEXT, decision TEXT
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            name TEXT NOT NULL, mime TEXT NOT NULL, sha256 TEXT NOT NULL, original BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit (
            seq INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            previous TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS audit_case ON audit(case_id,seq);
        CREATE INDEX IF NOT EXISTS document_case ON documents(case_id);
        """)
        conn.execute("UPDATE cases SET state='failed' WHERE state='processing'")
