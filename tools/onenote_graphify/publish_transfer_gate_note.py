"""Publish the transfer-gate analysis note and link it from the year summary."""

from __future__ import annotations

import argparse
from pathlib import Path


NOTE_LINK = "- 연구 전이 Gate 해석: [[연구 전이 Gate - Graphify 추가 해석]]"
DATA_LINK = "- 연구 전이 Gate 데이터: [research-transfer-gate.json](graphify-out/research-transfer-gate.json)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    parser.add_argument("note", type=Path)
    parser.add_argument("summary", type=Path)
    args = parser.parse_args()

    note_text = args.template.resolve().read_text(encoding="utf-8-sig")
    note_path = args.note.resolve()
    note_path.write_text(note_text, encoding="utf-8")

    summary_path = args.summary.resolve()
    summary = summary_path.read_text(encoding="utf-8-sig")
    anchor = "- 강조 연구 여정 데이터: [research-journey.json](graphify-out/research-journey.json)"
    if anchor not in summary:
        raise RuntimeError("Summary output-link anchor not found")
    additions = []
    if NOTE_LINK not in summary:
        additions.append(NOTE_LINK)
    if DATA_LINK not in summary:
        additions.append(DATA_LINK)
    if additions:
        summary = summary.replace(anchor, anchor + "\n" + "\n".join(additions), 1)
        summary_path.write_text(summary, encoding="utf-8")

    print(f"Published transfer-gate analysis to {note_path}")
    print(f"Summary links present: {NOTE_LINK in summary and DATA_LINK in summary}")


if __name__ == "__main__":
    main()
