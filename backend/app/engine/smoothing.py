"""
engine/smoothing.py — Exponential Moving Average (EMA) smoothing for landmarks.

One `LandmarkSmoother` instance is created per WebSocket connection and
lives for the duration of that connection. It keeps no global state.

EMA formula:  S_t = α · x_t + (1 − α) · S_{t-1}
  α → 1 : follow raw input closely  (more responsive, more jitter)
  α → 0 : heavy smoothing           (laggy but silky)
"""

from __future__ import annotations

from typing import List, Optional
from core.config import get_settings


class LandmarkSmoother:
    """
    Stateful EMA smoother for a single client's 21-landmark stream.

    Usage::

        smoother = LandmarkSmoother()
        smoothed = smoother.update(raw_landmarks)   # list of (x, y, z) tuples
    """

    __slots__ = ("_alpha", "_state", "_initialised")

    def __init__(self, alpha: Optional[float] = None) -> None:
        settings = get_settings()
        self._alpha: float = alpha if alpha is not None else settings.SMOOTHING_ALPHA
        # _state[i] = [x, y, z] for landmark i
        self._state: List[List[float]] = []
        self._initialised: bool = False

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, landmarks: List[tuple]) -> List[tuple]:
        """
        Apply EMA to a list of (x, y, z) tuples.
        First call bootstraps internal state directly from input.
        Returns a new list of smoothed (x, y, z) tuples.
        """
        if not self._initialised:
            self._state = [[p[0], p[1], p[2]] for p in landmarks]
            self._initialised = True
            return [(s[0], s[1], s[2]) for s in self._state]

        alpha = self._alpha
        one_minus = 1.0 - alpha

        for i, point in enumerate(landmarks):
            s = self._state[i]
            s[0] = alpha * point[0] + one_minus * s[0]
            s[1] = alpha * point[1] + one_minus * s[1]
            s[2] = alpha * point[2] + one_minus * s[2]

        return [(s[0], s[1], s[2]) for s in self._state]

    def reset(self) -> None:
        """Call on reconnect or after long tracking gap."""
        self._state = []
        self._initialised = False

    @property
    def alpha(self) -> float:
        return self._alpha

    @alpha.setter
    def alpha(self, value: float) -> None:
        if not 0.0 < value <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self._alpha = value