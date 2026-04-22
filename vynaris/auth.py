"""Password hashing + session utilities."""

from __future__ import annotations

import secrets

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def new_invite_token() -> str:
    return secrets.token_urlsafe(24)


def validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password.lower() == password or password.upper() == password:
        if not any(c.isdigit() for c in password):
            return "Add at least one number or a mix of upper/lowercase."
    return None
