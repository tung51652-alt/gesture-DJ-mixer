"""
schemas/payload.py — Pydantic models for every message crossing the WebSocket.

Frontend → Backend : HandPayload   (raw landmarks from MediaPipe)
Backend → Frontend : AudioCommand  (volume / tempo) | SwipeCommand | ErrorResponse
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ── Inbound ────────────────────────────────────────────────────────────────────

class LandmarkPoint(BaseModel):
    """One of the 21 hand landmarks produced by MediaPipe Hands."""
    x: float = Field(..., ge=0.0, le=1.0, description="Normalised [0,1] horizontal position")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalised [0,1] vertical position")
    z: float = Field(0.0, description="Depth relative to wrist (may be 0 if not provided)")

    model_config = {"frozen": True}


class HandPayload(BaseModel):
    """
    Single frame of hand-tracking data sent from the frontend.
    `landmarks` contains exactly 21 points (MediaPipe Hands convention).
    `hand_label` is optional metadata – not used for audio logic but useful for
    debugging multi-hand scenarios.
    """
    landmarks: List[LandmarkPoint] = Field(..., min_length=21, max_length=21)
    hand_label: Optional[str] = Field(None, description="'Left' or 'Right' – informational")
    frame_ts: Optional[float] = Field(None, description="Client-side timestamp (ms) for latency tracking")

    @field_validator("landmarks")
    @classmethod
    def must_have_21(cls, v: list) -> list:
        if len(v) != 21:
            raise ValueError(f"Expected exactly 21 landmarks, got {len(v)}")
        return v


# ── Outbound ───────────────────────────────────────────────────────────────────

class CommandType(str, Enum):
    AUDIO   = "audio"
    SWIPE   = "swipe"
    ERROR   = "error"
    LOST    = "tracking_lost"


class AudioCommand(BaseModel):
    """
    Continuously emitted every frame while a hand is tracked.
    volume  : 0.0 → 1.0  (maps to Web Audio GainNode)
    tempo   : 0.5 → 2.0  (maps to AudioBufferSourceNode.playbackRate)
    """
    type: CommandType = CommandType.AUDIO
    volume: float = Field(..., ge=0.0, le=1.0)
    tempo: float = Field(..., ge=0.5, le=2.0)
    # Echo client timestamp so frontend can measure round-trip latency
    frame_ts: Optional[float] = None


class SwipeDirection(str, Enum):
    LEFT  = "left"
    RIGHT = "right"


class SwipeCommand(BaseModel):
    """
    Emitted once per accepted swipe gesture (after cooldown / debounce).
    """
    type: CommandType = CommandType.SWIPE
    direction: SwipeDirection
    velocity: float = Field(..., description="Smoothed horizontal velocity at detection moment")


class TrackingLostCommand(BaseModel):
    """Sent when the frontend stops sending landmarks (hand disappeared)."""
    type: CommandType = CommandType.LOST


class ErrorResponse(BaseModel):
    """Sent when the backend cannot parse / validate an inbound message."""
    type: CommandType = CommandType.ERROR
    code: str
    detail: str