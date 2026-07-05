"""Drafting primitives and body-measurement presets (Aldrich-style, women's).

Measurements are in centimetres. Presets follow the standard UK/EU women's size
charts used in Winifred Aldrich, *Metric Pattern Cutting for Women's Wear*
(bust/waist/hip and the common secondary measurements). These are *real* body
sizes, so the drafted blocks correspond to garments you could actually cut and
sew — just simplified to the basic blocks.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #
def cubic_bezier(p0, p1, p2, p3, n: int = 16):
    """Sample a cubic Bezier (used for neck / armhole / sleeve-cap curves)."""
    out = []
    for k in range(n + 1):
        t = k / n
        mt = 1 - t
        x = (mt**3 * p0[0] + 3 * mt**2 * t * p1[0]
             + 3 * mt * t**2 * p2[0] + t**3 * p3[0])
        y = (mt**3 * p0[1] + 3 * mt**2 * t * p1[1]
             + 3 * mt * t**2 * p2[1] + t**3 * p3[1])
        out.append((x, y))
    return out


def line_pts(a, b, n: int = 1):
    return [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            for k in range(n + 1)]


def normal(a, b):
    """Unit normal (left side) of segment a->b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return (-dy / L, dx / L)


# --------------------------------------------------------------------------- #
# measurements
# --------------------------------------------------------------------------- #
@dataclass
class Measurements:
    size: str = "12"
    bust: float = 88.0          # full bust girth
    waist: float = 68.0
    hip: float = 94.0
    nape_to_waist: float = 41.0     # back length
    armscye_depth: float = 21.0     # nape to chest/scye line
    back_neck_width: float = 7.2
    shoulder: float = 12.2          # shoulder seam length
    hip_depth: float = 20.0         # waist to hip line
    skirt_length: float = 60.0      # waist to hem
    sleeve_length: float = 58.0     # shoulder point to wrist
    bicep: float = 30.0             # upper-arm girth (for sleeve width)


# standard women's sizes (bust/waist/hip per Aldrich-style charts)
PRESETS: dict[str, Measurements] = {
    "10": Measurements("10", 84, 64, 89, 40.0, 20.5, 7.0, 12.0, 20, 60, 57, 28),
    "12": Measurements("12", 88, 68, 94, 41.0, 21.0, 7.2, 12.2, 20, 60, 58, 30),
    "14": Measurements("14", 92, 74, 99, 42.0, 21.5, 7.4, 12.6, 20, 61, 58, 32),
    "16": Measurements("16", 97, 80, 104, 42.5, 22.0, 7.6, 13.0, 20, 61, 59, 34),
}


def get_measurements(size: str) -> Measurements:
    if size not in PRESETS:
        raise SystemExit(f"unknown size '{size}'. available: {', '.join(PRESETS)}")
    return PRESETS[size]


# --------------------------------------------------------------------------- #
# a pattern piece
# --------------------------------------------------------------------------- #
@dataclass
class Piece:
    name: str
    size: str
    boundary: list = field(default_factory=list)   # closed outline [(x,y),...]
    internals: list = field(default_factory=list)  # [[(x,y),...], ...] dart legs etc.
    notches: list = field(default_factory=list)    # [(x,y, nx,ny), ...] pos + inward dir
    grain: tuple | None = None                      # ((x1,y1),(x2,y2))
    label_pos: tuple = (0.0, 0.0)

    def bbox(self):
        xs = [p[0] for p in self.boundary]
        ys = [p[1] for p in self.boundary]
        return min(xs), min(ys), max(xs), max(ys)
