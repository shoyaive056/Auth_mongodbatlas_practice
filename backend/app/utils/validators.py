import re

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def validate_password_strength(value: str) -> str:
    """Password policy: 8-128 chars with upper, lower and a digit."""
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(value) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain a number")
    return value


def validate_username(value: str) -> str:
    value = value.strip()
    if not USERNAME_PATTERN.match(value):
        raise ValueError("Username must be 3-30 characters: letters, numbers and underscores only")
    return value.lower()  # stored lowercase so usernames are case-insensitively unique


def clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field cannot be empty")
    if len(value) > 50:
        raise ValueError("Must be at most 50 characters")
    return value
