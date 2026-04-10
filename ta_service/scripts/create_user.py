from __future__ import annotations

import argparse

from ta_service.config.settings import get_settings
from ta_service.db.mongo import create_mongo_client, get_database
from ta_service.repos.users import UserRepository
from ta_service.services.auth_security import hash_password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a ta_service user account.")
    parser.add_argument("--username", required=True, help="Unique username")
    parser.add_argument("--password", required=True, help="Initial password")
    parser.add_argument("--display-name", dest="display_name", help="Display name")
    parser.add_argument(
        "--role",
        choices=("user", "admin"),
        default="user",
        help="Role for the new account",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    client = create_mongo_client(settings)
    database = get_database(client, settings)
    user_repo = UserRepository(database)

    try:
        if user_repo.get_by_username(args.username):
            raise SystemExit(f"User already exists: {args.username}")

        user = user_repo.create_user(
            username=args.username,
            display_name=args.display_name,
            password_hash=hash_password(args.password),
            role=args.role,
        )
        print(
            f"Created user username={user['username']} role={user['role']} id={user['id']}",
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
