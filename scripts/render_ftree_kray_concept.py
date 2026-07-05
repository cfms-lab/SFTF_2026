"""Render a vector schematic explaining K_ray on the FTree4x mesh.

The figure is intentionally standalone: it writes a PDF/SVG/PNG into draft/pics
but does not modify any LaTeX manuscript.

Run:  .venv\\Scripts\\python.exe scripts\\render_ftree_kray_concept.py
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PICS = ROOT / "draft" / "pics"
STL = ROOT / "Experimental" / "etc" / "FTree4x.stl"
OUTPUT_STEM = "FTree4x_kray_concept"

FACE_FRACTION = 0.02
MIN_RAY_COUNT = 500
MAX_RAY_COUNT = 3000
BUILD_DIRECTION = (0.0, 0.0, 1.0)


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


def area(tri):
    return 0.5 * norm(cross(sub(tri[1], tri[0]), sub(tri[2], tri[0])))


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
    verts = [v for tri in tris for v in tri]
    cx = (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2.0
    cy = (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2.0

    def rot(p):
        x, y, z = p
        return (2.0 * cx - x, 2.0 * cy - y, z)

    return [tuple(rot(v) for v in tri) for tri in tris]


def fmt(n: float) -> str:
    return f"{n:.3f}"


def adaptive_k_ray(face_count: int) -> int:
    by_fraction = math.ceil(max(face_count, 1) * FACE_FRACTION)
    return min(max(by_fraction, MIN_RAY_COUNT), MAX_RAY_COUNT)


def overhang_weight(tri) -> float:
    ni = normal(tri)
    overhang = max(0.0, -dot(ni, BUILD_DIRECTION))
    return area(tri) * overhang


def make_projector(tris):
    verts = [v for tri in tris for v in tri]
    cx = (min(v[0] for v in verts) + max(v[0] for v in verts)) / 2.0
    cy = (min(v[1] for v in verts) + max(v[1] for v in verts)) / 2.0
    s = 0.058

    def raw(p):
        x, y, z = p
        return (
            s * ((x - cx) + 0.34 * (y - cy)),
            s * (z - 0.24 * (y - cy)),
        )

    projected = [raw(v) for v in verts]
    y_min = min(p[1] for p in projected)

    def project(p):
        x, y = raw(p)
        return (x, y - y_min + 0.25)

    return project


def coord(project, p, shift_x=0.0, shift_y=0.0):
    x, y = project(p)
    return f"({fmt(x + shift_x)},{fmt(y + shift_y)})"


def triangle_path(project, tri, shift_x=0.0):
    return " -- ".join(coord(project, p, shift_x) for p in tri) + " -- cycle"


def triangle_style(tri, selected: bool) -> str:
    if selected:
        return "selectedface"
    nz = normal(tri)[2]
    if nz > 0.7:
        return "meshup"
    if nz < -0.7:
        return "meshdown"
    return "meshside"


def draw_mesh(project, tris, selected_ids):
    lines = []
    selected = set(selected_ids)
    ordered = sorted(enumerate(tris), key=lambda item: sum(v[1] for v in item[1]) / 3.0)
    for idx, tri in ordered:
        lines.append(f"\\filldraw[{triangle_style(tri, idx in selected)}] {triangle_path(project, tri)};")
    return "\n".join(lines)


def draw_plate(project, tris):
    verts = [v for tri in tris for v in tri]
    xmin, xmax = min(v[0] for v in verts) - 7.0, max(v[0] for v in verts) + 7.0
    ymin, ymax = min(v[1] for v in verts) - 8.0, max(v[1] for v in verts) + 8.0
    plate = [(xmin, ymin, 0.0), (xmax, ymin, 0.0), (xmax, ymax, 0.0), (xmin, ymax, 0.0)]
    return f"\\filldraw[plate] {triangle_path(project, plate)};"


def draw_build_axis(project, tris):
    verts = [v for tri in tris for v in tri]
    start = (min(v[0] for v in verts) - 12.0, min(v[1] for v in verts) - 4.0, 52.0)
    end = (start[0], start[1], 82.0)
    return (
        f"\\draw[axis] {coord(project, start)} -- {coord(project, end)} "
        "node[above,inner sep=1pt]{$n$};"
    )


def draw_rays(project, tris, selected_ids):
    lines = []
    for idx in selected_ids:
        c = centroid(tris[idx])
        end = (c[0], c[1], max(0.0, c[2] - 28.0))
        lines.append(
            f"\\draw[sampleray] {coord(project, (c[0], c[1], c[2] - 1.0))} -- {coord(project, end)};"
        )
        lines.append(f"\\fill[srcdot] {coord(project, c)} circle (0.9pt);")
    return "\n".join(lines)


def draw_formula_panel(face_count: int, valid_count: int, selected_count: int, k_ray: int) -> str:
    raw = FACE_FRACTION * face_count
    return rf"""
\begin{{scope}}[xshift=7.35cm]
\node[paneltitle,anchor=west] at (0,6.35) {{Ray budget on FTree4x}};
\node[formulabox,anchor=west] at (0,5.55) {{$K_{{ray}}=\mathrm{{clip}}(0.02N_f,500,3000)$}};
\node[textblock,anchor=west] at (0,4.72) {{$N_f={face_count}$,\quad $0.02N_f={raw:.1f}$}};
\node[textblock,anchor=west] at (0,4.22) {{$K_{{ray}}=\mathrm{{clip}}({raw:.1f},500,3000)={k_ray}$}};
\node[textblock,anchor=west] at (0,3.72) {{weighted source pool: $A_iO_i(n)>0$}};
\node[textblock,anchor=west] at (0,3.22) {{$N_{{src}}={valid_count}<K_{{ray}}$}};
\node[resultbox,anchor=west] at (0,2.48) {{selected ray sources: ${selected_count}$ faces}};

\draw[barbase] (0,1.48) -- (5.7,1.48);
\draw[barsegA] (0,1.48) -- (1.88,1.48);
\draw[barsegB] (1.88,1.48) -- (4.08,1.48);
\draw[barsegC] (4.08,1.48) -- (5.7,1.48);
\draw[tick] (0,1.34) -- (0,1.62) node[below=5pt] {{0}};
\draw[tick] (1.88,1.34) -- (1.88,1.62) node[below=5pt] {{$25k$}};
\draw[tick] (4.08,1.34) -- (4.08,1.62) node[below=5pt] {{$150k$}};
\draw[tick] (5.7,1.34) -- (5.7,1.62);
\node[smalltext,anchor=west] at (0,0.72) {{small meshes: minimum $500$ protects stability}};
\node[smalltext,anchor=west] at (0,0.22) {{medium meshes: sample about $2\%$ of faces}};
\node[smalltext,anchor=west] at (0,-0.28) {{large meshes: cap $3000$ keeps runtime bounded}};

\node[notebox,anchor=north west,text width=5.95cm] at (0,-0.86)
{{For this small didactic mesh, the lower bound exceeds the overhang source pool, so no subsampling occurs: every weighted source face is ray-cast.}};
\end{{scope}}
"""


def document(body: str) -> str:
    return rf"""\documentclass[tikz,border=3pt]{{standalone}}
\usepackage{{amsmath}}
\usetikzlibrary{{arrows.meta,patterns,positioning}}
\definecolor{{ohred}}{{HTML}}{{B23B2E}}
\definecolor{{rcblue}}{{HTML}}{{2F5FA6}}
\definecolor{{warm}}{{HTML}}{{E68A2E}}
\tikzset{{
  meshup/.style={{fill=black!16, fill opacity=0.20, draw=black!34, draw opacity=0.44, line width=0.22pt}},
  meshdown/.style={{fill=black!26, fill opacity=0.20, draw=black!36, draw opacity=0.44, line width=0.22pt}},
  meshside/.style={{fill=black!9, fill opacity=0.17, draw=black!30, draw opacity=0.42, line width=0.22pt}},
  selectedface/.style={{fill=ohred!52, fill opacity=0.78, draw=ohred!88!black, draw opacity=0.96, line width=0.75pt}},
  plate/.style={{fill=black!4, fill opacity=0.22, draw=black!35, draw opacity=0.55, line width=0.5pt, pattern=north east lines, pattern color=black!25}},
  sampleray/.style={{->, >=Latex, dash pattern=on 2.2pt off 2.2pt, line width=0.95pt, ohred!82!black}},
  axis/.style={{->, >=Latex, line width=1.15pt, black!70}},
  srcdot/.style={{ohred!85!black}},
  paneltitle/.style={{font=\bfseries\large, text=black!82}},
  meshlabel/.style={{font=\bfseries, text=black!82}},
  formulabox/.style={{draw=black!35, fill=black!3, rounded corners=2pt, inner xsep=7pt, inner ysep=5pt, font=\large}},
  resultbox/.style={{draw=ohred!70!black, fill=ohred!8, rounded corners=2pt, inner xsep=7pt, inner ysep=5pt, font=\bfseries}},
  textblock/.style={{font=\normalsize, text=black!82}},
  smalltext/.style={{font=\small, text=black!72}},
  notebox/.style={{font=\small, text=black!72, align=left, draw=black!18, fill=black!2, rounded corners=2pt, inner xsep=5pt, inner ysep=4pt}},
  barbase/.style={{line width=5.5pt, black!15}},
  barsegA/.style={{line width=5.5pt, rcblue!75}},
  barsegB/.style={{line width=5.5pt, warm!85}},
  barsegC/.style={{line width=5.5pt, ohred!76}},
  tick/.style={{line width=0.55pt, black!55}},
}}
\begin{{document}}
\begin{{tikzpicture}}[line join=round,line cap=round]
{body}
\end{{tikzpicture}}
\end{{document}}
"""


def write_and_compile(tex: str):
    PICS.mkdir(parents=True, exist_ok=True)
    tex_path = PICS / f"{OUTPUT_STEM}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=PICS,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-2500:])
    pdf = PICS / f"{OUTPUT_STEM}.pdf"
    subprocess.run(["pdftocairo", "-svg", pdf.name, f"{OUTPUT_STEM}.svg"], cwd=PICS, check=False)
    subprocess.run(["pdftocairo", "-png", "-r", "300", "-singlefile", pdf.name, OUTPUT_STEM], cwd=PICS, check=False)
    for suffix in [".aux", ".log"]:
        (PICS / f"{OUTPUT_STEM}{suffix}").unlink(missing_ok=True)
    return tex_path, pdf, PICS / f"{OUTPUT_STEM}.svg", PICS / f"{OUTPUT_STEM}.png"


def main() -> None:
    tris = rotate_about_build_axis_180(load_ascii_stl(STL))
    weights = [overhang_weight(tri) for tri in tris]
    valid_ids = [idx for idx, weight in enumerate(weights) if weight > 0.0]
    k_ray = adaptive_k_ray(len(tris))
    selected_ids = valid_ids if len(valid_ids) <= k_ray else valid_ids[:k_ray]
    project = make_projector(tris)

    body = "\n".join(
        [
            "\\node[paneltitle,anchor=west] at (-3.2,6.35) {FTree4x source-face sampling};",
            "\\node[meshlabel,anchor=west] at (-3.2,5.82) {$A_iO_i(n)>0$ faces selected for ray casting};",
            draw_plate(project, tris),
            draw_mesh(project, tris, selected_ids),
            draw_rays(project, tris, selected_ids),
            draw_build_axis(project, tris),
            "\\node[smalltext,anchor=west] at (-3.2,-0.52) {red faces: source pool; dashed arrows: rays along $-n$};",
            draw_formula_panel(len(tris), len(valid_ids), len(selected_ids), k_ray),
        ]
    )

    for path in write_and_compile(document(body)):
        if path.exists():
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
