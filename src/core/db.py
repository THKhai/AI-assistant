import uuid
from datetime import datetime
from typing import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from src.core import config
from src.core.models import (
    Conversation, KnowledgeDoc, Plan,
    RefreshToken, RevokedToken, Task, TotpSecret, User,
)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{config.SQLITE_PATH}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _set_wal(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    return _engine


def get_session() -> Generator[Session, None, None]:
    """FastAPI Depends: yields a Session for Unit-of-Work batching in route handlers."""
    with Session(get_engine()) as s:
        yield s


def _to_dict(obj) -> dict:
    """Convert a SQLModel instance to a plain dict (datetimes as ISO strings)."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.key)
        if isinstance(val, datetime):
            val = val.isoformat()
        result[col.key] = val
    return result


def new_session_id() -> str:
    return str(uuid.uuid4())


def init_db():
    import threading
    from src.core.migrate import run
    from src.core.logger import get_logger
    from src.core import services  # local import — avoids circular at module load time

    run()
    SQLModel.metadata.create_all(get_engine())
    services.tokens.cleanup_revoked()
    services.tokens.cleanup_refresh()

    log = get_logger("db")

    def _cleanup_loop():
        import time
        while True:
            time.sleep(6 * 3600)
            try:
                services.tokens.cleanup_revoked()
                services.tokens.cleanup_refresh()
                log.debug("periodic token cleanup complete")
            except Exception as exc:
                log.error(f"periodic token cleanup failed: {exc}")

    threading.Thread(target=_cleanup_loop, daemon=True, name="token-cleanup").start()
