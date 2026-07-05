from cachetools import TTLCache
from datetime import datetime, timedelta
from threading import Lock

from sqlmodel import Session, select

from src.core import config
from src.core.db import get_engine, _to_dict
from src.core.models import User

_cache: TTLCache = TTLCache(maxsize=128, ttl=300)
_lock = Lock()

_SAFE_FIELDS = {"id", "username", "role", "deleted", "created_at"}


class UserService:
    """User CRUD with integrated TTL cache. Stateless — safe to use as a singleton."""

    def _invalidate(self, username: str):
        with _lock:
            _cache.pop(username, None)

    def get(self, username: str) -> dict | None:
        with _lock:
            if username in _cache:
                return _cache[username]
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
        result = _to_dict(row) if row else None
        with _lock:
            _cache[username] = result
        return result

    def create(self, username: str, password_hash: str, role: str = "member") -> int:
        with Session(get_engine()) as s:
            row = User(username=username, password_hash=password_hash, role=role)
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id

    def list_all(self) -> list[dict]:
        with Session(get_engine()) as s:
            rows = s.exec(select(User).order_by(User.id)).all()
        return [{k: v for k, v in _to_dict(r).items() if k in _SAFE_FIELDS} for r in rows]

    def update_role(self, username: str, role: str):
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
            if row:
                row.role = role
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()
        self._invalidate(username)

    def update_password(self, username: str, password_hash: str):
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
            if row:
                row.password_hash = password_hash
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()
        self._invalidate(username)

    def soft_delete(self, username: str):
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
            if row:
                row.deleted = 1
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()
        self._invalidate(username)

    def restore(self, username: str):
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
            if row:
                row.deleted = 0
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()
        self._invalidate(username)

    def is_active(self, username: str) -> bool:
        row = self.get(username)
        return row is not None and row["deleted"] == 0

    def is_locked(self, username: str) -> bool:
        user = self.get(username)
        if not user or not user.get("locked_until"):
            return False
        expiry = datetime.fromisoformat(user["locked_until"])
        return datetime.utcnow() < expiry

    def increment_failed_login(self, username: str):
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
            if row:
                row.failed_login_count = (row.failed_login_count or 0) + 1
                if row.failed_login_count >= config.LOGIN_MAX_ATTEMPTS:
                    row.locked_until = datetime.utcnow() + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()
        self._invalidate(username)

    def reset_failed_login(self, username: str):
        with Session(get_engine()) as s:
            row = s.exec(select(User).where(User.username == username)).first()
            if row:
                row.failed_login_count = 0
                row.locked_until = None
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()
        self._invalidate(username)

    def cache_stats(self) -> dict:
        with _lock:
            return {"size": len(_cache), "maxsize": _cache.maxsize, "ttl_seconds": _cache.ttl}

    def cache_entries(self, mask: set[str] = None) -> dict:
        with _lock:
            entries = dict(_cache)
        if mask:
            return {
                k: {f: v for f, v in e.items() if f not in mask} if e else None
                for k, e in entries.items()
            }
        return entries
