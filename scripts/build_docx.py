"""Build a Word .docx from the LaTeX draft with ALL figures embedded.

Pandoc alone cannot render two kinds of figures used in this draft:

  1. ``tikzpicture`` environments (the schematic diagrams) -- pandoc drops them
     entirely, so the figures simply vanish from the .docx.
  2. ``\\includegraphics`` that point at a *PDF* (e.g. the appendix contour) --
     pandoc embeds the raw .pdf as a media blob, which Word cannot display, so
     the figure shows up as a broken/blank image.

This script works around both limitations so the .docx looks like the .pdf:

  * Every ``tikzpicture`` is compiled to a standalone PNG (using the same
    preamble packages / pgfplots colormap as the main document) via pdflatex +
    pdftocairo, and the environment is replaced by an ``\\includegraphics`` of
    that PNG.
  * Every ``\\includegraphics`` whose target is a .pdf is rasterised to a PNG
    (pdftocairo) and the reference is rewritten to the .png.
  * Raster figures that already work (.png/.jpg) are left untouched.

The rewritten .tex is then handed to pandoc (with citeproc) to produce the
.docx. Generated PNGs live in ``draft/pics/_docx_auto/`` so reruns are cheap and
nothing in the original sources is mutated.

Requirements (all already present in this environment): pdflatex, pdftocairo
(poppler), pandoc.

Run:  python scripts/build_docx.py [draft/sftf_draft_byCODEX.tex]
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRAFT_DIR = PROJECT_ROOT / "draft"
DEFAULT_TEX = DRAFT_DIR / "sftf_draft_byCODEX.tex"
AUTO_DIR_NAME = "pics/_docx_auto"  # relative to draft/, referenced from the tex
BIB = "references.bib"
CSL = "3d-printing-and-additive-manufacturing.csl"
DPI = 300
LATEX_SIDECAR_SUFFIXES = (".aux", ".bbl", ".blg", ".log", ".out")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def extract_preamble(tex: str) -> str:
    """Return the package/setup preamble (between documentclass and document),
    dropping document-class-specific lines that conflict with `standalone`."""
    body = tex.split(r"\begin{document}", 1)[0]
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(r"\documentclass"):
            continue
        if stripped.startswith(r"\geometry") or "{geometry}" in stripped:
            continue
        if stripped.startswith((r"\title", r"\author", r"\date")):
            continue
        lines.append(line)
    return "\n".join(lines)


def compile_tikz_to_png(block: str, preamble: str, work: Path, out_dir: Path) -> Path | None:
    """Compile one tikzpicture block to a cropped PNG (cached by content hash).

    The PNG filename is derived from a hash of (preamble + block), so an unchanged
    figure is never recompiled -- this keeps the on-edit hook fast.
    """
    digest = hashlib.md5((preamble + "\x00" + block).encode("utf-8")).hexdigest()[:16]
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"tikz_{digest}.png"
    if png.exists():
        return png  # cache hit -- identical figure already rendered

    standalone = (
        "\\documentclass[border=4pt]{standalone}\n"
        f"{preamble}\n"
        "\\begin{document}\n"
        f"{block}\n"
        "\\end{document}\n"
    )
    src = work / f"tikz_{digest}.tex"
    src.write_text(standalone, encoding="utf-8")
    proc = run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", src.name], work)
    pdf = work / f"tikz_{digest}.pdf"
    if proc.returncode != 0 or not pdf.exists():
        log_tail = "\n".join(proc.stdout.splitlines()[-12:])
        print(f"  [warn] tikz figure failed to compile:\n{log_tail}")
        return None
    run(["pdftocairo", "-png", "-r", str(DPI), "-singlefile", str(pdf), str(png.with_suffix(""))], work)
    return png if png.exists() else None


def pdf_includegraphics_to_png(pdf_rel: str, out_dir: Path) -> str | None:
    """Rasterise a .pdf figure (path relative to draft/) to PNG; return new rel path."""
    pdf_path = DRAFT_DIR / pdf_rel
    if not pdf_path.exists():
        print(f"  [warn] includegraphics target not found: {pdf_rel}")
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    png_stem = out_dir / pdf_path.stem
    png = png_stem.with_suffix(".png")
    # cache: skip rasterising if the PNG is already newer than its source PDF
    if not (png.exists() and png.stat().st_mtime >= pdf_path.stat().st_mtime):
        run(["pdftocairo", "-png", "-r", str(DPI), "-singlefile", str(pdf_path), str(png_stem)], DRAFT_DIR)
    if not png.exists():
        print(f"  [warn] pdftocairo failed for {pdf_rel}")
        return None
    return f"{AUTO_DIR_NAME}/{png.name}"


def cleanup_latex_sidecars(tex_path: Path) -> list[Path]:
    """Remove reproducible LaTeX sidecar files next to the source document."""
    removed = []
    for suffix in LATEX_SIDECAR_SUFFIXES:
        sidecar = tex_path.with_suffix(suffix)
        if sidecar.exists():
            sidecar.unlink()
            removed.append(sidecar)
    return removed


TIKZ_RE = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.DOTALL)
INCLUDE_RE = re.compile(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}")


def build(tex_path: Path) -> Path:
    """Render figures and produce the .docx next to the .tex. Returns docx path."""
    tex_path = Path(tex_path).resolve()
    tex = tex_path.read_text(encoding="utf-8")
    preamble = extract_preamble(tex)
    out_dir = DRAFT_DIR / AUTO_DIR_NAME

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        # 1) tikzpicture -> PNG (cached by content hash)
        tikz_blocks = TIKZ_RE.findall(tex)
        print(f"rendering {len(tikz_blocks)} tikzpicture block(s) -> PNG ...")
        out_tex = tex
        for i, block in enumerate(tikz_blocks, start=1):
            png = compile_tikz_to_png(block, preamble, work, out_dir)
            if png is None:
                continue
            rel = f"{AUTO_DIR_NAME}/{png.name}"
            new_inc = f"\\includegraphics[width=0.8\\linewidth]{{{rel}}}"
            out_tex = out_tex.replace(block, new_inc, 1)
            print(f"  tikz #{i} -> {rel}")

        # 2) includegraphics{...pdf} -> PNG
        def swap_pdf(match: re.Match) -> str:
            opts, target = match.group(1) or "", match.group(2)
            if target.lower().endswith(".pdf"):
                new_rel = pdf_includegraphics_to_png(target, out_dir)
                if new_rel:
                    print(f"  pdf figure {target} -> {new_rel}")
                    return f"\\includegraphics{opts}{{{new_rel}}}"
            return match.group(0)

        out_tex = INCLUDE_RE.sub(swap_pdf, out_tex)

        # 2b) unwrap \resizebox{..}{..}{\includegraphics..} -> \includegraphics
        # (pandoc ignores \resizebox and would otherwise drop the wrapped image;
        # Word scales the picture to the page anyway).
        out_tex = re.sub(
            r"\\resizebox\{[^{}]*\}\{[^{}]*\}\{%?\s*(\\includegraphics(?:\[[^\]]*\])?\{[^}]*\})\s*\}",
            r"\1",
            out_tex,
        )

        # 3) write rewritten tex + run pandoc (from draft/ so relative paths resolve)
        docx_src = DRAFT_DIR / (tex_path.stem + ".docxsrc.tex")
        docx_src.write_text(out_tex, encoding="utf-8")
        docx_out = tex_path.stem + ".docx"
        print(f"running pandoc -> {docx_out} ...")
        proc = run(
            [
                "pandoc", docx_src.name, "-o", docx_out,
                "--citeproc", f"--bibliography={BIB}", f"--csl={CSL}",
            ],
            DRAFT_DIR,
        )
        docx_src.unlink(missing_ok=True)
        if proc.returncode != 0:
            raise RuntimeError("pandoc failed:\n" + proc.stderr[:1000])
        result = DRAFT_DIR / docx_out
        removed = cleanup_latex_sidecars(tex_path)
        if removed:
            names = ", ".join(path.name for path in removed)
            print(f"removed LaTeX sidecar file(s): {names}")
        print(f"wrote {result.relative_to(PROJECT_ROOT)}")
        return result


def main() -> int:
    tex_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_TEX
    try:
        build(tex_path)
    except RuntimeError as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
