"""Signed session tokens: base64url(payload) + "." + base64url(HMAC-SHA256)."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time

ENV_SECRET = "CAZMIND_SESSION_SECRET"
ENV_DEV = "CAZMIND_DEV"
MIN_SECRET_BYTES = 32
DEFAULT_TTL = 12 * 60 * 60

_B64URL = re.compile(r"[A-Za-z0-9_-]+")
_dev_secret = None


def _b64encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key(secret):
    return secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)


def _sign(secret, payload_part):
    return hmac.new(_key(secret), payload_part.encode("ascii"), hashlib.sha256).digest()


def issue(secret, sub, role, ttl=DEFAULT_TTL, name=None):
    payload = {"sub": sub.strip().lower(), "role": role, "exp": int(time.time()) + int(ttl)}
    if name is not None:
        payload["name"] = name
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    part = _b64encode(body)
    return part + "." + _b64encode(_sign(secret, part))


def verify(secret, token):
    """Payload dict if the token is well formed, correctly signed and unexpired, else None."""
    try:
        if not isinstance(token, str):
            return None
        parts = token.split(".")
        if len(parts) != 2 or not all(_B64URL.fullmatch(p) for p in parts):
            return None
        if not hmac.compare_digest(_sign(secret, parts[0]), _b64decode(parts[1])):
            return None
        payload = json.loads(_b64decode(parts[0]))
        if not isinstance(payload, dict):
            return None
        exp = payload.get("exp")
        if not isinstance(exp, int) or isinstance(exp, bool) or exp <= time.time():
            return None
        if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("role"), str):
            return None
        return payload
    except Exception:
        return None


def resolve_secret(explicit=None):
    """Explicit secret, else $CAZMIND_SESSION_SECRET (at least 32 bytes).

    With neither set, CAZMIND_DEV=1 gives a random per-process secret;
    otherwise this raises. There is no built-in fallback secret.
    """
    global _dev_secret
    value = explicit if explicit is not None else (os.environ.get(ENV_SECRET) or None)
    if value is not None:
        key = _key(value)
        if len(key) < MIN_SECRET_BYTES:
            raise ValueError(f"session secret must be at least {MIN_SECRET_BYTES} bytes")
        return key
    if os.environ.get(ENV_DEV) == "1":
        if _dev_secret is None:
            _dev_secret = secrets.token_bytes(MIN_SECRET_BYTES)
            print(
                f"cazmind: warning: {ENV_SECRET} is not set; using a random "
                "per-process dev secret. Sessions will not survive a restart.",
                file=sys.stderr,
            )
        return _dev_secret
    raise RuntimeError(
        f"no session secret: set {ENV_SECRET} (at least {MIN_SECRET_BYTES} bytes), "
        f"or set {ENV_DEV}=1 for a random per-process dev secret"
    )
