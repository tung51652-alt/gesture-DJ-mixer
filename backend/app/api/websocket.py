"""
api/websocket.py — WebSocket endpoint for realtime gesture processing.

One WebSocket connection = one GestureSession (smoother + mapper).
All processing is async and non-blocking.

Message protocol
────────────────
Frontend → Backend:  JSON  { "landmarks": [...21 points...], "frame_ts": <ms> }
Backend → Frontend:  JSON  AudioCommand  (every frame)
                     JSON  SwipeCommand  (on detected swipe, same frame)
                     JSON  ErrorResponse (on bad input)
                     JSON  TrackingLostCommand (on disconnect / empty payload)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from core.config import get_settings
from engine.smoothing import LandmarkSmoother
from engine.gesture_mapper import GestureMapper
from schemas.payload import (
    HandPayload,
    TrackingLostCommand,
    ErrorResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


# ── Per-client session ────────────────────────────────────────────────────────

class GestureSession:
    """Encapsulates all mutable state for a single WebSocket connection."""

    __slots__ = ("id", "smoother", "mapper", "connected_at", "frame_count")

    def __init__(self) -> None:
        self.id: str = uuid4().hex[:8]
        self.smoother: LandmarkSmoother = LandmarkSmoother()
        self.mapper: GestureMapper = GestureMapper()
        self.connected_at: float = time.monotonic()
        self.frame_count: int = 0

    def reset(self) -> None:
        self.smoother.reset()
        self.mapper.reset()


# ── Connection manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Tracks active WebSocket connections and their sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, GestureSession] = {}

    def add(self, session: GestureSession) -> None:
        self._sessions[session.id] = session
        logger.info("WS connected  | session=%s | total=%d", session.id, len(self._sessions))

    def remove(self, session: GestureSession) -> None:
        self._sessions.pop(session.id, None)
        logger.info("WS disconnected | session=%s | frames=%d | total=%d",
                    session.id, session.frame_count, len(self._sessions))

    @property
    def active_count(self) -> int:
        return len(self._sessions)


manager = ConnectionManager()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _landmarks_to_tuples(payload: HandPayload) -> list:
    """Convert validated Pydantic LandmarkPoints → list of (x,y,z) tuples."""
    return [(lm.x, lm.y, lm.z) for lm in payload.landmarks]


async def _send(ws: WebSocket, obj) -> None:
    """Serialise with stdlib json and send as text."""
    try:
        await ws.send_text(json.dumps(obj.model_dump()))
    except Exception as exc:
        logger.debug("send error: %s", exc)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket(settings.WS_PATH)
async def gesture_ws(websocket: WebSocket) -> None:
    """
    Main WebSocket handler.

    Lifecycle:
    1. Accept connection → create session
    2. Loop: receive → validate → smooth → map → send response(s)
    3. On disconnect / error → clean up session
    """
    await websocket.accept()

    session = GestureSession()
    manager.add(session)

    try:
        while True:
            # ── Receive ───────────────────────────────────────────────────────
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            # ── Parse JSON ────────────────────────────────────────────────────
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                await _send(websocket, ErrorResponse(
                    code="INVALID_JSON",
                    detail=f"Could not parse JSON: {exc}",
                ))
                continue

            # ── Handle explicit "no hand" signal ──────────────────────────────
            # Frontend can send {"landmarks": null} to signal tracking lost.
            if not data.get("landmarks"):
                session.reset()
                await _send(websocket, TrackingLostCommand())
                continue

            # ── Validate with Pydantic ────────────────────────────────────────
            try:
                payload = HandPayload.model_validate(data)
            except ValidationError as exc:
                await _send(websocket, ErrorResponse(
                    code="VALIDATION_ERROR",
                    detail=exc.errors()[0].get("msg", str(exc)),
                ))
                continue

            # ── Smooth ────────────────────────────────────────────────────────
            raw_tuples = _landmarks_to_tuples(payload)
            smoothed   = session.smoother.update(raw_tuples)

            # ── Map gestures ──────────────────────────────────────────────────
            audio_cmd, swipe_cmd = session.mapper.process(
                landmarks=smoothed,
                frame_ts=payload.frame_ts,
            )

            # ── Send responses ────────────────────────────────────────────────
            await _send(websocket, audio_cmd)

            if swipe_cmd is not None:
                await _send(websocket, swipe_cmd)

            session.frame_count += 1

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Unexpected error in session=%s: %s", session.id, exc)
    finally:
        manager.remove(session)
        try:
            await websocket.close()
        except Exception:
            pass