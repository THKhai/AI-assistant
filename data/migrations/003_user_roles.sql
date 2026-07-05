-- Add role to users. Roles: admin, member (extensible later)
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'member';
