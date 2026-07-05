import sqlite3
from pathlib import Path

from src.core import config
from src.core.logger import get_logger

log = get_logger("migrate")

MIGRATIONS_DIR = Path(config.BASE_DIR) / "data" / "migrations"


def run() -> int:
    """Apply all pending .sql files in data/migrations/ in filename order. Returns count applied."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    Path(config.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id         INTEGER  PRIMARY KEY AUTOINCREMENT,
            filename   TEXT     UNIQUE NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    applied = {row[0] for row in conn.execute("SELECT filename FROM _migrations").fetchall()}
    pending = sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.name not in applied)

    for path in pending:
        sql = path.read_text(encoding="utf-8")
        try:
            conn.executescript(sql)
            conn.execute("INSERT INTO _migrations (filename) VALUES (?)", (path.name,))
            conn.commit()
            log.info(f"applied {path.name}")
        except Exception as e:
            conn.rollback()
            log.error(f"failed {path.name}: {e}")
            raise

    conn.close()
    return len(pending)
