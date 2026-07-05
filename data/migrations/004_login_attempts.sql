CREATE TABLE IF NOT EXISTS login_attempts (
    id         INTEGER  PRIMARY KEY AUTOINCREMENT,
    username   TEXT     NOT NULL,
    ip         TEXT     NOT NULL,
    success    INTEGER  NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_user ON login_attempts(username, created_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip   ON login_attempts(ip, created_at);
