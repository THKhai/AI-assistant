CREATE TABLE IF NOT EXISTS revoked_tokens (
    id         INTEGER  PRIMARY KEY AUTOINCREMENT,
    jti        TEXT     UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_jti ON revoked_tokens(jti);
