"""API key auth (Day 7).

Single mechanism: `X-API-Key` header compared against `API_KEY`. When unset,
the documented dev default from `.env.example` applies with a loud warning —
convenient for `docker compose up` demos, never for anything shared. JWT
issue/refresh (HS256 access + rotating refresh) lives in `app/api/jwt_auth.py`
and is accepted as a Bearer alternative; SSO remains post-hackathon.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

logger = logging.getLogger("asset_intel.auth")

DEV_API_KEY = "local-dev-key-123"


def resolve_api_key(environ: Mapping[str, str] | None = None) -> str:
    """Return the expected API key, defaulting loudly to the dev key."""
    env = os.environ if environ is None else environ
    key = (env.get("API_KEY") or "").strip()
    if key:
        return key
    logger.warning(
        "auth_dev_key",
        extra={"hint": "API_KEY unset — using documented dev key; set API_KEY"
                       " for anything shared"},
    )
    return DEV_API_KEY
