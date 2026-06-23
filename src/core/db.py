import sqlite3
import json
import uuid
from contextlib import contextmanager
from datetime import datetime
from src.core import config


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS plans (
                id          INTEGER  PRIMARY KEY AUTOINCREMENT,
                module      TEXT     NOT NULL,
                level       TEXT,
                period      TEXT,
                content     TEXT     NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted     INTEGER  DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER  PRIMARY KEY AUTOINCREMENT,
                plan_id     INTEGER  REFERENCES plans(id),
                module      TEXT     NOT NULL,
                description TEXT     NOT NULL,
                status      TEXT     DEFAULT 'pending',
                due_date    TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted     INTEGER  DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id           INTEGER  PRIMARY KEY AUTOINCREMENT,
                module       TEXT     NOT NULL,
                session_type TEXT,
                session_id   TEXT     NOT NULL,
                turn         INTEGER  NOT NULL,
                role         TEXT     NOT NULL,
                content      TEXT     NOT NULL,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted      INTEGER  DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id          INTEGER  PRIMARY KEY AUTOINCREMENT,
                module      TEXT     NOT NULL,
                doc_id      TEXT     UNIQUE NOT NULL,
                filepath    TEXT     NOT NULL,
                title       TEXT,
                tags        TEXT,
                indexed_at  DATETIME,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted     INTEGER  DEFAULT 0
            );
        """)


def new_session_id() -> str:
    return str(uuid.uuid4())


def save_turn(session_id: str, module: str, session_type: str, turn: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (module, session_type, session_id, turn, role, content) VALUES (?,?,?,?,?,?)",
            (module, session_type, session_id, turn, role, content),
        )


def get_recent_turns(session_id: str, limit: int = None) -> list[dict]:
    limit = limit or config.CONVERSATION_HISTORY_TURNS * 2
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id=? AND deleted=0 ORDER BY turn LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def save_plan(module: str, level: str, period: str, content: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO plans (module, level, period, content) VALUES (?,?,?,?)",
            (module, level, period, json.dumps(content)),
        )
        return cur.lastrowid


def get_plan(module: str, level: str, period: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM plans WHERE module=? AND level=? AND period=? AND deleted=0 ORDER BY id DESC LIMIT 1",
            (module, level, period),
        ).fetchone()
    if not row:
        return None
    return {**dict(row), "content": json.loads(row["content"])}


def save_tasks(plan_id: int, module: str, tasks: list[str], due_date: str = None):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO tasks (plan_id, module, description, due_date) VALUES (?,?,?,?)",
            [(plan_id, module, t, due_date) for t in tasks],
        )


def get_tasks(plan_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE plan_id=? AND deleted=0 ORDER BY id",
            (plan_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_task_status(task_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, task_id),
        )


def soft_delete(table: str, row_id: int):
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET deleted=1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (row_id,),
        )


def hard_delete(table: str, row_id: int):
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))


def upsert_knowledge_doc(module: str, doc_id: str, filepath: str, title: str, tags: list[str]):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO knowledge_docs (module, doc_id, filepath, title, tags, indexed_at)
               VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(doc_id) DO UPDATE SET
                   indexed_at=CURRENT_TIMESTAMP,
                   updated_at=CURRENT_TIMESTAMP,
                   deleted=0""",
            (module, doc_id, filepath, title, json.dumps(tags)),
        )


def is_doc_indexed(doc_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM knowledge_docs WHERE doc_id=? AND deleted=0", (doc_id,)
        ).fetchone()
    return row is not None
