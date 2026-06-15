import base64
import hashlib
import hmac
import json
import os
import time


def hash_password(password: str, iterations: int = 210_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_value, digest_value = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_value)
        expected = base64.urlsafe_b64decode(digest_value)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session(username: str, secret: str, ttl_seconds: int, now: int | None = None) -> tuple[str, str]:
    current = int(time.time() if now is None else now)
    csrf = _encode(os.urandom(24))
    payload = _encode(json.dumps({"username": username, "exp": current + ttl_seconds, "csrf": csrf}, separators=(",", ":")).encode())
    signature = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", csrf


def read_session(token: str | None, secret: str, now: int | None = None) -> dict | None:
    if not token or not secret:
        return None
    try:
        payload, signature = token.split(".", 1)
        expected = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_decode(payload))
        current = int(time.time() if now is None else now)
        return data if int(data["exp"]) >= current else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def valid_csrf(session: dict, submitted: str | None) -> bool:
    expected = session.get("csrf", "")
    return bool(submitted and expected and hmac.compare_digest(submitted, expected))


class LoginLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.failures: dict[str, list[int]] = {}

    def _recent(self, key: str, now: int) -> list[int]:
        recent = [stamp for stamp in self.failures.get(key, []) if stamp + self.window_seconds >= now]
        self.failures[key] = recent
        return recent

    def allowed(self, key: str, now: int | None = None) -> bool:
        current = int(time.time() if now is None else now)
        return len(self._recent(key, current)) < self.max_attempts

    def record_failure(self, key: str, now: int | None = None) -> None:
        current = int(time.time() if now is None else now)
        self._recent(key, current).append(current)

    def clear(self, key: str) -> None:
        self.failures.pop(key, None)
