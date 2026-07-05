-- Long-lived refresh tokens (SHA-256 hashed, rotated on use)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         INTEGER  PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT     UNIQUE NOT NULL,
    username   TEXT     NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked    INTEGER  NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(username);

-- Auth audit log (login, logout, password change, role change, TOTP events)
CREATE TABLE IF NOT EXISTS auth_events (
    id         INTEGER  PRIMARY KEY AUTOINCREMENT,
    username   TEXT     NOT NULL,
    event      TEXT     NOT NULL,
    ip         TEXT     NOT NULL DEFAULT '',
    detail     TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_auth_events_user ON auth_events(username, created_at);

-- TOTP secrets (one per user, stored as base32)
CREATE TABLE IF NOT EXISTS totp_secrets (
    id         INTEGER  PRIMARY KEY AUTOINCREMENT,
    username   TEXT     UNIQUE NOT NULL,
    secret     TEXT     NOT NULL,
    enabled    INTEGER  NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
