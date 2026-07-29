"""Group Graphify semantic files by directory into bounded chunks."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file_list", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--size", type=int, default=22)
    args = parser.parse_args()

    files = [line for line in args.file_list.read_text(encoding="utf-8").splitlines() if line]
    groups: dict[str, list[str]] = defaultdict(list)
    for file_name in files:
        groups[str(Path(file_name).parent)].append(file_name)

    chunks: list[list[str]] = []
    current: list[str] = []
    for group in groups.values():
        while group:
            capacity = args.size - len(current)
            current.extend(group[:capacity])
            del group[:capacity]
            if len(current) == args.size:
                chunks.append(current)
                current = []
    if current:
        chunks.append(current)

    for old in args.output_dir.glob(".chunk_files_*.txt"):
        old.unlink()
    for index, chunk in enumerate(chunks, start=1):
        (args.output_dir / f".chunk_files_{index:02d}.txt").write_text(
            "\n".join(chunk), encoding="utf-8"
        )
    print(f"Chunks: {[len(chunk) for chunk in chunks]}")


if __name__ == "__main__":
    main()
