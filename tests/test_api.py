"""API tests: routes, auth, adapter, errors, store (TestClient, faked pipeline)."""

from __future__ import annotations

import asyncio
import io
import json
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.main import create_app
from app.api.store import InspectionStore
from app.gateway.errors import (
    MetaAuthError,
    MetaClientError,
    MetaRateLimitError,
    MetaResponseError,
    MetaServerError,
    MetaTimeoutError,
)
from app.validator import validate_inspection

NOTE = "Crack seen"
KEY = {"X-API-Key": "test-key-123"}


def _jpeg(w: int = 16, h: int = 12, exif_orientation: int | None = None) -> bytes:
    img = Image.new("RGB", (w, h), (200, 200, 200))
    buf = io.BytesIO()
    if exif_orientation is None:
        img.save(buf, format="JPEG")
    else:
        exif = Image.Exif()
        exif[274] = exif_orientation
        img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _result(note: str = NOTE, with_mask: bool = True, rle_size: list[int] | None = None):
    segs = []
    evidence: list[dict[str, Any]] = [{"source": "maintenance_note", "span": [0, 5]}]
    if with_mask:
        h, w = rle_size or [12, 16]
        segs = [{
            "mask_id": "mask_1", "label": "crack", "bbox": [1, 1, 5, 5],
            "confidence": 0.9,
            "rle": {"size": [h, w], "counts": [h * w]},
            "source_image": "image_0",
        }]
        evidence.insert(0, {"source": "image_0", "mask_id": "mask_1"})
    return validate_inspection(
        {
            "request_id": "req_t1", "asset_id": "A-1",
            "model_trace": {"sam": "s", "vision": "v", "reasoning": "r",
                            "planning": "w", "timestamp": "2026-10-26T00:00:00+00:00"},
            "segmentations": segs,
            "observations": [{"text": "crack visible", "evidence": evidence,
                              "uncertainty": 0.3}],
            "discrepancies": [],
            "missing_information": ["crack_dimensions"],
            "recommended_next_step": "Request qualified inspection.",
            "human_review_required": True,
            "cost_cents": 11.0, "cost_priced": False,
        },
        note=note, image_count=1,
    )


class _FakePipeline:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def run_full(self, images, note="", asset_meta=None, request_id=None):
        self.calls.append({"images": images, "note": note, "asset_meta": asset_meta})
        if self.error is not None:
            raise self.error
        return self.result


def _client(tmp_path, fake: _FakePipeline, rate_limit: str = "1000/minute") -> TestClient:
    store = InspectionStore(tmp_path / "t.db")
    app = create_app(pipeline=fake, store=store, api_key="test-key-123",
                     rate_limit=rate_limit, enable_otel=False)
    return TestClient(app)


def _post(client: TestClient, files, note: str = NOTE, meta: Any = None, headers=KEY):
    return client.post(
        "/v1/inspections",
        files=files,
        data={"note": note, "asset_meta": json.dumps(meta if meta is not None else {})},
        headers=headers,
    )


# -- open routes --------------------------------------------------------


def test_healthz_and_metrics_open(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False)))
    assert client.get("/healthz").json()["status"] == "ok"
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "inspection_requests_total" in metrics.text


# -- auth ---------------------------------------------------------------


def test_auth_required(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False)))
    files = [("images", ("a.jpg", _jpeg(), "image/jpeg"))]
    assert _post(client, files, headers={}).status_code == 401
    assert _post(client, files, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/v1/inspections/req_x").status_code == 401


# -- happy flow ---------------------------------------------------------


def test_create_get_review_flow(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False)))
    res = _post(client, [("images", ("a.jpg", _jpeg(), "image/jpeg"))],
                meta={"asset_id": "FLOW-1"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["asset_id"] == "A-1"  # canned result echoes its own asset
    assert body["human_review_required"] is True
    rid = body["request_id"]

    got = client.get(f"/v1/inspections/{rid}", headers=KEY)
    assert got.status_code == 200
    assert got.json()["request_id"] == rid
    assert got.json()["review_status"] is None

    rev = client.post(f"/v1/inspections/{rid}/review", headers=KEY,
                      json={"decision": "accept"})
    assert rev.status_code == 200
    assert rev.json()["review_status"] == "accept"
    assert client.get(f"/v1/inspections/{rid}", headers=KEY).json()["review_status"] == "accept"


def test_overlay_png_matches_upload(tmp_path) -> None:
    img = _jpeg(16, 12)
    client = _client(tmp_path, _FakePipeline(_result(rle_size=[12, 16])))
    rid = _post(client, [("images", ("a.jpg", img, "image/jpeg"))]).json()["request_id"]
    res = client.get(f"/v1/inspections/{rid}/overlay?image=0", headers=KEY)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(res.content)) as out:
        assert out.size == (16, 12)


def test_exif_stripped_and_transposed(tmp_path) -> None:
    fake = _FakePipeline(_result(with_mask=False))
    client = _client(tmp_path, fake)
    res = _post(client, [("images", ("a.jpg", _jpeg(16, 12, exif_orientation=6), "image/jpeg"))])
    assert res.status_code == 200
    seen = fake.calls[0]["images"][0]
    with Image.open(io.BytesIO(seen)) as normalized:
        assert dict(normalized.getexif()) == {}
        assert normalized.size == (12, 16)  # orientation-6 transpose applied


# -- caller mistakes ----------------------------------------------------


def test_caller_mistakes(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False)))
    files = [("images", ("a.jpg", _jpeg(), "image/jpeg"))]
    assert client.post("/v1/inspections", headers=KEY).status_code == 422  # no images part
    gif = io.BytesIO()
    Image.new("RGB", (8, 8)).save(gif, format="GIF")
    assert _post(client, [("images", ("a.gif", gif.getvalue(), "image/gif"))]).status_code == 400
    assert _post(client, [("images", ("a.jpg", bytes(15 * 1024 * 1024 + 1), "image/jpeg"))]).status_code == 413
    bad_meta = client.post("/v1/inspections", files=files, headers=KEY,
                           data={"note": NOTE, "asset_meta": "{oops"})
    assert bad_meta.status_code == 400
    assert _post(client, files, note="x" * 10001).status_code == 400


def test_adapter_unit_rejects_empty_list() -> None:
    from fastapi import HTTPException

    from app.api.adapter import normalize_inspection

    with pytest.raises(HTTPException) as ei:
        asyncio.run(normalize_inspection([], "n", "{}"))
    assert ei.value.status_code == 400


# -- upstream + validation failures -------------------------------------


def _bad_payload_error():
    from pydantic import ValidationError

    try:
        validate_inspection({"request_id": "x"}, note=NOTE, image_count=1)
    except ValidationError as exc:
        return exc
    raise AssertionError("unreachable")


def test_upstream_error_mapping(tmp_path) -> None:
    cases = [
        (_bad_payload_error(), 422, None),
        (MetaRateLimitError("slow", retry_after_s=7), 429, "7"),
        (MetaServerError("down"), 502, None),
        (MetaTimeoutError("t"), 504, None),
        (MetaAuthError("bad"), 500, None),
        (MetaClientError("rejected"), 502, None),
        (MetaResponseError("garbage"), 422, None),
    ]
    for error, status, retry_after in cases:
        client = _client(tmp_path, _FakePipeline(_result(with_mask=False), error=error))
        res = _post(client, [("images", ("a.jpg", _jpeg(), "image/jpeg"))])
        assert res.status_code == status, (error, res.text)
        if retry_after is not None:
            assert res.headers["Retry-After"] == retry_after
    # auth failure detail must not leak key material
    assert "test-key" not in res.text


def test_validation_failures_metered(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False), error=_bad_payload_error()))

    def counter() -> float:
        text = client.get("/metrics").text
        m = re.search(r"inspection_validation_failures_total (\d+\.\d+)", text)
        return float(m.group(1)) if m else 0.0

    before = counter()
    _post(client, [("images", ("a.jpg", _jpeg(), "image/jpeg"))])
    assert counter() - before == 1.0


def test_rate_limit(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False)), rate_limit="2/minute")
    files = [("images", ("a.jpg", _jpeg(), "image/jpeg"))]
    assert _post(client, files).status_code == 200
    assert _post(client, files).status_code == 200
    assert _post(client, files).status_code == 429


# -- unknown ids + store TTL --------------------------------------------


def test_unknown_ids(tmp_path) -> None:
    client = _client(tmp_path, _FakePipeline(_result(with_mask=False)))
    assert client.get("/v1/inspections/nope", headers=KEY).status_code == 404
    assert client.get("/v1/inspections/nope/overlay", headers=KEY).status_code == 404
    assert client.post("/v1/inspections/nope/review", headers=KEY,
                       json={"decision": "accept"}).status_code == 404
    rid = _post(client, [("images", ("a.jpg", _jpeg(), "image/jpeg"))]).json()["request_id"]
    assert client.get(f"/v1/inspections/{rid}/overlay?image=9", headers=KEY).status_code == 404
    bad = client.post(f"/v1/inspections/{rid}/review", headers=KEY,
                      json={"decision": "maybe"})
    assert bad.status_code == 422


def test_store_ttl_expiry(tmp_path) -> None:
    import sqlite3

    store = InspectionStore(tmp_path / "t.db", ttl_hours=24)
    record = store.save(_result(with_mask=False), {})
    assert store.get(record.request_id) is not None
    store.close()
    with sqlite3.connect(tmp_path / "t.db") as db:
        db.execute("UPDATE inspections SET created_at = ? WHERE request_id = ?",
                   ("2000-01-01T00:00:00+00:00", record.request_id))
        db.commit()
    reopened = InspectionStore(tmp_path / "t.db", ttl_hours=24)
    assert reopened.get(record.request_id) is None
    reopened.close()


def test_jwt_compose_escaped_hash(tmp_path) -> None:
    from argon2 import PasswordHasher
    from fastapi.testclient import TestClient

    from app.api.main import create_app

    pwd_hash = PasswordHasher().hash("pw")
    app = create_app(
        api_key="k",
        store_path=str(tmp_path / "t.db"),
        jwt_secret="test-secret-1234567890",
        ui_username="u",
        ui_password_hash=pwd_hash.replace("$", "$$"),
    )
    client = TestClient(app)
    r = client.post("/v1/auth/token", json={"username": "u", "password": "pw"})
    assert r.status_code == 200, r.text


def test_jwt_issue_refresh_and_bearer_access(tmp_path) -> None:
    from argon2 import PasswordHasher
    from fastapi.testclient import TestClient

    from app.api.main import create_app

    pwd_hash = PasswordHasher().hash("pw")
    app = create_app(
        api_key="k",
        store_path=str(tmp_path / "t.db"),
        jwt_secret="test-secret-1234567890",
        ui_username="u",
        ui_password_hash=pwd_hash,
    )
    client = TestClient(app)
    r = client.post("/v1/auth/token", json={"username": "u", "password": "pw"})
    assert r.status_code == 200, r.text
    access, refresh = r.json()["access_token"], r.json()["refresh_token"]
    assert r.json()["token_type"] == "bearer"
    r2 = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200, r2.text
    r3 = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert r3.status_code == 401  # rotated: single use
    r4 = client.post(
        "/v1/inspections/nope/review",
        json={"decision": "accept"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r4.status_code == 404  # auth passed, unknown id
    r5 = client.post(
        "/v1/inspections/nope/review",
        json={"decision": "accept"},
        headers={"Authorization": "Bearer bogus"},
    )
    assert r5.status_code == 401
    r6 = client.post("/v1/auth/token", json={"username": "u", "password": "wrong"})
    assert r6.status_code == 401


def test_jwt_routes_503_when_unconfigured(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.api.main import create_app

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("UI_USERNAME", raising=False)
    monkeypatch.delenv("UI_PASSWORD_HASH", raising=False)
    app = create_app(api_key="k", store_path=str(tmp_path / "t.db"))
    client = TestClient(app)
    assert client.post("/v1/auth/token", json={"username": "u", "password": "p"}).status_code == 503
    assert client.post("/v1/auth/refresh", json={"refresh_token": "x"}).status_code == 503


def test_rate_limit_storage_uri_plumbing(tmp_path) -> None:
    from app.api.main import create_app

    app = create_app(
        api_key="k",
        store_path=str(tmp_path / "t.db"),
        rate_limit_storage="redis://localhost:6379/0",
    )
    assert "redis" in type(app.state.limiter._storage).__name__.lower()
    app2 = create_app(api_key="k", store_path=str(tmp_path / "t2.db"))
    assert "memory" in type(app2.state.limiter._storage).__name__.lower()
