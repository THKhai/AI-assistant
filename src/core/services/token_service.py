from cachetools import TTLCache
from datetime import datetime
from threading import Lock

from sqlalchemy import delete as sa_delete, update as sa_update
from sqlmodel import Session, select

from src.core.db import get_engine, _to_dict
from src.core.models import RefreshToken, RevokedToken, TotpSecret

_token_cache: TTLCache = TTLCache(maxsize=2048, ttl=60)
_token_lock = Lock()


class TokenService:
    """JWT revocation and refresh token management with TTL cache. Stateless singleton."""

    def revoke(self, jti: str, expires_at: datetime):
        with Session(get_engine()) as s:
            if not s.exec(select(RevokedToken).where(RevokedToken.jti == jti)).first():
                s.add(RevokedToken(jti=jti, expires_at=expires_at))
                s.commit()
        with _token_lock:
            _token_cache[jti] = True

    def is_revoked(self, jti: str) -> bool:
        with _token_lock:
            if jti in _token_cache:
                return _token_cache[jti]
        with Session(get_engine()) as s:
            result = s.exec(select(RevokedToken).where(RevokedToken.jti == jti)).first() is not None
        with _token_lock:
            _token_cache[jti] = result
        return result

    def cleanup_revoked(self):
        with Session(get_engine()) as s:
            s.execute(sa_delete(RevokedToken).where(RevokedToken.expires_at < datetime.utcnow()))
            s.commit()

    def create_refresh(self, username: str, token_hash: str, expires_at: datetime):
        with Session(get_engine()) as s:
            s.add(RefreshToken(username=username, token_hash=token_hash, expires_at=expires_at))
            s.commit()

    def get_refresh(self, token_hash: str) -> dict | None:
        with Session(get_engine()) as s:
            row = s.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
        return _to_dict(row) if row else None

    def revoke_refresh(self, token_hash: str):
        with Session(get_engine()) as s:
            row = s.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
            if row:
                row.revoked = 1
                s.add(row)
                s.commit()

    def revoke_all_user_refresh(self, username: str):
        with Session(get_engine()) as s:
            s.execute(
                sa_update(RefreshToken)
                .where(RefreshToken.username == username)
                .values(revoked=1)
            )
            s.commit()

    def cleanup_refresh(self):
        with Session(get_engine()) as s:
            s.execute(sa_delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow()))
            s.commit()

    def cache_stats(self) -> dict:
        with _token_lock:
            return {"size": len(_token_cache), "maxsize": _token_cache.maxsize, "ttl_seconds": _token_cache.ttl}

    def cache_entries(self) -> dict:
        with _token_lock:
            return dict(_token_cache)


class TotpService:
    """TOTP secret storage — thin wrapper over the totp_secrets table."""

    def get(self, username: str) -> dict | None:
        with Session(get_engine()) as s:
            row = s.exec(select(TotpSecret).where(TotpSecret.username == username)).first()
        return _to_dict(row) if row else None

    def set(self, username: str, secret: str, enabled: bool):
        with Session(get_engine()) as s:
            row = s.exec(select(TotpSecret).where(TotpSecret.username == username)).first()
            now = datetime.utcnow()
            if row:
                row.secret = secret
                row.enabled = int(enabled)
                row.updated_at = now
            else:
                row = TotpSecret(username=username, secret=secret, enabled=int(enabled))
            s.add(row)
            s.commit()
