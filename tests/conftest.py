"""Shared test fixtures."""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_pricing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep cost tests hermetic: ignore ambient META_PRICE_* variables.

    `Settings.from_env()` calls `load_dotenv()`, which would otherwise leak a
    developer's real .env pricing into placeholder-cost assertions depending
    on test order. Tests that need pricing set it explicitly via monkeypatch.
    """
    for var in [v for v in os.environ if v.startswith("META_PRICE")]:
        monkeypatch.delenv(var, raising=False)
