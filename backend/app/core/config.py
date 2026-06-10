"""
core/config.py — Centralised configuration for Gesture DJ Mixer backend.
All tuning knobs live here; nothing is hard-coded inside engine modules.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Gesture DJ Mixer Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── WebSocket ─────────────────────────────────────────────────────────────
    WS_PATH: str = "/ws/gesture"
    WS_MAX_MESSAGE_SIZE: int = 65_536          # 64 KB – landmarks JSON is tiny

    # ── EMA Smoothing ─────────────────────────────────────────────────────────
    # alpha ∈ (0, 1]: higher → more responsive; lower → smoother
    SMOOTHING_ALPHA: float = 0.35

    # ── Pinch (Volume) ────────────────────────────────────────────────────────
    # Raw Euclidean distance between thumb-tip (4) and index-tip (8)
    # in normalised MediaPipe coordinate space (0-1).
    PINCH_MIN_DIST: float = 0.03              # fully closed → volume 0.0
    PINCH_MAX_DIST: float = 0.30              # fully open   → volume 1.0
    PINCH_JITTER_THRESHOLD: float = 0.008     # ignore deltas smaller than this

    # ── Hand Y → Tempo ────────────────────────────────────────────────────────
    # wrist (0) Y in normalised image space; 0 = top, 1 = bottom
    TEMPO_Y_TOP: float = 0.15                 # hand high → fast (tempo 2.0)
    TEMPO_Y_BOTTOM: float = 0.85              # hand low  → slow (tempo 0.5)
    TEMPO_MIN: float = 0.5
    TEMPO_MAX: float = 2.0
    TEMPO_JITTER_THRESHOLD: float = 0.01

    # ── Swipe Detection ───────────────────────────────────────────────────────
    # Minimum horizontal displacement (normalised X) to register a swipe
    SWIPE_VELOCITY_THRESHOLD: float = 0.015   # units/frame in normalised [0,1] space
    SWIPE_MIN_DISPLACEMENT: float = 0.20      # total X travel required
    SWIPE_COOLDOWN_MS: float = 600.0          # ms between accepted swipes
    SWIPE_WINDOW_FRAMES: int = 8              # frames used to calc displacement

    # ── Gesture output clamp ──────────────────────────────────────────────────
    VOLUME_MIN: float = 0.0
    VOLUME_MAX: float = 1.0

    class Config:
        env_prefix = "GDJ_"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()