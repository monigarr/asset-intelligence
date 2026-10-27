"""Ephemeral inspection store (Day 7): SQLite records + overlay BLOBs, 24h TTL.

Demo posture per ARCHITECTURE.md §5: SQLite file (or :memory:), no cloud.
Production path (M3) is Postgres + MinIO/R2; the compose file already runs
MinIO reserved for that move. No raw uploads or notes are stored — only the
validated result, rendered overlays, and review state (data minimization).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from app.validator import InspectionResult

logger = logging.getLogger("asset_intel.store")

TTL_HOURS = 24


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
            self._db.commit()

    def save(
        self, result: InspectionResult, overlays: Mapping[int, bytes]
    ) -> InspectionRecord:
        """Persist a validated result + overlays. Returns the stored record."""
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
            self._db.commit()
            logger.debug("store_prune", extra={"expired": cur.rowcount})

    def close(self) -> None:
        with self._lock:
            self._db.close()
