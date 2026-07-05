"""Remove the mislabeled cross-group duplicate from the generated G5Test outputs.

The mesh folder contains a stray ``Group_D10_65942.stl`` whose number (65942) is
actually E10 (``Group_E10_65942.stl``); the two files are byte-identical. The
roster glob in ``G5Test.py`` therefore produced 36 entries while the manuscript
and Figure 6 use the canonical 35 (D10 = 37416). This script post-processes the
*already generated* artifacts so they match the 35-mesh basis, without re-running
any TOMO/SFTF computation (which would be GPU-heavy and would also overwrite the
per-angle caches). It is idempotent: re-running finds nothing to remove.

The rule is identical to ``render_figure6_grouped.dedupe_records``: drop any
group-D row whose trailing mesh number also appears in a group-E row.

Artifacts cleaned (under Experimental/G5Test/):
  * G5Test_summary.csv
  * G5Test_summary.json
  * every _5G_CA<deg>deg_4Method_table.html

Run:  python scripts/dedupe_g5test_outputs.py
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
G5_DIR = PROJECT_ROOT / "Experimental" / "G5Test"

MESH_RE = re.compile(r"Group_([A-Za-z])\d+_(\d+)\.[A-Za-z0-9]+")


def mesh_number(name: str) -> str:
    """Trailing numeric token of a Group_XN_<id> mesh name (e.g. 65942)."""
    return Path(str(name)).stem.split("_")[-1]


def mesh_group(name: str) -> str:
    """Group letter of a Group_XN_<id> mesh name (e.g. D)."""
    stem = Path(str(name)).stem
    parts = stem.split("_")
    return parts[1][:1].upper() if len(parts) > 1 else ""


def clean_csv(path: Path) -> None:
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        return
    header, data = rows[0], rows[1:]
    mesh_col = header.index("mesh")
    e_numbers = {mesh_number(r[mesh_col]) for r in data if mesh_group(r[mesh_col]) == "E"}
    kept, dropped = [], []
    for r in data:
        if mesh_group(r[mesh_col]) == "D" and mesh_number(r[mesh_col]) in e_numbers:
            dropped.append(r[mesh_col])
            continue
        kept.append(r)
    if not dropped:
        print(f"  {path.name}: already clean ({len(data)} rows)")
        return
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(kept)
    path.write_text(buf.getvalue(), encoding="utf-8")
    print(f"  {path.name}: dropped {dropped} -> {len(kept)} rows")


def clean_json(path: Path) -> None:
    records = json.loads(path.read_text(encoding="utf-8"))
    e_numbers = {mesh_number(r["mesh"]) for r in records if mesh_group(r["mesh"]) == "E"}
    kept, dropped = [], []
    for r in records:
        if mesh_group(r["mesh"]) == "D" and mesh_number(r["mesh"]) in e_numbers:
            dropped.append(r["mesh"])
            continue
        kept.append(r)
    if not dropped:
        print(f"  {path.name}: already clean ({len(records)} rows)")
        return
    path.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {path.name}: dropped {dropped} -> {len(kept)} rows")


def clean_html(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    rows = list(re.finditer(r"<tr>.*?</tr>", html, flags=re.DOTALL))
    # collect the E-group numbers across all data rows
    e_numbers = set()
    for m in rows:
        mm = MESH_RE.search(m.group(0))
        if mm and mm.group(1).upper() == "E":
            e_numbers.add(mm.group(2))
    dropped = []
    for m in rows:
        mm = MESH_RE.search(m.group(0))
        if mm and mm.group(1).upper() == "D" and mm.group(2) in e_numbers:
            html = html.replace(m.group(0), "", 1)
            dropped.append(f"Group_{mm.group(1)}..._{mm.group(2)}")
    if not dropped:
        print(f"  {path.name}: already clean")
        return
    # tidy any blank line left where a row was removed
    html = re.sub(r"\n[ \t]*\n", "\n", html)
    path.write_text(html, encoding="utf-8")
    print(f"  {path.name}: dropped {dropped}")


def main() -> None:
    print("Deduping generated G5Test outputs (cross-group D/E rule)...")
    csv_path = G5_DIR / "G5Test_summary.csv"
    json_path = G5_DIR / "G5Test_summary.json"
    if csv_path.is_file():
        clean_csv(csv_path)
    if json_path.is_file():
        clean_json(json_path)
    for html_path in sorted(G5_DIR.glob("_5G_CA*deg_4Method_table.html")):
        clean_html(html_path)
    print("done.")


if __name__ == "__main__":
    main()
