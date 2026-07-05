-- User accounts (admin-created only, no self-signup)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    username      TEXT     UNIQUE NOT NULL,
    password_hash TEXT     NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted       INTEGER  DEFAULT 0
);
