import base64, hashlib, hmac, json, os, time
from typing import Optional
from app.config import settings

ROLE_ORDER = {"Viewer": 1, "Collector": 2, "Analyst": 3, "Admin": 4}


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120000)
    return "pbkdf2_sha256$120000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_b64, digest_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(rounds))
        return hmac.compare_digest(actual, base64.b64decode(digest_b64))
    except Exception:
        return False


def _sign(payload_b64: str) -> str:
    return hmac.new(settings.secret_key.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def create_session_token(user_id: int, username: str, role: str, ttl_seconds: int = 12 * 3600) -> str:
    payload = {"uid": user_id, "username": username, "role": role, "exp": int(time.time()) + ttl_seconds}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    payload_b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return payload_b64 + "." + _sign(payload_b64)


def read_session_token(token: str) -> Optional[dict]:
    try:
        payload_b64, sig = token.split(".", 1)
        if not hmac.compare_digest(_sign(payload_b64), sig):
            return None
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def role_at_least(role: str, required: str) -> bool:
    return ROLE_ORDER.get(role, 0) >= ROLE_ORDER.get(required, 999)
