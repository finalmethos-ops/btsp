from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from secrets import token_hex

import jwt

from app.core.config import settings

ALGORITHM = "HS256"
PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = token_hex(16)
    digest = pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, raw_iterations, salt, expected_digest = password_hash.split("$", 3)
        iterations = int(raw_iterations)
    except (AttributeError, TypeError, ValueError):
        return False
    if (
        algorithm != "pbkdf2_sha256"
        or iterations < 100_000
        or iterations > 2_000_000
        or not salt
        or len(expected_digest) != 64
    ):
        return False
    try:
        digest = pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
    except (OverflowError, ValueError):
        return False
    return compare_digest(digest.hex(), expected_digest)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
