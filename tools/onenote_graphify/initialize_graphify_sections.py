"""Detect exported OneNote corpora and prepare semantic-extraction chunks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from graphify.cache import check_semantic_cache
from graphify.detect import detect


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--chunk-size", type=int, default=22)
    args = parser.parse_args()

    summaries = []
    for section_root in args.roots:
        section_root = section_root.resolve()
        corpus = section_root / "graph-corpus"
        out = section_root / "graphify-out"
        out.mkdir(parents=True, exist_ok=True)

        detection = detect(corpus)
        (out / ".graphify_detect.json").write_text(
            json.dumps(detection, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out / ".graphify_python").write_text(sys.executable, encoding="utf-8")
        (out / ".graphify_root").write_text(str(corpus), encoding="utf-8")
        (out / ".graphify_ast.json").write_text(
            json.dumps(
                {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        semantic_files = [
            path
            for category in ("document", "paper", "image")
            for path in detection.get("files", {}).get(category, [])
        ]
        cached_nodes, cached_edges, cached_hyperedges, uncached = check_semantic_cache(
            semantic_files, root=corpus
        )
        cached = {
            "nodes": cached_nodes,
            "edges": cached_edges,
            "hyperedges": cached_hyperedges,
        }
        if cached_nodes or cached_edges or cached_hyperedges:
            (out / ".graphify_cached.json").write_text(
                json.dumps(cached, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            (out / ".graphify_cached.json").unlink(missing_ok=True)

        work_chunks = chunks(uncached, args.chunk_size)
        (out / ".graphify_chunks.json").write_text(
            json.dumps(work_chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out / ".graphify_uncached.txt").write_text("\n".join(uncached), encoding="utf-8")

        summaries.append(
            {
                "section": section_root.name,
                "files": detection.get("total_files", 0),
                "words": detection.get("total_words", 0),
                "cached_files": len(semantic_files) - len(uncached),
                "uncached_files": len(uncached),
                "chunks": len(work_chunks),
                "skipped_sensitive": len(detection.get("skipped_sensitive", [])),
            }
        )

    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
