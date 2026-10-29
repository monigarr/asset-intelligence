"""Record/replay transports for deterministic live-eval reruns (Stage 3).

RecordingTransport wraps a real transport and stores one JSON cassette per
request keyed by sha256(method + url + body). Headers are excluded from the
key on purpose: the gateway sends its volatile request id only as
X-Request-ID (see MetaClient._send), so identical cases hash identically
across runs. ReplayingTransport serves cassettes back and fails closed on a
cache miss. Cassettes live under eval/.cache/ (gitignored).
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from pathlib import Path

import httpx

_STRIPPED_HEADERS = {"content-length", "content-encoding", "transfer-encoding"}


def cassette_key(request: httpx.Request) -> str:
    """Stable cache key: method + url + body (headers excluded)."""
    h = hashlib.sha256()
    h.update(request.method.encode("ascii"))
    h.update(b"\x00")
    h.update(str(request.url).encode("utf-8"))
    h.update(b"\x00")
    h.update(request.content)
    return h.hexdigest()[:32]


class RecordingTransport(httpx.BaseTransport):
    """Wrap a live transport, storing one cassette per request key."""

    def __init__(self, inner: httpx.BaseTransport, cache_dir: Path | str) -> None:
        self._inner = inner
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._inner.handle_request(request)
        body = response.read()
        cassette = {
            "method": request.method,
            "url": str(request.url),
            "status": response.status_code,
            "headers": [
                [k, v]
                for k, v in response.headers.multi_items()
                if k.lower() not in _STRIPPED_HEADERS
            ],
            "body_b64": base64.b64encode(body).decode("ascii"),
        }
        with self._lock:
            (self._dir / f"{cassette_key(request)}.json").write_text(
                json.dumps(cassette), encoding="utf-8"
            )
        return response


class ReplayMissError(RuntimeError):
    """No cassette matched a replayed request (fail closed)."""


class ReplayingTransport(httpx.BaseTransport):
    """Serve recorded cassettes; raise ReplayMissError on a cache miss."""

    def __init__(self, cache_dir: Path | str) -> None:
        self._dir = Path(cache_dir)
        if not self._dir.is_dir():
            raise FileNotFoundError(f"replay cache not found: {self._dir}")

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        key = cassette_key(request)
        path = self._dir / f"{key}.json"
        if not path.exists():
            raise ReplayMissError(
                f"no cassette for {request.method} {request.url} "
                f"(key {key}); re-record with --record"
            )
        cassette = json.loads(path.read_text(encoding="utf-8"))
        return httpx.Response(
            cassette["status"],
            headers=cassette["headers"],
            content=base64.b64decode(cassette["body_b64"]),
            request=request,
        )
