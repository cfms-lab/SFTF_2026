"""Aldrich-style basic block drafting -> Piece objects.

Implements real basic blocks (the foundation patterns every flat-pattern course
teaches): a straight skirt (front/back), a basic bodice (front/back) and a basic
one-piece sleeve. Darts are kept as internal features (the wedge is folded, not
cut), waist/neck/armhole use proper curves, and notches + grain lines are added —
so the output is a recognisable, sewable test garment rather than a synthetic
parametric shape.

The straight skirt is a faithful basic block; the bodice and sleeve are
*simplified* basic drafts (clean and plausible, but not graded production blocks).
All dimensions derive from the body measurements in drafting.Measurements.
"""
from __future__ import annotations

import math

from drafting import Measurements, Piece, cubic_bezier


def _dedup(pts, eps=1e-6):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append((float(p[0]), float(p[1])))
    return out


def _waist_dart(center_x, intake, length, y=0.0, down=True):
    """Internal dart V (two legs to a point) and the two notch marks at the waist."""
    s = -1.0 if down else 1.0
    half = intake / 2.0
    left = (center_x - half, y)
    right = (center_x + half, y)
    tip = (center_x, y + s * length)
    legs = [left, tip, right]
    notches = [(left[0], left[1], 0.0, s), (right[0], right[1], 0.0, s)]
    return legs, notches


# --------------------------------------------------------------------------- #
# straight skirt (basic block)
# --------------------------------------------------------------------------- #
def _skirt(m: Measurements, *, back: bool) -> Piece:
    H4 = m.hip / 4.0
    W4 = m.waist / 4.0
    d = m.hip_depth
    L = m.skirt_length
    R = H4 - W4                                   # waist suppression for this quarter
    if back:
        side_take, dart_take, dart_len = 0.40 * R, 0.60 * R, 14.0
        name = "skirt_back"
    else:
        side_take, dart_take, dart_len = 0.50 * R, 0.50 * R, 10.0
        name = "skirt_front"

    side_waist_x = H4 - side_take
    hip_x = H4

    # boundary (CCW): CF/CB waist -> waist edge -> side curve -> side straight -> hem -> centre
    side_curve = cubic_bezier((side_waist_x, 0.0),
                              (side_waist_x + 0.3, -d * 0.45),
                              (hip_x, -d * 0.72),
                              (hip_x, -d), n=14)
    boundary = _dedup(
        [(0.0, 0.0), (side_waist_x, 0.0)]
        + side_curve
        + [(hip_x, -L), (0.0, -L)]
    )

    dart_center = side_waist_x * (0.55 if back else 0.50)
    legs, notches = _waist_dart(dart_center, dart_take, dart_len)
    notches.append((hip_x, -d, -1.0, 0.0))        # balance notch at hip on side seam

    p = Piece(name=name, size=m.size, boundary=boundary, internals=[legs],
              notches=notches,
              grain=((side_waist_x * 0.45, -5.0), (side_waist_x * 0.45, -(L - 5.0))),
              label_pos=(side_waist_x * 0.35, -L * 0.5))
    return p


def skirt_front(m): return _skirt(m, back=False)
def skirt_back(m): return _skirt(m, back=True)


# --------------------------------------------------------------------------- #
# basic bodice (simplified)
# --------------------------------------------------------------------------- #
def _bodice(m: Measurements, *, back: bool) -> Piece:
    BL = m.nape_to_waist
    scye = m.armscye_depth
    chest_y = BL - scye
    neck_w = m.back_neck_width + (0.3 if not back else 0.0)
    neck_drop = 1.0 if back else (neck_w + 1.0)        # front neck is deeper
    shoulder_slope = 4.0
    dx = math.sqrt(max(m.shoulder**2 - shoulder_slope**2, 1.0))
    across = (m.bust / 4.0) - (1.5 if back else 0.0)   # chest-line half width
    waist_side_x = across - 1.5
    name = "bodice_back" if back else "bodice_front"

    centre_neck = (0.0, BL)
    neck_pt = (neck_w, BL - neck_drop)
    neckline = cubic_bezier(centre_neck,
                            (neck_w * 0.5, BL - neck_drop * 0.15),
                            (neck_w, BL - neck_drop * 0.55),
                            neck_pt, n=12)
    shoulder_tip = (neck_w + dx, BL - neck_drop - shoulder_slope)
    underarm = (across, chest_y)
    armhole = cubic_bezier(shoulder_tip,
                           (shoulder_tip[0] + 1.0, (shoulder_tip[1] + chest_y) * 0.5),
                           (across + 1.2, chest_y + scye * 0.30),
                           underarm, n=14)
    side = [(across, chest_y), (waist_side_x, 0.0)]

    boundary = _dedup(
        [(0.0, 0.0), centre_neck]
        + neckline + armhole + side
    )

    # waist dart
    dart_take = max(waist_side_x - (m.waist / 4.0), 1.2)
    dpos = across * (0.5 if back else 0.45)
    dlen = (BL - chest_y) + (3.0 if back else 0.0)
    legs, notches = _waist_dart(dpos, dart_take, min(dlen, BL - 2), down=False)
    notches.append((underarm[0], underarm[1], -1.0, 0.0))   # underarm balance notch

    p = Piece(name=name, size=m.size, boundary=boundary, internals=[legs],
              notches=notches,
              grain=((1.5, 3.0), (1.5, BL - 3.0)),
              label_pos=(across * 0.35, BL * 0.45))
    return p


def bodice_front(m): return _bodice(m, back=False)
def bodice_back(m): return _bodice(m, back=True)


# --------------------------------------------------------------------------- #
# basic one-piece sleeve (simplified)
# --------------------------------------------------------------------------- #
def sleeve(m: Measurements) -> Piece:
    SL = m.sleeve_length
    cap = m.armscye_depth * 0.72
    hw = (m.bicep + 4.0) / 2.0                      # half bicep width (+ease)
    wrist_h = max(m.bicep * 0.5, 9.0) / 1.0 / 2.0 + 4.0
    biceps_y = SL - cap

    left_u = (-hw, biceps_y)
    right_u = (hw, biceps_y)
    top = (0.0, SL)
    # sleeve cap: back half (left, fuller) + front half (right, shallower)
    back_cap = cubic_bezier(left_u, (-hw * 0.5, biceps_y + cap * 0.95),
                            (-hw * 0.2, SL), top, n=12)
    front_cap = cubic_bezier(top, (hw * 0.25, SL),
                             (hw * 0.6, biceps_y + cap * 0.75), right_u, n=12)

    boundary = _dedup(
        [(-wrist_h, 0.0), left_u] + back_cap[1:] + front_cap[1:]
        + [right_u, (wrist_h, 0.0)]
    )

    # cap balance notches: single front (right), double back (left)
    notches = [
        (hw * 0.55, biceps_y + cap * 0.45, -0.4, 0.9),
        (-hw * 0.45, biceps_y + cap * 0.55, 0.4, 0.9),
        (-hw * 0.60, biceps_y + cap * 0.40, 0.4, 0.9),
        (0.0, SL, 0.0, -1.0),                       # crown notch
    ]
    p = Piece(name="sleeve", size=m.size, boundary=boundary, internals=[],
              notches=notches,
              grain=((0.0, 3.0), (0.0, SL - 3.0)),
              label_pos=(-hw * 0.2, SL * 0.4))
    return p


ALL_BLOCKS = {
    "skirt_front": skirt_front,
    "skirt_back": skirt_back,
    "bodice_front": bodice_front,
    "bodice_back": bodice_back,
    "sleeve": sleeve,
}
