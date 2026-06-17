import base64
import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 200_000


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def hash_password(password: str, iterations: int = _ITERATIONS) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt.

    Returns a self-describing string ``algorithm$iterations$salt$hash`` so the
    parameters travel with the stored hash.
    """

    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_ALGORITHM}${iterations}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against an encoded PBKDF2 hash in constant time."""

    try:
        algorithm, iterations_str, salt_b64, hash_b64 = encoded.split("$")
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False

    salt = _unb64(salt_b64)
    expected = _unb64(hash_b64)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, int(iterations_str)
    )
    return hmac.compare_digest(derived, expected)
