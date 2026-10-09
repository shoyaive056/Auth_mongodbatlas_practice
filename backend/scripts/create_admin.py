"""Promote an existing, registered user to admin.

1. Register normally in the app and verify the email.
2. From the backend folder run:
       python -m scripts.create_admin you@example.com
No password is typed here and no admin credentials live in the code.
"""
import sys

from app.core.config import get_settings
from app.core.database import close_client, get_db
from app.models.user import COLLECTION, ROLE_ADMIN


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.create_admin <email>")
        return 1
    get_settings().validate_for_startup()
    result = get_db()[COLLECTION].update_one({"email": sys.argv[1].lower()}, {"$set": {"role": ROLE_ADMIN}})
    close_client()
    if result.matched_count == 0:
        print("No user with that email. Register first, then run this again.")
        return 1
    print("Done. That user is now an admin (they must log in again to see it).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
