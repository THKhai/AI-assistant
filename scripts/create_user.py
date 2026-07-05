"""
Admin CLI — create a user account.

Usage:
    python311 scripts/create_user.py --username khai --password <secret>
    python311 scripts/create_user.py --username mom --password <secret> --role member

Roles: admin (full access), member (standard access). Default: member.
This is the ONLY way to create accounts. No /register route exists.
"""
import argparse
import sys
from pathlib import Path

# Make sure src/ is importable when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.db import init_db
from src.core import services
from src.core.auth import hash_password

_VALID_ROLES = {"admin", "member"}


def main():
    parser = argparse.ArgumentParser(description="Create a user account for the AI Assistant web UI.")
    parser.add_argument("--username", required=True, help="Login username")
    parser.add_argument("--password", required=True, help="Plain-text password (will be hashed)")
    parser.add_argument("--role", default="member", choices=list(_VALID_ROLES), help="Role: admin or member (default: member)")
    args = parser.parse_args()

    init_db()

    if services.users.get(args.username):
        print(f"Error: username '{args.username}' already exists.")
        sys.exit(1)

    pw_hash = hash_password(args.password)
    user_id = services.users.create(args.username, pw_hash, role=args.role)
    print(f"Created user '{args.username}' role={args.role} (id={user_id})")


if __name__ == "__main__":
    main()
