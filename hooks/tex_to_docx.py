#!/usr/bin/env python3
"""PostToolUse hook: convert an edited draft/*.tex file to a figure-complete .docx.

Plain ``pandoc`` drops tikzpicture diagrams and cannot display PDF figures inside
Word. This hook delegates to ``scripts/build_docx.py``, which pre-renders every
tikzpicture to PNG and rasterises PDF figures to PNG before calling pandoc, so
the .docx contains every figure exactly as the .pdf does.

It resolves all paths from the edited file (not the process cwd), so it works no
matter where Claude's shell happens to be. Always exits 0 so it never blocks.
"""
import json
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    f = (payload.get("tool_input") or {}).get("file_path", "") or ""
    f = f.replace("\\", "/")
    if not f.lower().endswith(".tex"):
        return 0

    tex_path = Path(f).resolve()
    parts = [p.lower() for p in tex_path.parts]
    if "draft" not in parts or not tex_path.is_file():
        return 0
    # ignore the throwaway rewritten tex the builder itself writes
    if tex_path.name.endswith(".docxsrc.tex"):
        return 0

    # project root = the parent of the 'draft' directory in the path
    draft_idx = parts.index("draft")
    project_root = Path(*tex_path.parts[:draft_idx])
    builder = project_root / "scripts" / "build_docx.py"
    if not builder.is_file():
        return 0

    sys.path.insert(0, str(project_root))
    try:
        from scripts.build_docx import build  # noqa: E402

        docx = build(tex_path)
        print(json.dumps({
            "systemMessage": f"docx (figures embedded): {docx.name} 생성 완료",
            "suppressOutput": True,
        }))
    except Exception as e:  # never block Claude on a conversion failure
        print(json.dumps({"systemMessage": f"docx 변환 실패 ({tex_path.name}): {str(e)[:300]}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
