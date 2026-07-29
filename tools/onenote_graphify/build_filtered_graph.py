"""Build the dated-only OneNote research graph from prepared extraction JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.detect import save_manifest
from graphify.diagnostics import diagnose_extraction
from graphify.export import to_json
from graphify.exporters.html import to_html
from graphify.report import generate


COMMUNITY_LABELS = {
    0: "SFTFCluster 목적함수와 복합재",
    1: "버그 수정 후 원고 재평가",
    2: "비대칭 텐서 응용 확장",
    3: "Cura 독립 검증과 SFTFSoft",
    4: "SFTF 방향 후보와 Warm-start",
    5: "Shadow Tensor 가시성",
    6: "CUDA 드레이프 솔버",
    7: "의복 Physical AI 데이터",
    8: "미분가능 SFTF와 GNN",
    9: "PFTF 신규성과 RE100",
    10: "PFTF 방향 컬링 음성 결과",
    11: "SFTF 심사 위험과 재현성",
    12: "CUDA Colab 실행 환경",
    13: "인체 계측 견고성 개선",
    14: "Ground Node와 평가 지표",
    15: "자동봉제 그래프 매칭",
    16: "SoftSew 관측가능성 공백",
    17: "SFTFSoft 비용 스케일",
    18: "Auxetic Infill",
    19: "SEM Metaball 재구성",
    20: "2026 투고 포트폴리오",
    21: "PFTF 압박밴드 공동연구",
    22: "하드웨어별 LLM 선택",
    23: "SFTF 순위상관 기준",
    24: "SFTFSoft PiAM 적합성",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    corpus = root / "graph-corpus"
    out = root / "graphify-out"
    extraction = json.loads((out / ".graphify_extract.json").read_text(encoding="utf-8"))
    detection = json.loads((out / ".graphify_detect.json").read_text(encoding="utf-8"))

    diagnostics = diagnose_extraction(
        extraction,
        directed=False,
        root=corpus,
        extract_path=out / ".graphify_extract.json",
    )
    (out / "diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    graph = build_from_json(extraction, directed=False, root=corpus)
    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = {
        cid: COMMUNITY_LABELS.get(cid, f"Research Theme {cid}")
        for cid in communities
    }
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)

    token_cost = {
        "input": extraction.get("input_tokens", 0),
        "output": extraction.get("output_tokens", 0),
        "note": "semantic extraction was performed by host subagents; token counts were not reported",
    }
    analysis = {
        "communities": communities,
        "cohesion_scores": cohesion,
        "community_labels": labels,
        "god_nodes": gods,
        "surprising_connections": surprises,
        "suggested_questions": questions,
    }
    (out / ".graphify_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / ".graphify_labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "cost.json").write_text(
        json.dumps(token_cost, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    written = to_json(
        graph,
        communities,
        str(out / "graph.json"),
        force=True,
        community_labels=labels,
    )
    if not written:
        raise RuntimeError("Graphify declined to write graph.json")

    report = generate(
        graph,
        communities,
        cohesion,
        labels,
        gods,
        surprises,
        detection,
        token_cost,
        str(corpus),
        suggested_questions=questions,
        obsidian=False,
    )
    (out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    to_html(graph, communities, str(out / "graph.html"), community_labels=labels)

    corpus_files = {
        path for paths in detection.get("files", {}).values() for path in paths
    }
    save_manifest(
        detection.get("files", {}),
        str(out / "manifest.json"),
        kind="semantic",
        root=corpus,
        scan_corpus=corpus_files,
    )

    result = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "hyperedges": len(graph.graph.get("hyperedges", [])),
        "communities": len(communities),
        "god_nodes": gods,
        "surprising_connections": surprises,
        "suggested_questions": questions,
        "diagnostics": diagnostics,
    }
    (out / "build-summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
