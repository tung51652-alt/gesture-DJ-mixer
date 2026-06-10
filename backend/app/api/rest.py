"""
api/rest.py — Lightweight REST endpoints.

GET /health   → liveness probe
GET /config   → current tunable parameters
GET /stats    → active WebSocket connection count
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import get_settings
from api.websocket import manager

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": settings.APP_VERSION})


@router.get("/config")
async def get_config() -> JSONResponse:
    cfg = get_settings()
    return JSONResponse({
        "smoothing": {
            "alpha": cfg.SMOOTHING_ALPHA,
        },
        "volume": {
            "pinch_min_dist": cfg.PINCH_MIN_DIST,
            "pinch_max_dist": cfg.PINCH_MAX_DIST,
            "jitter_threshold": cfg.PINCH_JITTER_THRESHOLD,
        },
        "tempo": {
            "y_top": cfg.TEMPO_Y_TOP,
            "y_bottom": cfg.TEMPO_Y_BOTTOM,
            "min": cfg.TEMPO_MIN,
            "max": cfg.TEMPO_MAX,
            "jitter_threshold": cfg.TEMPO_JITTER_THRESHOLD,
        },
        "swipe": {
            "velocity_threshold": cfg.SWIPE_VELOCITY_THRESHOLD,
            "min_displacement": cfg.SWIPE_MIN_DISPLACEMENT,
            "cooldown_ms": cfg.SWIPE_COOLDOWN_MS,
            "window_frames": cfg.SWIPE_WINDOW_FRAMES,
        },
    })


@router.get("/stats")
async def get_stats() -> JSONResponse:
    return JSONResponse({"active_connections": manager.active_count})