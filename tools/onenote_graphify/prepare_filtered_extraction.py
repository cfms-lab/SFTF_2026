"""Merge semantic chunks and keep only the current dated-page corpus.

The semantic chunks may have been produced before the OneNote export was
renumbered.  Corpus files are therefore matched by their title portion rather
than their three-digit generated prefix, and source paths are rewritten to the
current snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PREFIX_RE = re.compile(r"^\d{3}\s+")
ID_RE = re.compile(r"^[a-z0-9_]+$")


def title_key(path_value: str) -> str:
    return PREFIX_RE.sub("", Path(path_value).name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    out = root / "graphify-out"
    detection = json.loads((out / ".graphify_detect.json").read_text(encoding="utf-8"))

    current_files: list[str] = []
    for paths in detection.get("files", {}).values():
        current_files.extend(paths)
    current_by_title = {title_key(path): str(Path(path).resolve()) for path in current_files}

    nodes_by_id: dict[str, dict] = {}
    candidate_edges: list[dict] = []
    candidate_hyperedges: list[dict] = []
    invalid_ids: list[str] = []

    def remap_source(item: dict) -> bool:
        source = item.get("source_file", "")
        current = current_by_title.get(title_key(source))
        if not current:
            return False
        item["source_file"] = current
        return True

    for chunk_path in sorted(out.glob(".graphify_chunk_*.json")):
        chunk = json.loads(chunk_path.read_text(encoding="utf-8-sig"))
        for raw_node in chunk.get("nodes", []):
            node = dict(raw_node)
            if not remap_source(node):
                continue
            node_id = str(node.get("id", ""))
            if not ID_RE.fullmatch(node_id):
                invalid_ids.append(node_id)
                continue
            nodes_by_id.setdefault(node_id, node)
        candidate_edges.extend(dict(edge) for edge in chunk.get("edges", []))
        candidate_hyperedges.extend(dict(edge) for edge in chunk.get("hyperedges", []))

    kept_ids = set(nodes_by_id)
    edges: list[dict] = []
    seen_edges: set[tuple] = set()
    dangling_edges = 0
    for edge in candidate_edges:
        if not remap_source(edge):
            continue
        if edge.get("source") not in kept_ids or edge.get("target") not in kept_ids:
            dangling_edges += 1
            continue
        key = (
            edge.get("source"),
            edge.get("target"),
            edge.get("relation"),
            edge.get("source_file"),
            edge.get("source_location"),
        )
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append(edge)

    hyperedges: list[dict] = []
    seen_hyperedges: set[tuple] = set()
    for hyperedge in candidate_hyperedges:
        if not remap_source(hyperedge):
            continue
        hyperedge["nodes"] = [node_id for node_id in hyperedge.get("nodes", []) if node_id in kept_ids]
        if len(set(hyperedge["nodes"])) < 3:
            continue
        key = (
            hyperedge.get("id"),
            tuple(hyperedge["nodes"]),
            hyperedge.get("source_file"),
        )
        if key not in seen_hyperedges:
            seen_hyperedges.add(key)
            hyperedges.append(hyperedge)

    semantic = {
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
        "hyperedges": hyperedges,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    ast_data = json.loads((out / ".graphify_ast.json").read_text(encoding="utf-8"))
    extraction = {
        "nodes": ast_data.get("nodes", []) + semantic["nodes"],
        "edges": ast_data.get("edges", []) + semantic["edges"],
        "hyperedges": semantic["hyperedges"],
        "input_tokens": ast_data.get("input_tokens", 0),
        "output_tokens": ast_data.get("output_tokens", 0),
    }

    (out / ".graphify_semantic.json").write_text(
        json.dumps(semantic, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / ".graphify_extract.json").write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    source_counts: dict[str, int] = {}
    for node in semantic["nodes"]:
        key = title_key(node["source_file"])
        source_counts[key] = source_counts.get(key, 0) + 1

    diagnostics = {
        "allowed_corpus_files": len(current_files),
        "covered_corpus_files": len(source_counts),
        "nodes": len(semantic["nodes"]),
        "edges": len(edges),
        "hyperedges": len(hyperedges),
        "invalid_node_ids": sorted(set(invalid_ids)),
        "dropped_dangling_edges": dangling_edges,
        "uncovered_corpus_files": sorted(set(current_by_title) - set(source_counts)),
    }
    (out / ".graphify_filter_diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
