"""Ephemeral inspection store (Day 7): SQLite records + overlay/original BLOBs, 24h TTL.

Demo posture per ARCHITECTURE.md §5: SQLite file (or :memory:), no cloud.
Production path (M3) is Postgres + MinIO/R2; the compose file already runs
MinIO reserved for that move. Raw upload bytes and notes are never kept --
only the validated result, rendered overlays, the normalized EXIF-stripped
working image (exact pixels the model saw), and review state.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import threading
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from app.validator import InspectionResult

logger = logging.getLogger("asset_intel.store")

TTL_HOURS = 24
MAX_LIST_LIMIT = 200


def _percentile(sorted_values: Sequence[float], pct: float) -> float | None:
    """Linear-interpolation percentile over ascending values (None when empty)."""
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return round(sorted_values[0], 1)
    rank = (pct / 100) * (len(sorted_values) - 1)
    low, high = math.floor(rank), math.ceil(rank)
    span = sorted_values[high] - sorted_values[low]
    return round(sorted_values[low] + span * (rank - low), 1)


class InspectionRecord(InspectionResult):
    review_status: Literal["accept", "edit", "reject"] | None = None
    review_note: str | None = None
    reviewed_at: str | None = None


class InspectionStore:
    """Thread-safe SQLite store with opportunistic TTL expiry."""

    def __init__(self, path: str | Path | None = None, ttl_hours: int = TTL_HOURS) -> None:
        self._path = str(path or "data/inspections.db")
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self._path, check_same_thread=False)
        with self._lock:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS inspections ("
                "request_id TEXT PRIMARY KEY, result_json TEXT NOT NULL, "
                "review_status TEXT, review_note TEXT, "
                "created_at TEXT NOT NULL, reviewed_at TEXT)"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS overlays ("
                "request_id TEXT NOT NULL, image_index INTEGER NOT NULL, "
                "png BLOB NOT NULL, PRIMARY KEY (request_id, image_index))"
            )
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS originals ("
                "request_id TEXT NOT NULL, image_index INTEGER NOT NULL, "
                "mime TEXT NOT NULL, data BLOB NOT NULL, "
                "PRIMARY KEY (request_id, image_index))"
            )
            self._db.commit()

    def save(
        self,
        result: InspectionResult,
        overlays: Mapping[int, bytes],
        originals: Mapping[int, tuple[str, bytes]] | None = None,
    ) -> InspectionRecord:
        """Persist a validated result + image BLOBs. Returns the stored record."""
        # model_construct: result is already valid; full re-validation would
        # demand note/image_count context the store intentionally never keeps.
        record = InspectionRecord.model_construct(
            **result.model_dump(), review_status=None, review_note=None, reviewed_at=None
        )
        now = datetime.now(UTC).isoformat()
        with self._lock:
            self._prune_locked(now)
            self._db.execute(
                "INSERT OR REPLACE INTO inspections "
                "(request_id, result_json, review_status, review_note, created_at, reviewed_at)"
                " VALUES (?, ?, NULL, NULL, ?, NULL)",
                (record.request_id, record.model_dump_json(), now),
            )
            self._db.executemany(
                "INSERT OR REPLACE INTO overlays (request_id, image_index, png)"
                " VALUES (?, ?, ?)",
                [(record.request_id, idx, png) for idx, png in overlays.items()],
            )
            if originals:
                self._db.executemany(
                    "INSERT OR REPLACE INTO originals (request_id, image_index, mime, data)"
                    " VALUES (?, ?, ?, ?)",
                    [
                        (record.request_id, idx, mime, data)
                        for idx, (mime, data) in originals.items()
                    ],
                )
            self._db.commit()
        return record

    def get(self, request_id: str) -> InspectionRecord | None:
        """Fetch a record, or None when unknown/expired."""
        with self._lock:
            self._prune_locked(datetime.now(UTC).isoformat())
            row = self._db.execute(
                "SELECT result_json, review_status, review_note, reviewed_at"
                " FROM inspections WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        payload.update(review_status=row[1], review_note=row[2], reviewed_at=row[3])
        # model_construct: skip re-validation (validated at write; contextless
        # re-checks would spuriously fail without note/image_count).
        return InspectionRecord.model_construct(**payload)

    def get_overlay(self, request_id: str, image_index: int) -> bytes | None:
        with self._lock:
            self._prune_locked(datetime.now(UTC).isoformat())
            row = self._db.execute(
                "SELECT png FROM overlays WHERE request_id = ? AND image_index = ?",
                (request_id, image_index),
            ).fetchone()
        return bytes(row[0]) if row else None

    def get_original(
        self, request_id: str, image_index: int
    ) -> tuple[bytes, str] | None:
        """Stored (data, mime) working image, or None when unknown/expired."""
        with self._lock:
            self._prune_locked(datetime.now(UTC).isoformat())
            row = self._db.execute(
                "SELECT data, mime FROM originals WHERE request_id = ?"
                " AND image_index = ?",
                (request_id, image_index),
            ).fetchone()
        return (bytes(row[0]), str(row[1])) if row else None

    def list(
        self,
        *,
        limit: int = 50,
        review_status: str | None = None,
        asset_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Newest-first inspection summaries (expired records pruned first).

        `review_status`: "pending" (unreviewed) or a decision; `asset_id` is an
        exact match. Only validated results are ever stored, so every row here
        is a successful inspection -- filter by review state, not outcome.
        """
        limit = max(1, min(limit, MAX_LIST_LIMIT))
        with self._lock:
            self._prune_locked(datetime.now(UTC).isoformat())
            query = (
                "SELECT request_id, result_json, review_status,"
                " created_at, reviewed_at FROM inspections"
            )
            clauses: list[str] = []
            params: list[str] = []
            if review_status == "pending":
                clauses.append("review_status IS NULL")
            elif review_status is not None:
                clauses.append("review_status = ?")
                params.append(review_status)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(str(limit))
            rows = self._db.execute(query, params).fetchall()
        items = []
        for request_id, result_json, status, created_at, reviewed_at in rows:
            try:
                result = json.loads(result_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if asset_id is not None and result.get("asset_id") != asset_id:
                continue
            durations = result.get("durations_ms") or {}
            items.append({
                "request_id": request_id,
                "asset_id": result.get("asset_id"),
                "asset_type": result.get("asset_type"),
                "created_at": created_at,
                "reviewed_at": reviewed_at,
                "review_status": status,
                "latency_ms_total": round(sum(float(v) for v in durations.values()), 1),
                "cost_cents": result.get("cost_cents", 0.0),
                "cost_priced": bool(result.get("cost_priced", False)),
                "model_usage": result.get("model_usage") or [],
                "model_trace": result.get("model_trace") or {},
                "usage_total_tokens": (result.get("usage") or {}).get("total_tokens", 0),
                "observation_count": len(result.get("observations") or []),
                "discrepancy_count": len(result.get("discrepancies") or []),
                "missing_count": len(result.get("missing_information") or []),
            })
        return items

    def stats(self) -> dict[str, Any]:
        """Aggregate summary over unexpired inspections (Insights tab)."""
        with self._lock:
            self._prune_locked(datetime.now(UTC).isoformat())
            n = self._db.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
            by_review = dict(
                self._db.execute(
                    "SELECT review_status, COUNT(*)"
                    " FROM inspections GROUP BY review_status"
                ).fetchall()
            )
            blobs = [
                r[0]
                for r in self._db.execute("SELECT result_json FROM inspections").fetchall()
            ]
        priced_cents = 0.0
        unpriced = 0
        latencies: list[float] = []
        for blob in blobs:
            try:
                result = json.loads(blob)
            except (json.JSONDecodeError, TypeError):
                continue
            if result.get("cost_priced"):
                priced_cents += float(result.get("cost_cents") or 0.0)
            else:
                unpriced += 1
            durations = result.get("durations_ms") or {}
            latencies.append(sum(float(v) for v in durations.values()))
        latencies.sort()
        pending = by_review.get(None, 0)
        return {
            "n": n,
            "by_review_status": {
                "pending": pending,
                "accept": by_review.get("accept", 0),
                "edit": by_review.get("edit", 0),
                "reject": by_review.get("reject", 0),
            },
            "review_rate": round((n - pending) / n, 4) if n else None,
            "cost_priced_cents": round(priced_cents, 2),
            "cost_unpriced_count": unpriced,
            "latency_p50_ms": _percentile(latencies, 50),
            "latency_p95_ms": _percentile(latencies, 95),
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def review(
        self, request_id: str, decision: str, note: str | None
    ) -> InspectionRecord | None:
        """Record a human review decision. Returns the updated record or None."""
        record = self.get(request_id)
        if record is None:
            return None
        reviewed_at = datetime.now(UTC).isoformat()
        with self._lock:
            self._db.execute(
                "UPDATE inspections SET review_status = ?, review_note = ?,"
                " reviewed_at = ? WHERE request_id = ?",
                (decision, note, reviewed_at, request_id),
            )
            self._db.commit()
        record.review_status = decision  # type: ignore[assignment]
        record.review_note = note
        record.reviewed_at = reviewed_at
        return record

    def _prune_locked(self, now_iso: str) -> None:
        cutoff = (datetime.fromisoformat(now_iso) - self._ttl).isoformat()
        cur = self._db.execute("DELETE FROM inspections WHERE created_at < ?", (cutoff,))
        if cur.rowcount:
            self._db.execute(
                "DELETE FROM overlays WHERE request_id NOT IN"
                " (SELECT request_id FROM inspections)"
            )
            self._db.execute(
                "DELETE FROM originals WHERE request_id NOT IN"
                " (SELECT request_id FROM inspections)"
            )
            self._db.commit()
            logger.debug("store_prune", extra={"expired": cur.rowcount})

    def close(self) -> None:
        with self._lock:
            self._db.close()
