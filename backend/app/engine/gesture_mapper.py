"""
engine/gesture_mapper.py — Business logic: smoothed landmarks → AudioCommand / SwipeCommand.

One `GestureMapper` instance per WebSocket connection.

MediaPipe Hands landmark indices (relevant subset):
  0  – WRIST
  4  – THUMB_TIP
  8  – INDEX_FINGER_TIP
  9  – MIDDLE_FINGER_MCP  (palm centre proxy)
"""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, List, Optional, Tuple, Union

from core.config import get_settings
from engine.math_utils import (
    euclidean_2d,
    normalise_range,
    clamp,
    dead_zone,
    velocity_1d,
)
from schemas.payload import (
    AudioCommand,
    SwipeCommand,
    SwipeDirection,
)

# MediaPipe landmark indices
_WRIST       = 0
_THUMB_TIP   = 4
_INDEX_TIP   = 8

# Type alias for smoothed landmark list
Landmarks = List[Tuple[float, float, float]]

# Union of possible outputs from a single frame
GestureResult = Union[AudioCommand, SwipeCommand, None]


class GestureMapper:
    """
    Stateful per-connection gesture interpreter.

    Call `process(landmarks, frame_ts)` every frame.
    Returns an `AudioCommand`, a `SwipeCommand`, or `None` if nothing changed.

    Edge cases handled:
    - Swipe cooldown / debounce (SWIPE_COOLDOWN_MS)
    - Anti-jitter dead-zones for volume and tempo
    - Swipe detection over a rolling window of wrist X positions
    """

    __slots__ = (
        "_cfg",
        "_prev_volume",
        "_prev_tempo",
        "_wrist_x_history",
        "_last_swipe_ts",
        "_swipe_displacement_acc",
    )

    def __init__(self) -> None:
        self._cfg = get_settings()

        # Last emitted values for jitter suppression
        self._prev_volume: float = 0.5
        self._prev_tempo:  float = 1.0

        # Rolling window of wrist X positions for swipe detection
        self._wrist_x_history: Deque[float] = deque(
            maxlen=self._cfg.SWIPE_WINDOW_FRAMES
        )

        # Timestamp (seconds) of the last accepted swipe
        self._last_swipe_ts: float = 0.0

        # Accumulated horizontal displacement for in-progress swipe
        self._swipe_displacement_acc: float = 0.0

    # ── Public ────────────────────────────────────────────────────────────────

    def process(
        self,
        landmarks: Landmarks,
        frame_ts: Optional[float] = None,
    ) -> Tuple[AudioCommand, Optional[SwipeCommand]]:
        """
        Main entry point. Always returns an AudioCommand.
        Also returns a SwipeCommand when a swipe is detected (else None).
        """
        volume = self._calc_volume(landmarks)
        tempo  = self._calc_tempo(landmarks)

        swipe = self._detect_swipe(landmarks)

        audio_cmd = AudioCommand(
            volume=volume,
            tempo=tempo,
            frame_ts=frame_ts,
        )

        return audio_cmd, swipe

    def reset(self) -> None:
        """Reset mutable state, e.g. after a tracking loss gap."""
        self._prev_volume = 0.5
        self._prev_tempo  = 1.0
        self._wrist_x_history.clear()
        self._swipe_displacement_acc = 0.0

    # ── Private: Volume ───────────────────────────────────────────────────────

    def _calc_volume(self, lm: Landmarks) -> float:
        thumb = (lm[_THUMB_TIP][0], lm[_THUMB_TIP][1])
        index = (lm[_INDEX_TIP][0], lm[_INDEX_TIP][1])

        raw_dist = euclidean_2d(thumb, index)

        volume = normalise_range(
            raw_dist,
            src_min=self._cfg.PINCH_MIN_DIST,
            src_max=self._cfg.PINCH_MAX_DIST,
            dst_min=self._cfg.VOLUME_MIN,
            dst_max=self._cfg.VOLUME_MAX,
        )

        # Anti-jitter: only update if delta exceeds threshold
        volume = dead_zone(volume, self._prev_volume, self._cfg.PINCH_JITTER_THRESHOLD)
        volume = clamp(volume, self._cfg.VOLUME_MIN, self._cfg.VOLUME_MAX)

        self._prev_volume = volume
        return round(volume, 4)

    # ── Private: Tempo ────────────────────────────────────────────────────────

    def _calc_tempo(self, lm: Landmarks) -> float:
        wrist_y = lm[_WRIST][1]

        # Y=0 is top → hand high = fast; Y=1 is bottom → hand low = slow
        # So we invert: map Y_TOP→tempo_max, Y_BOTTOM→tempo_min
        tempo = normalise_range(
            wrist_y,
            src_min=self._cfg.TEMPO_Y_TOP,
            src_max=self._cfg.TEMPO_Y_BOTTOM,
            dst_min=self._cfg.TEMPO_MAX,   # note: inverted
            dst_max=self._cfg.TEMPO_MIN,
        )

        tempo = dead_zone(tempo, self._prev_tempo, self._cfg.TEMPO_JITTER_THRESHOLD)
        tempo = clamp(tempo, self._cfg.TEMPO_MIN, self._cfg.TEMPO_MAX)

        self._prev_tempo = tempo
        return round(tempo, 4)

    # ── Private: Swipe ────────────────────────────────────────────────────────

    def _detect_swipe(self, lm: Landmarks) -> Optional[SwipeCommand]:
        wrist_x = lm[_WRIST][0]

        history = self._wrist_x_history
        history.append(wrist_x)

        if len(history) < self._cfg.SWIPE_WINDOW_FRAMES:
            return None  # not enough history yet

        # Displacement over the full window
        displacement = wrist_x - history[0]           # signed X travel
        abs_disp = abs(displacement)

        # Instantaneous velocity (last frame delta)
        vel = velocity_1d(history[-2], history[-1])

        # Need both enough total displacement AND fast enough velocity
        if abs_disp < self._cfg.SWIPE_MIN_DISPLACEMENT:
            return None
        if abs(vel) < self._cfg.SWIPE_VELOCITY_THRESHOLD:
            return None

        # Cooldown check
        now = time.monotonic()
        elapsed_ms = (now - self._last_swipe_ts) * 1000.0
        if elapsed_ms < self._cfg.SWIPE_COOLDOWN_MS:
            return None

        # Accept swipe
        self._last_swipe_ts = now
        self._wrist_x_history.clear()   # reset window to avoid re-triggering

        direction = SwipeDirection.RIGHT if displacement > 0 else SwipeDirection.LEFT

        return SwipeCommand(
            direction=direction,
            velocity=round(abs(vel), 4),
        )