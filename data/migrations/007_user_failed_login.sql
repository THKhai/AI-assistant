-- Replace login_attempts + auth_events tables with a lightweight counter on users
ALTER TABLE users ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until DATETIME;

DROP TABLE IF EXISTS login_attempts;
DROP TABLE IF EXISTS auth_events;
