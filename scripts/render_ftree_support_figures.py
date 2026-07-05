"""Render the FTree4x STL support-flow schematic.

The script uses only the Python standard library. It parses the ASCII STL,
projects the actual mesh triangles into TikZ, highlights representative
face-to-face and build-plate support cases, and exports TeX/PDF/SVG/PNG files.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "draft"
PICS = DRAFT / "pics"
STL = PICS / "FTree4x.stl"

SRC_FACE_TO_FACE = 8
RECEIVER_FACE = 6
SRC_TO_PLATE = 27
OUTPUT_STEM = "FTree4x_fig1_unified_flow"


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def norm(a):
    return math.sqrt(dot(a, a))


def centroid(tri):
    return tuple(sum(v[i] for v in tri) / 3.0 for i in range(3))


def normal(tri):
    cr = cross(sub(tri[1], tri[0]), sub(tri[2], tri[0]))
    length = norm(cr)
    return tuple(x / length for x in cr) if length else (0.0, 0.0, 0.0)


def load_ascii_stl(path: Path):
    tris = []
    cur = []
    for line in path.read_text(errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) >= 4 and parts[0] == "vertex":
            cur.append(tuple(float(x) for x in parts[1:4]))
        elif parts and parts[0] == "endfacet":
            if len(cur) == 3:
                tris.append(tuple(cur))
            cur = []
    if not tris:
        raise RuntimeError(f"No triangles parsed from {path}")
    return tris


def rotate_about_build_axis_180(tris):
    """Rotate the mesh 180 degrees around the build direction n (+Z).

    The axis passes through the XY center of the STL bounding box. This changes
    the viewing side while preserving the build direction and all vertical
    support relationships.
    """
    verts = [v for tri in tris for v in tri]
    cx = (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2.0
    cy = (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2.0

    def rot(p):
        x, y, z = p
        return (2.0 * cx - x, 2.0 * cy - y, z)

    return [tuple(rot(v) for v in tri) for tri in tris]


def fmt(n: float) -> str:
    return f"{n:.3f}"


def make_projector(tris):
    verts = [v for tri in tris for v in tri]
    cx = (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2.0
    cy = (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2.0
    s = 0.060

    def raw(p):
        x, y, z = p
        return (
            s * ((x - cx) + 0.36 * (y - cy)),
            s * (z - 0.22 * (y - cy)),
        )

    projected = [raw(v) for v in verts]
    y_min = min(p[1] for p in projected)

    def project(p):
        x, y = raw(p)
        return (x, y - y_min + 0.25)

    return project


def coord(project, p, shift_x=0.0):
    x, y = project(p)
    return f"({fmt(x + shift_x)},{fmt(y)})"


def triangle_path(project, tri, shift_x=0.0):
    return " -- ".join(coord(project, p, shift_x) for p in tri) + " -- cycle"


def triangle_style(tri, highlight=None):
    if highlight == "source":
        return "srcface"
    if highlight == "receiver":
        return "recface"
    nz = normal(tri)[2]
    if nz > 0.7:
        return "meshup"
    if nz < -0.7:
        return "meshdown"
    return "meshside"


def draw_mesh(project, tris, shift_x=0.0, highlights=None):
    highlights = highlights or {}
    lines = []
    ordered = sorted(enumerate(tris), key=lambda item: sum(v[1] for v in item[1]) / 3.0)
    for idx, tri in ordered:
        style = triangle_style(tri, highlights.get(idx))
        lines.append(f"\\filldraw[{style}] {triangle_path(project, tri, shift_x)};")
    return "\n".join(lines)


def draw_plate(project, tris, shift_x=0.0):
    verts = [v for tri in tris for v in tri]
    xmin, xmax = min(v[0] for v in verts) - 7.0, max(v[0] for v in verts) + 7.0
    ymin, ymax = min(v[1] for v in verts) - 8.0, max(v[1] for v in verts) + 8.0
    plate = [(xmin, ymin, 0.0), (xmax, ymin, 0.0), (xmax, ymax, 0.0), (xmin, ymax, 0.0)]
    return f"\\filldraw[plate] {triangle_path(project, plate, shift_x)};"


def draw_build_axis(project, tris, shift_x=0.0, label="$n$"):
    verts = [v for tri in tris for v in tri]
    start = (min(v[0] for v in verts) - 12.0, min(v[1] for v in verts) - 4.0, 52.0)
    end = (start[0], start[1], 82.0)
    return (
        f"\\draw[axis] {coord(project, start, shift_x)} -- {coord(project, end, shift_x)} "
        f"node[above,inner sep=1pt]{{{label}}};"
    )


def draw_face_to_face(project, tris, shift_x=0.0, compact=False):
    src = tris[SRC_FACE_TO_FACE]
    rec = tris[RECEIVER_FACE]
    ci = centroid(src)
    cj = centroid(rec)
    mi0 = ci
    mi1 = (ci[0], ci[1], ci[2] - 11.0)
    mj0 = cj
    mj1 = (cj[0], cj[1], cj[2] + 11.0)
    label_y = ci[2] + (22.0 if compact else 14.0)
    label_x = ci[0] + (22.0 if compact else 24.0)
    lines = [
        f"\\draw[ray] {coord(project, (ci[0], ci[1], ci[2] - 1.5), shift_x)} -- "
        f"{coord(project, (cj[0], cj[1], cj[2] + 4.0), shift_x)} "
        "node[midway,right=14pt,yshift=-8pt]{$-n$};",
        f"\\draw[normSrc] {coord(project, mi0, shift_x)} -- {coord(project, mi1, shift_x)} "
        "node[right=1pt]{$m_i$};",
        f"\\draw[normRec] {coord(project, mj0, shift_x)} -- {coord(project, mj1, shift_x)} "
        "node[left=1pt]{$m_j$};",
        f"\\fill[srcDot] {coord(project, ci, shift_x)} circle (1.25pt);",
        f"\\fill[recDot] {coord(project, cj, shift_x)} circle (1.25pt);",
        f"\\draw[measure] {coord(project, (ci[0] + 30.0, ci[1], ci[2]), shift_x)} -- "
        f"{coord(project, (cj[0] + 30.0, cj[1], cj[2]), shift_x)} "
        "node[midway,right=2pt]{$h_{ij}$};",
    ]
    if compact:
        lines.append(
            f"\\node[termLabel] at {coord(project, (ci[0] + 31.0, ci[1], ci[2] + 31.0), shift_x)} "
            "{$m_i m_j^T$};"
        )
    return "\n".join(lines)


def draw_ground_case(project, tris, shift_x=0.0):
    src = tris[SRC_TO_PLATE]
    ci = centroid(src)
    gp = (ci[0], ci[1], 0.0)
    lines = [
        f"\\draw[ray] {coord(project, (ci[0], ci[1], ci[2] - 2.0), shift_x)} -- "
        f"{coord(project, (gp[0], gp[1], gp[2] + 3.0), shift_x)} "
        "node[midway,left=2pt]{$-n$};",
        f"\\draw[normSrc] {coord(project, ci, shift_x)} -- {coord(project, (ci[0], ci[1], ci[2] - 11.0), shift_x)} "
        "node[right=1pt]{$m_i$};",
        f"\\fill[srcDot] {coord(project, ci, shift_x)} circle (1.25pt);",
        f"\\fill[groundDot] {coord(project, gp, shift_x)} circle (1.45pt);",
        f"\\draw[normRec] {coord(project, gp, shift_x)} -- {coord(project, (gp[0], gp[1], gp[2] + 13.0), shift_x)} "
        "node[right=1pt]{$n$};",
        f"\\draw[measure] {coord(project, (ci[0] - 22.0, ci[1], ci[2]), shift_x)} -- "
        f"{coord(project, (gp[0] - 22.0, gp[1], gp[2]), shift_x)} "
        "node[midway,left=2pt]{$h_{iP}$};",
        f"\\node[termLabel] at {coord(project, (ci[0] + 23.0, ci[1], ci[2] + 31.0), shift_x)} "
        "{$m_i n^T$};",
    ]
    return "\n".join(lines)


def document(body: str) -> str:
    return rf"""\documentclass[tikz,border=3pt]{{standalone}}
\usepackage{{amsmath}}
\usetikzlibrary{{arrows.meta,patterns,decorations.pathreplacing}}
\definecolor{{ohred}}{{HTML}}{{B23B2E}}
\definecolor{{rcblue}}{{HTML}}{{2F5FA6}}
\tikzset{{
  meshup/.style={{fill=black!18, fill opacity=0.22, draw=black!35, draw opacity=0.45, line width=0.22pt}},
  meshdown/.style={{fill=black!28, fill opacity=0.22, draw=black!38, draw opacity=0.45, line width=0.22pt}},
  meshside/.style={{fill=black!10, fill opacity=0.18, draw=black!32, draw opacity=0.45, line width=0.22pt}},
  srcface/.style={{fill=ohred!45, fill opacity=0.72, draw=ohred!85!black, draw opacity=0.96, line width=0.9pt}},
  recface/.style={{fill=rcblue!42, fill opacity=0.72, draw=rcblue!85!black, draw opacity=0.96, line width=0.9pt}},
  plate/.style={{fill=black!4, fill opacity=0.22, draw=black!35, draw opacity=0.55, line width=0.5pt, pattern=north east lines, pattern color=black!25}},
  ray/.style={{->, >=Latex, dash pattern=on 2.2pt off 2.2pt, line width=1.0pt, black!70}},
  axis/.style={{->, >=Latex, line width=1.2pt, black!70}},
  normSrc/.style={{->, >=Latex, line width=1.1pt, ohred!80!black}},
  normRec/.style={{->, >=Latex, line width=1.1pt, rcblue!82!black}},
  measure/.style={{<->, >=Latex, line width=0.65pt, black!55}},
  srcDot/.style={{ohred!80!black}},
  recDot/.style={{rcblue!82!black}},
  groundDot/.style={{rcblue!82!black}},
  termLabel/.style={{font=\small\bfseries, text=black!80, align=center}},
  panelLabel/.style={{font=\bfseries, text=black!80}},
}}
\begin{{document}}
\begin{{tikzpicture}}[line join=round,line cap=round]
{body}
\end{{tikzpicture}}
\end{{document}}
"""


def write_and_compile(name: str, tex: str):
    tex_path = PICS / f"{name}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=PICS,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-2000:])
    pdf = PICS / f"{name}.pdf"
    subprocess.run(["pdftocairo", "-svg", pdf.name, f"{name}.svg"], cwd=PICS, check=False)
    subprocess.run(["pdftocairo", "-png", "-r", "300", "-singlefile", pdf.name, name], cwd=PICS, check=False)
    for suffix in [".aux", ".log"]:
        (PICS / f"{name}{suffix}").unlink(missing_ok=True)
    return tex_path, pdf, PICS / f"{name}.svg", PICS / f"{name}.png"


def main():
    tris = rotate_about_build_axis_180(load_ascii_stl(STL))
    project = make_projector(tris)

    body = "\n".join(
        [
            "\\begin{scope}",
            "\\node[panelLabel] at (-2.8,6.7) {(a)};",
            draw_plate(project, tris),
            draw_mesh(project, tris, highlights={SRC_FACE_TO_FACE: "source", RECEIVER_FACE: "receiver"}),
            draw_face_to_face(project, tris, compact=True),
            draw_build_axis(project, tris),
            "\\end{scope}",
            "\\begin{scope}[xshift=8.0cm]",
            "\\node[panelLabel] at (-2.8,6.7) {(b)};",
            draw_plate(project, tris),
            draw_mesh(project, tris, highlights={SRC_TO_PLATE: "source"}),
            draw_ground_case(project, tris),
            draw_build_axis(project, tris),
            "\\end{scope}",
        ]
    )

    outputs = []
    outputs.extend(write_and_compile(OUTPUT_STEM, document(body)))
    for path in outputs:
        if path.exists():
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
