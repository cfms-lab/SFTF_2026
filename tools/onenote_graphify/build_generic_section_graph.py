"""Merge semantic chunks and build one OneNote year-section Graphify graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cache import save_semantic_cache
from graphify.cluster import cluster, score_all
from graphify.detect import save_manifest
from graphify.diagnostics import diagnose_extraction
from graphify.export import to_json
from graphify.exporters.html import to_html
from graphify.report import generate


VALID_ID = re.compile(r"^[a-z0-9_]+$")
VALID_TYPES = {"code", "document", "paper", "image", "rationale", "concept"}


def choose_label(graph, members: list[str], cid: int) -> str:
    candidates = sorted(
        members,
        key=lambda node_id: (
            graph.nodes[node_id].get("file_type") == "document",
            -graph.degree(node_id),
            graph.nodes[node_id].get("label", node_id),
        ),
    )
    if not candidates:
        return f"Research Theme {cid}"
    label = str(graph.nodes[candidates[0]].get("label", candidates[0])).strip()
    label = re.sub(r"\s*연구노트$", "", label)
    return label[:42] or f"Research Theme {cid}"


def merge_chunks(out: Path, allowed_files: set[str]) -> tuple[dict, dict]:
    cached_path = out / ".graphify_cached.json"
    cached = (
        json.loads(cached_path.read_text(encoding="utf-8"))
        if cached_path.exists()
        else {"nodes": [], "edges": [], "hyperedges": []}
    )

    node_by_id: dict[str, dict] = {}
    raw_edges: list[dict] = []
    raw_hyperedges: list[dict] = []
    invalid_ids: list[str] = []
    invalid_types: list[str] = []

    sources = [cached, *[
        json.loads(path.read_text(encoding="utf-8-sig"))
        for path in sorted(out.glob(".graphify_chunk_*.json"))
    ]]
    for source in sources:
        for node in source.get("nodes", []):
            node_id = str(node.get("id", ""))
            if not VALID_ID.fullmatch(node_id):
                invalid_ids.append(node_id)
                continue
            if node.get("file_type") not in VALID_TYPES:
                invalid_types.append(str(node.get("file_type")))
                continue
            if node.get("source_file") not in allowed_files:
                continue
            node_by_id.setdefault(node_id, node)
        raw_edges.extend(source.get("edges", []))
        raw_hyperedges.extend(source.get("hyperedges", []))

    node_ids = set(node_by_id)
    edges: list[dict] = []
    seen_edges: set[tuple] = set()
    dangling = 0
    for edge in raw_edges:
        if edge.get("source_file") not in allowed_files:
            continue
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            dangling += 1
            continue
        key = (
            edge.get("source"), edge.get("target"), edge.get("relation"),
            edge.get("source_file"), edge.get("source_location"),
        )
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append(edge)

    hyperedges: list[dict] = []
    seen_hyperedges: set[tuple] = set()
    for item in raw_hyperedges:
        if item.get("source_file") not in allowed_files:
            continue
        item = dict(item)
        item["nodes"] = list(dict.fromkeys(
            node_id for node_id in item.get("nodes", []) if node_id in node_ids
        ))
        if len(item["nodes"]) < 3:
            continue
        key = (item.get("id"), tuple(item["nodes"]), item.get("source_file"))
        if key not in seen_hyperedges:
            seen_hyperedges.add(key)
            hyperedges.append(item)

    extraction = {
        "nodes": list(node_by_id.values()),
        "edges": edges,
        "hyperedges": hyperedges,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    merge_diagnostics = {
        "nodes": len(node_by_id),
        "edges": len(edges),
        "hyperedges": len(hyperedges),
        "invalid_ids": sorted(set(invalid_ids)),
        "invalid_types": sorted(set(invalid_types)),
        "dropped_dangling_edges": dangling,
    }
    return extraction, merge_diagnostics


def make_summary(
    section_root: Path,
    manifest: dict,
    detection: dict,
    graph,
    communities: dict[int, list[str]],
    cohesion: dict[int, float],
    labels: dict[int, str],
    gods: list[dict],
    surprises: list[dict],
    questions: list[dict],
) -> str:
    section = section_root.name
    graph_uri = (section_root / "graphify-out" / "graph.html").as_uri()
    lines = [
        "---",
        "source_type: OneNote Graphify summary",
        f'section: "{section}"',
        f"source_page_count: {manifest.get('source_page_count', 0)}",
        f"included_dated_pages: {manifest.get('exported_page_count', 0)}",
        f"excluded_non_date_pages: {manifest.get('undated_skipped_count', 0) + manifest.get('sensitive_skipped_count', 0)}",
        f"graph_nodes: {graph.number_of_nodes()}",
        f"graph_edges: {graph.number_of_edges()}",
        f"graph_communities: {len(communities)}",
        "tags:",
        "  - 연구노트",
        "  - graphify",
        "---",
        "",
        f"# {section} 연구노트 요약",
        "",
        "## 범위",
        "",
        f"- OneNote 전체 {manifest.get('source_page_count', 0)}쪽 중 제목이 날짜로 시작하는 {manifest.get('exported_page_count', 0)}쪽만 포함했다.",
        f"- 날짜로 시작하지 않는 {manifest.get('undated_skipped_count', 0) + manifest.get('sensitive_skipped_count', 0)}쪽은 원문, 요약, Graphify corpus와 그래프에서 제외했다.",
        f"- Graphify 입력은 {detection.get('total_files', 0)}개 문서, 약 {detection.get('total_words', 0):,}단어다.",
        "",
        "## 핵심 연구 주제",
        "",
    ]
    ranked = sorted(communities, key=lambda cid: (-len(communities[cid]), cid))
    for cid in ranked[:12]:
        member_labels = [
            graph.nodes[node_id].get("label", node_id)
            for node_id in sorted(communities[cid], key=lambda n: -graph.degree(n))[:4]
        ]
        lines.append(
            f"- **{labels[cid]}** — {len(communities[cid])}개 개념, 응집도 {cohesion.get(cid, 0):.3f}; "
            + ", ".join(member_labels)
        )

    lines += ["", "## 중심 개념", ""]
    for node in gods[:8]:
        lines.append(f"- `{node['label']}` — {node['degree']}개 관계")

    lines += ["", "## 주목할 교차 연결", ""]
    if surprises:
        for item in surprises[:5]:
            lines.append(
                f"- `{item['source']}` → `{item['target']}` ({item.get('relation', 'related_to')}, {item.get('confidence', 'EXTRACTED')})"
            )
    else:
        lines.append("- 서로 다른 문서·커뮤니티를 잇는 뚜렷한 연결은 아직 적다.")

    lines += ["", "## 논리적으로 확인할 질문", ""]
    for index, item in enumerate(questions[:7], 1):
        lines.append(f"{index}. {item.get('question', '')}")
        if item.get("why"):
            lines.append(f"   - 이유: {item['why']}")

    lines += [
        "",
        "## 다음 연차와 연결할 때의 점검",
        "",
        "- 당시의 계산 결과와 현재 코드·데이터가 같은 버전인지 provenance를 확인한다.",
        "- 내부 proxy 결과와 독립적인 검증 도구 또는 실험 결과를 구분한다.",
        "- 실패·오류 수정 기록이 이후 논문 주장과 데이터에 반영됐는지 추적한다.",
        "- 다음 연차에 다시 나타난 개념은 이름뿐 아니라 수식·가정·검증 방법이 어떻게 변했는지 비교한다.",
        "",
        "## 산출물 연결",
        "",
        "- 원문 인덱스: [[원문-pages/INDEX|날짜 제목 원문]]",
        f"- 대화형 그래프: [graph.html](<{graph_uri}>)",
        "- Graphify 보고서: [GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md)",
        "- 기계 판독 그래프: [graph.json](graphify-out/graph.json)",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("section_root", type=Path)
    args = parser.parse_args()

    section_root = args.section_root.resolve()
    corpus = section_root / "graph-corpus"
    out = section_root / "graphify-out"
    detection = json.loads((out / ".graphify_detect.json").read_text(encoding="utf-8"))
    manifest = json.loads((section_root / "import-manifest.json").read_text(encoding="utf-8-sig"))
    allowed_files = {
        path for paths in detection.get("files", {}).values() for path in paths
    }

    extraction, merge_diagnostics = merge_chunks(out, allowed_files)
    if not extraction["nodes"]:
        raise RuntimeError(f"No semantic nodes extracted for {section_root.name}")
    (out / ".graphify_extract.json").write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_semantic_cache(
        extraction["nodes"], extraction["edges"], extraction["hyperedges"],
        root=corpus, allowed_source_files=list(allowed_files),
    )

    diagnostics = diagnose_extraction(
        extraction, directed=False, root=corpus, extract_path=out / ".graphify_extract.json"
    )
    (out / "diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    graph = build_from_json(extraction, directed=False, root=corpus)
    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = {cid: choose_label(graph, members, cid) for cid, members in communities.items()}
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)
    tokens = {
        "input": 0,
        "output": 0,
        "note": "host subagent token counts were not reported",
    }

    if not to_json(
        graph, communities, str(out / "graph.json"), force=True, community_labels=labels
    ):
        raise RuntimeError("Graphify declined to write graph.json")
    report = generate(
        graph, communities, cohesion, labels, gods, surprises, detection, tokens,
        str(corpus), suggested_questions=questions,
    )
    (out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    (out / ".graphify_labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    to_html(graph, communities, str(out / "graph.html"), community_labels=labels)
    save_manifest(
        detection.get("files", {}), str(out / "manifest.json"), kind="semantic",
        root=corpus, scan_corpus=allowed_files,
    )
    (out / "cost.json").write_text(
        json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = make_summary(
        section_root, manifest, detection, graph, communities, cohesion, labels,
        gods, surprises, questions,
    )
    summary_path = section_root / f"{section_root.name} 연구노트 요약.md"
    summary_path.write_text(summary, encoding="utf-8")

    build_summary = {
        "section": section_root.name,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "hyperedges": len(graph.graph.get("hyperedges", [])),
        "communities": len(communities),
        "merge_diagnostics": merge_diagnostics,
        "diagnostics": diagnostics,
        "god_nodes": gods,
        "surprising_connections": surprises,
        "suggested_questions": questions,
    }
    (out / "build-summary.json").write_text(
        json.dumps(build_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "section": section_root.name,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "hyperedges": len(graph.graph.get("hyperedges", [])),
        "communities": len(communities),
        "dangling": diagnostics.get("dangling_endpoint_edges", 0),
        "self_loops": diagnostics.get("self_loop_edges", 0),
        "collapsed": diagnostics.get("undirected_same_endpoint_collapsed_edges", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
