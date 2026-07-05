-- Initial schema

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
