"""Password hashing — bcrypt directly (no passlib: its bcrypt backend is
broken against bcrypt>=4.1's changed internal API)."""
import bcrypt

_MAX_BCRYPT_BYTES = 72


def hash_password(plain: str) -> str:
    if not plain:
        raise ValueError("password must not be empty")
    encoded = plain.encode("utf-8")[:_MAX_BCRYPT_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode("utf-8")[:_MAX_BCRYPT_BYTES]
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError:
        return False
