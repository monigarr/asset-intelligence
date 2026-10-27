"""API key auth (Day 7).

Single mechanism: `X-API-Key` header compared against `API_KEY`. When unset,
the documented dev default from `.env.example` applies with a loud warning —
convenient for `docker compose up` demos, never for anything shared. JWT/SSO
is a post-hackathon item (see module docstring rationale in `app/api/main.py`).
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
