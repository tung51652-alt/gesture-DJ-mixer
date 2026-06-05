"""
engine/math_utils.py — Pure numeric helpers used across the gesture engine.

All functions are stateless and importable independently.
Zero external dependencies — only Python stdlib `math`.
"""

from __future__ import annotations
import math
from typing import Tuple

# Type alias for a 2D or 3D coordinate tuple
Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]


# ── Distance ──────────────────────────────────────────────────────────────────

def euclidean_2d(a: Point2D, b: Point2D) -> float:
    """Euclidean distance between two 2D points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def euclidean_3d(a: Point3D, b: Point3D) -> float:
    """Euclidean distance between two 3D points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


# ── Vector helpers ────────────────────────────────────────────────────────────

def vector_delta_2d(prev: Point2D, curr: Point2D) -> Point2D:
    """Signed displacement vector from prev → curr."""
    return (curr[0] - prev[0], curr[1] - prev[1])


def vector_magnitude(v: Point2D) -> float:
    """L2 norm of a 2D vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1])


def normalise_vector(v: Point2D) -> Point2D:
    """Return unit vector; returns (0,0) for zero-length input."""
    mag = vector_magnitude(v)
    if mag < 1e-9:
        return (0.0, 0.0)
    return (v[0] / mag, v[1] / mag)


# ── Speed ─────────────────────────────────────────────────────────────────────

def velocity_1d(prev_val: float, curr_val: float) -> float:
    """
    Signed scalar velocity for a single axis.
    In frame-rate-independent usage, divide by elapsed_seconds outside.
    """
    return curr_val - prev_val


# ── Range helpers ─────────────────────────────────────────────────────────────

def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def normalise_range(value: float, src_min: float, src_max: float,
                    dst_min: float = 0.0, dst_max: float = 1.0) -> float:
    """
    Linear map from [src_min, src_max] → [dst_min, dst_max].
    Safe against zero-width source range.
    """
    span = src_max - src_min
    if abs(span) < 1e-9:
        return dst_min
    t = (value - src_min) / span
    t = clamp(t, 0.0, 1.0)
    return dst_min + t * (dst_max - dst_min)


def dead_zone(value: float, prev_value: float, threshold: float) -> float:
    """
    Return `value` only if |value - prev_value| > threshold;
    otherwise return `prev_value` (suppress jitter).
    """
    if abs(value - prev_value) > threshold:
        return value
    return prev_value