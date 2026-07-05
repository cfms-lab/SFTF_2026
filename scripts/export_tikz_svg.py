r"""Export the standalone TikZ diagrams embedded in SFTF_draft_eng.tex to SVG.

The paper's conceptual diagrams (fig:flow-geometry, fig:unified-flow,
fig:overhang-coeff, fig:spherical-sampling, fig:basin-nms) are pure TikZ, i.e.
true vector graphics. Each ``tikzpicture`` is wrapped in a ``standalone``
document built with the native pgf dvisvgm driver
(``\def\pgfsysdriver{pgfsys-dvisvgm.def}``), compiled with ``latex`` to DVI
(auto-cropped to the picture), and converted with ``dvisvgm`` in DVI mode. This
is the canonical TikZ->SVG route: dvisvgm consumes the driver's native specials
directly, so hatch patterns, brace decorations, and clips convert cleanly --
unlike the earlier ``dvisvgm --pdf`` PDF-parsing path, which mangled some
figures. Glyphs are flattened to paths (``--no-fonts``) so the SVGs render
identically everywhere and stay editable as shapes in Inkscape/Illustrator.

Output: draft/pics/tikz_<label>.svg

Run:  python scripts/export_tikz_svg.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRAFT = PROJECT_ROOT / "draft"
SRC = DRAFT / "SFTF_draft_eng.tex"
OUT_DIR = DRAFT / "pics"
BUILD = DRAFT / "_tikz_build"

PREAMBLE = r"""\documentclass[border=3pt]{standalone}
\def\pgfsysdriver{pgfsys-dvisvgm.def}
\usepackage{amsmath,amssymb,amsfonts,bm}
\usepackage{tikz}
\usetikzlibrary{arrows.meta, calc, positioning, decorations.pathreplacing, patterns, shapes.geometric}
\begin{document}
%s
\end{document}
"""

# A tikzpicture block, with the figure \label that follows it (used for naming).
BLOCK_RE = re.compile(
    r"(\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}).*?\\label\{fig:([^}]+)\}",
    re.DOTALL,
)

# Output file stems keyed by the figure label, following the Fig<N>_ convention.
NAME_MAP = {
    "flow-geometry": "Fig1_flow-geometry",
    "unified-flow": "Fig2_unified-flow",
    "overhang-coeff": "Fig3_overhang-coeff",
    "spherical-sampling": "Fig4_spherical-sampling",
    "basin-nms": "Fig5_basin",
}


def run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"--- stdout tail ---\n{proc.stdout[-1500:]}\n"
            f"--- stderr tail ---\n{proc.stderr[-800:]}"
        )


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    blocks = BLOCK_RE.findall(text)
    if not blocks:
        raise SystemExit("no tikzpicture blocks found")

    BUILD.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for picture, label in blocks:
        name = NAME_MAP.get(label, f"tikz_{label}")
        tex_path = BUILD / f"{name}.tex"
        tex_path.write_text(PREAMBLE % picture, encoding="utf-8")
        run(
            ["latex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
            cwd=BUILD,
        )
        svg_out = OUT_DIR / f"{name}.svg"
        run(
            ["dvisvgm", "--no-fonts", f"--output={svg_out}", f"{name}.dvi"],
            cwd=BUILD,
        )
        print(f"wrote {svg_out.relative_to(PROJECT_ROOT)}")

    shutil.rmtree(BUILD, ignore_errors=True)


if __name__ == "__main__":
    main()
