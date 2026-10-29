"""JWT issue/refresh for the review UI (FR-09, ARCH §6).

HS256 access tokens (15 min) + rotating refresh tokens (24 h, single-use) for
one env-configured UI user (UI_USERNAME + Argon2 UI_PASSWORD_HASH). Accepted as
a Bearer alternative to X-API-Key on all protected routes.

Refresh rotation is enforced via an in-memory consumed-jti set: correct on the
single-worker deployment (Dockerfile runs one worker). Multi-replica needs a
shared denylist (Valkey, M3).

Mint a password hash with:
    python -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('pw'))"
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

ACCESS_TTL_S = 900
REFRESH_TTL_S = 86400
_ALGORITHM = "HS256"

_hasher = PasswordHasher()


class JWTError(Exception):
    """Any JWT issue/verify/rotate failure (caller maps to 401/503)."""


@dataclass(frozen=True)
class JWTConfig:
    secret: str = ""
    username: str = "reviewer"
    password_hash: str = ""
    access_ttl_s: int = ACCESS_TTL_S
    refresh_ttl_s: int = REFRESH_TTL_S

    @property
    def configured(self) -> bool:
        return bool(self.secret and self.password_hash)


def verify_password(password_hash: str, plaintext: str) -> bool:
    try:
        return _hasher.verify(password_hash, plaintext)
    except (VerifyMismatchError, InvalidHash, ValueError, TypeError, AttributeError):
        return False


def issue_token_pair(config: JWTConfig, username: str) -> dict[str, Any]:
    now = int(time.time())
    access = jwt.encode(
        {"sub": username, "type": "access", "iat": now, "exp": now + config.access_ttl_s},
        config.secret,
        algorithm=_ALGORITHM,
    )
    refresh = jwt.encode(
        {
            "sub": username,
            "type": "refresh",
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": now + config.refresh_ttl_s,
        },
        config.secret,
        algorithm=_ALGORITHM,
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": config.access_ttl_s,
    }


def verify_access_token(config: JWTConfig, token: str) -> str:
    """Return the subject of a valid access token, else raise JWTError."""
    if not config.secret:
        raise JWTError("JWT not configured")
    try:
        claims = jwt.decode(token, config.secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise JWTError(f"invalid token: {exc}") from exc
    if claims.get("type") != "access" or not claims.get("sub"):
        raise JWTError("not an access token")
    return str(claims["sub"])


def rotate_token_pair(
    config: JWTConfig, refresh_token: str, consumed: dict[str, int]
) -> dict[str, Any]:
    """Consume a refresh token (single-use) and issue a fresh pair."""
    if not config.secret:
        raise JWTError("JWT not configured")
    try:
        claims = jwt.decode(refresh_token, config.secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise JWTError(f"invalid refresh token: {exc}") from exc
    if claims.get("type") != "refresh" or not claims.get("sub"):
        raise JWTError("not a refresh token")
    jti = str(claims.get("jti") or "")
    now = int(time.time())
    for old_jti in [k for k, exp in consumed.items() if exp < now]:
        del consumed[old_jti]
    if not jti or jti in consumed:
        raise JWTError("refresh token already used")
    consumed[jti] = int(claims.get("exp", now))
    return issue_token_pair(config, str(claims["sub"]))
