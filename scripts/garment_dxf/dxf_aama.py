"""Minimal, dependency-free DXF (R12 ASCII) writer + reader for apparel patterns.

Follows the common AAMA/ASTM DXF *layer convention* used by apparel CAD
(Lectra / Gerber / Optitex / Seamly2D import these):

    layer "1"   piece boundary (cut line)        -> closed POLYLINE
    layer "8"   internal / construction (darts)  -> open POLYLINE
    layer "11"  notches                          -> short LINE
    layer "13"  grain line (with arrow heads)    -> LINE
    layer "15"  piece annotation (name/size)     -> TEXT

Units are millimetres by default (AAMA is typically mm); pass scale=1.0 to keep
the drafting units (cm) instead. Geometry is plain R12 POLYLINE/LINE/TEXT so it
opens in virtually any CAD, while the layer numbers carry the AAMA semantics.

The tiny reader (read_dxf) pulls POLYLINE/LINE/TEXT back out with their layers —
used to round-trip-validate and preview generated files.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# AAMA-DXF layer names (strings, per convention)
LAYER_BOUNDARY = "1"
LAYER_INTERNAL = "8"
LAYER_NOTCH = "11"
LAYER_GRAIN = "13"
LAYER_TEXT = "15"
_LAYERS = [(LAYER_BOUNDARY, 7), (LAYER_INTERNAL, 3), (LAYER_NOTCH, 1),
           (LAYER_GRAIN, 5), (LAYER_TEXT, 2)]


def _g(code, value) -> str:
    """One DXF group: code line + value line."""
    return f"{code}\n{value}\n"


class DxfWriter:
    """Accumulate entities, then `.tostring()` / `.save()` a valid R12 DXF."""

    def __init__(self, scale: float = 10.0):
        self.scale = scale            # cm -> mm by default
        self._ents: list[str] = []

    # -- entities ----------------------------------------------------------- #
    def polyline(self, pts, layer: str, closed: bool = False) -> None:
        s = self.scale
        body = _g(0, "POLYLINE") + _g(8, layer) + _g(66, 1) + _g(70, 1 if closed else 0)
        for x, y in pts:
            body += _g(0, "VERTEX") + _g(8, layer)
            body += _g(10, f"{x*s:.4f}") + _g(20, f"{y*s:.4f}") + _g(30, "0.0")
        body += _g(0, "SEQEND")
        self._ents.append(body)

    def line(self, p1, p2, layer: str) -> None:
        s = self.scale
        self._ents.append(
            _g(0, "LINE") + _g(8, layer)
            + _g(10, f"{p1[0]*s:.4f}") + _g(20, f"{p1[1]*s:.4f}") + _g(30, "0.0")
            + _g(11, f"{p2[0]*s:.4f}") + _g(21, f"{p2[1]*s:.4f}") + _g(31, "0.0")
        )

    def text(self, pos, string: str, layer: str, height: float = 10.0) -> None:
        s = self.scale
        self._ents.append(
            _g(0, "TEXT") + _g(8, layer)
            + _g(10, f"{pos[0]*s:.4f}") + _g(20, f"{pos[1]*s:.4f}") + _g(30, "0.0")
            + _g(40, f"{height:.4f}") + _g(1, string)
        )

    def grainline(self, p1, p2, layer: str = LAYER_GRAIN) -> None:
        """A grain line drawn as a shaft + two arrow heads (apparel convention)."""
        import math
        self.line(p1, p2, layer)
        for tip, other in ((p2, p1), (p1, p2)):
            ang = math.atan2(other[1] - tip[1], other[0] - tip[0])
            a = 2.0  # arrow length in drafting units (cm)
            for da in (-0.4, 0.4):
                hx = tip[0] + a * math.cos(ang + da)
                hy = tip[1] + a * math.sin(ang + da)
                self.line(tip, (hx, hy), layer)

    # -- assemble ----------------------------------------------------------- #
    def tostring(self) -> str:
        tables = _g(0, "SECTION") + _g(2, "TABLES") + _g(0, "TABLE") + _g(2, "LAYER") \
            + _g(70, len(_LAYERS))
        for name, color in _LAYERS:
            tables += _g(0, "LAYER") + _g(2, name) + _g(70, 0) + _g(62, color) \
                + _g(6, "CONTINUOUS")
        tables += _g(0, "ENDTAB") + _g(0, "ENDSEC")

        header = _g(0, "SECTION") + _g(2, "HEADER") \
            + _g(9, "$INSUNITS") + _g(70, 4 if self.scale == 10.0 else 5) \
            + _g(0, "ENDSEC")            # 4 = mm, 5 = cm

        entities = _g(0, "SECTION") + _g(2, "ENTITIES")
        entities += "".join(self._ents)
        entities += _g(0, "ENDSEC")

        return header + tables + entities + _g(0, "EOF")

    def save(self, path: str) -> None:
        with open(path, "w", encoding="ascii", errors="replace") as f:
            f.write(self.tostring())


# --------------------------------------------------------------------------- #
# tiny reader (POLYLINE / LINE / TEXT) for round-trip checks & preview
# --------------------------------------------------------------------------- #
@dataclass
class ReadResult:
    polylines: list = field(default_factory=list)   # (layer, [(x,y),...], closed)
    lines: list = field(default_factory=list)       # (layer, (x1,y1),(x2,y2))
    texts: list = field(default_factory=list)       # (layer, (x,y), string)


def read_dxf(path: str) -> ReadResult:
    with open(path, "r", encoding="ascii", errors="replace") as f:
        toks = [ln.rstrip("\n") for ln in f]
    res = ReadResult()
    i = 0
    n = len(toks)

    def pairs(start):
        # yield (code:int, value:str) from start, stepping by 2
        k = start
        while k + 1 < n:
            yield k, int(toks[k]), toks[k + 1]
            k += 2

    while i + 1 < n:
        code, val = toks[i], toks[i + 1]
        if code == "0" and val == "POLYLINE":
            layer, verts, closed = "0", [], False
            j = i + 2
            # read header groups until first VERTEX/SEQEND
            while j + 1 < n and not (toks[j] == "0" and toks[j + 1] in ("VERTEX", "SEQEND")):
                if toks[j] == "8":
                    layer = toks[j + 1]
                elif toks[j] == "70":
                    closed = bool(int(toks[j + 1]) & 1)
                j += 2
            # read vertices
            while j + 1 < n and toks[j] == "0" and toks[j + 1] == "VERTEX":
                x = y = 0.0
                k = j + 2
                while k + 1 < n and toks[k] != "0":
                    if toks[k] == "10":
                        x = float(toks[k + 1])
                    elif toks[k] == "20":
                        y = float(toks[k + 1])
                    k += 2
                verts.append((x, y))
                j = k
            res.polylines.append((layer, verts, closed))
            i = j
            continue
        if code == "0" and val == "LINE":
            layer = "0"; x1 = y1 = x2 = y2 = 0.0
            k = i + 2
            while k + 1 < n and toks[k] != "0":
                c, v = toks[k], toks[k + 1]
                if c == "8": layer = v
                elif c == "10": x1 = float(v)
                elif c == "20": y1 = float(v)
                elif c == "11": x2 = float(v)
                elif c == "21": y2 = float(v)
                k += 2
            res.lines.append((layer, (x1, y1), (x2, y2)))
            i = k
            continue
        if code == "0" and val == "TEXT":
            layer = "0"; x = y = 0.0; s = ""
            k = i + 2
            while k + 1 < n and toks[k] != "0":
                c, v = toks[k], toks[k + 1]
                if c == "8": layer = v
                elif c == "10": x = float(v)
                elif c == "20": y = float(v)
                elif c == "1": s = v
                k += 2
            res.texts.append((layer, (x, y), s))
            i = k
            continue
        i += 2
    return res
