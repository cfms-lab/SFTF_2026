"""Build a provenance-preserving 2022-2026 OneNote research genealogy graph.

The year graphs remain authoritative for within-year Graphify extraction.
This builder prefixes their node IDs, merges them, and adds a small set of
explicitly curated cross-year lineage links.  Curated links are always marked
INFERRED and are never represented as Graphify-extracted semantic facts.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.diagnostics import diagnose_extraction
from graphify.export import to_json
from graphify.exporters.html import to_html
from graphify.report import generate


SECTIONS = [
    (2022, "중견1차년도(2022)"),
    (2023, "중견2차년도(2023)"),
    (2024, "중견3차년도(2024)"),
    (2025, "중견4차년도(2025)"),
    (2026, "중견5차년도(2026)"),
]

OUTPUT_FOLDER = "중견 연구 계보(2022-2026)"
SUMMARY_NAME = "중견 연구 계보 요약.md"
INDEX_NAME = "중견 연구노트 연차별 Graphify 인덱스.md"


def qid(year: int, node_id: str) -> str:
    return f"y{year}__{node_id}"


def step(year: int, node_id: str, date_text: str, phase: str, detail: str) -> dict:
    return {
        "id": qid(year, node_id),
        "year": year,
        "date": date_text,
        "phase": phase,
        "detail": detail,
    }


THREADS = {
    "support_validation": {
        "label": "지지체적·검증 계보",
        "color": "#00d4ff",
        "steps": [
            step(2022, "001_2022_03_04_tomography_vss_vss_error", "2022-03-04", "Vss 보정 공백", "3DWOX 대비 과소·음수 지지체적 문제를 식별"),
            step(2022, "012_2022_03_11_duplicate_points_pixelwise_volume_correction", "2022-03-11", "픽셀 단위 보정", "Vo·Vss 누적 오류를 픽셀별 계산으로 수정"),
            step(2023, "041_7_10_convex_hull_vs_alpha_shape_vs_k_dop_1_explicit_support_volume", "2023-07-10", "명시적 지지체적 수식", "근사 형상과 지지체적 계산을 수식으로 정리"),
            step(2023, "037_7_3_tomo_tse2023_benchmark_dataset", "2023-07-03", "벤치마크 데이터", "Tomo 비교용 메쉬 데이터셋을 정리"),
            step(2024, "003_2024_06_19_tomo_data_tomo_mesh_dataset", "2024-06-19", "데이터 감사", "CPU/GPU·Mo/Mss 비교를 위한 데이터셋 재정비"),
            step(2025, "050_2025_07_19_bone_12_tomo_orientation_validation", "2025-07-19", "방향 검증", "Tomo 방향 최적화 검증으로 확장"),
            step(2026, "012_2026_06_19_eigenvector_tomo_sftf_validation", "2026-06-19", "TOMO-SFTF 검증", "Support Tensor 고유벡터와 TOMO 결과를 비교"),
            step(2026, "graph_corpus_033_2026_06_28_sftf___cura_slicer_validation", "2026-06-28", "독립 슬라이서 교차검증", "내부 TOMO 기준에서 Cura 기준으로 검증 독립성을 강화"),
        ],
    },
    "shadow_visibility": {
        "label": "Shadow·가시성 계보",
        "color": "#b084ff",
        "steps": [
            step(2022, "p053_2022_05_14_half_orbital__full_and_half_orbitals", "2022-05-14", "Support Orbital", "방향별 shadow 거리를 full·half orbital로 근사"),
            step(2022, "p056_2022_05_17_orbital_validation__int3_orbital_validation", "2022-05-17", "Orbital 검증", "여러 메쉬에서 orbital landscape를 실제값과 비교"),
            step(2023, "016_6_3_tse4_orbital_shadow_algorithm", "2023-06-03", "Orbital Shadow", "가시성 문제를 회전·방향 공간 알고리즘으로 재구성"),
            step(2023, "017_6_9_tomonv_tomosp_shadow_pyramid_shadow_pyramid_preprocessing", "2023-06-09", "Shadow Pyramid", "삼각형 관계를 pyramid 전처리로 압축"),
            step(2023, "041_7_10_convex_hull_vs_alpha_shape_vs_k_dop_1_shadow_tensor_equation", "2023-07-10", "Shadow Tensor 수식", "방향·가시성 관계를 텐서 수식으로 명시"),
            step(2024, "001_2024_06_02_tomo_st_shadow_tensor_shadow_tensor", "2024-06-02", "Shadow Tensor 복기", "픽셀 없이 삼각형 쌍 occlusion을 다루는 개념을 재정리"),
            step(2025, "038_2025_07_09_bone_4_shadow_tensor_heat_analogy", "2025-07-09", "Heat 행렬 유추", "Shadow Tensor 계산을 heat-map 행렬 방식과 연결"),
            step(2026, "005_2026_05_20_shadow_tensor_shadow_tensor", "2026-05-20", "Shadow Tensor 재점화", "AI 협업을 통해 기존 개념과 실패 조건을 다시 구조화"),
            step(2026, "012_2026_06_19_eigenvector_tomo_sftf_validation", "2026-06-19", "SFTF 정식화·검증", "Shadow/Support 관계를 고유벡터 기반 후보 방향으로 연결"),
        ],
    },
    "mesh_partition": {
        "label": "메쉬 분할·군집 계보",
        "color": "#ff7ab6",
        "steps": [
            step(2022, "p058_2022_05_19_mesh_segmentation__support_aware_mesh_segmentation", "2022-05-19", "지지 인지 메쉬 분할", "지지구조 감소를 위한 분할 가능성을 조사"),
            step(2025, "001_2025_03_01_1_support_minimizing_partition", "2025-03-01", "지지 최소화 분할", "분할 목적을 지지구조 최소화로 구체화"),
            step(2025, "001_2025_03_01_1_pose_invariant_meshcnn", "2025-03-01", "자세 불변 MeshCNN", "자세 변화에 강한 학습 기반 분할을 검토"),
            step(2025, "040_2025_07_09_mesh_clustering_2_fixed_joint_partitioning", "2025-07-09", "고정 관절 좌표 분할", "관절 좌표를 사용한 안정적 절단 규칙으로 전환"),
            step(2025, "068_2025_09_11_bodym_3_graph_based_clustering", "2025-09-11", "그래프 군집", "Graph Laplacian 기반 군집화로 확장"),
            step(2026, "graph_corpus_027_2026_06_27_sftf_clustering___sftf_clustering_improvement_note", "2026-06-27", "SFTF-Clustering", "지지 목적함수와 분할·군집 계보를 결합"),
        ],
    },
    "ai_sftf_pftf": {
        "label": "AI → SFTF/PFTF",
        "color": "#ffd166",
        "steps": [
            step(2026, "004_2026_05_19_whichllm_test_note", "2026-05-19", "AI 도구 탐색", "문제와 장비에 맞는 LLM 협업 방식을 선택"),
            step(2026, "005_2026_05_20_shadow_tensor_shadow_tensor", "2026-05-20", "기존 문제 복기", "Shadow Tensor와 occlusion 문제를 다시 구조화"),
            step(2026, "008_shadow_tensor_mathematica_note", "2026-05-29~06-15", "연속 계산 실험", "Mathematica 반복 실험으로 정식화와 실패 조건을 탐색"),
            step(2026, "012_2026_06_19_eigenvector_tomo_sftf_validation", "2026-06-19", "SFTF 정식화·검증", "Support Tensor 고유벡터를 TOMO 전수탐색과 비교"),
            step(2026, "graph_corpus_025_2026_06_24_codex__paper_review_note", "2026-06-24", "AI 비판으로 주장 교정", "최종 솔버가 아닌 후보 생성기·warm-start로 주장 범위를 제한"),
            step(2026, "graph_corpus_029_2026_06_28_chatgpt__source_response_tensor", "2026-06-27~28", "핵심 개념 추상화", "source-response 비대칭 텐서로 파생 응용을 연결"),
            step(2026, "graph_corpus_033_2026_06_28_sftf___cura_slicer_validation", "2026-06-28~07-02", "독립 도구 검증", "Cura 지지량으로 검증 기준의 독립성을 강화"),
            step(2026, "graph_corpus_043_2026_07_03_vss_int16_document", "2026-07-03~04", "오류·음성 결과 수용", "int16 오류 수정 뒤 성능과 적용 범위를 재평가"),
            step(2026, "graph_corpus_048_2026_07_08_pftf_kdop_document", "2026-07-08", "PFTF로 개념 전이", "방향 컬링·압축·입지 문제로 비대칭 텐서 개념을 확장"),
            step(2026, "graph_corpus_051_2026_07_09_sftf_pftf_document", "2026-07-09", "신규성 경계 정리", "기존 수학과 문제·관찰·검증 설계의 신규성을 분리"),
            step(2026, "graph_corpus_058_2026_07_14_re100_document", "2026-07-14", "새 연구주제로 재적용", "RE100 입지 문제에 PFTF와 held-out 검증 흐름을 적용"),
        ],
    },
}


def load_year_graphs(vault_root: Path) -> tuple[dict, dict[int, list[str]], dict]:
    merged_nodes: list[dict] = []
    merged_edges: list[dict] = []
    merged_hyperedges: list[dict] = []
    communities: dict[int, list[str]] = {}
    counts: dict[str, dict] = {}

    for community_id, (year, section) in enumerate(SECTIONS):
        graph_path = vault_root / section / "graphify-out" / "graph.json"
        payload = json.loads(graph_path.read_text(encoding="utf-8-sig"))
        year_nodes: list[str] = []
        id_map: dict[str, str] = {}

        for raw in payload.get("nodes", []):
            node = dict(raw)
            old_id = str(node["id"])
            new_id = qid(year, old_id)
            id_map[old_id] = new_id
            node.update({
                "id": new_id,
                "original_id": old_id,
                "year": year,
                "section": section,
                "original_community": node.get("community"),
                "original_community_name": node.get("community_name"),
                "community": community_id,
                "community_name": section,
                "source_file": f"{section}/graph-corpus/{node.get('source_file', '')}",
            })
            merged_nodes.append(node)
            year_nodes.append(new_id)
        communities[community_id] = year_nodes

        for raw in payload.get("links", []):
            if raw.get("source") not in id_map or raw.get("target") not in id_map:
                continue
            edge = dict(raw)
            edge.update({
                "source": id_map[raw["source"]],
                "target": id_map[raw["target"]],
                "year": year,
                "section": section,
                "edge_origin": "graphify_year_graph",
                "source_file": f"{section}/graph-corpus/{edge.get('source_file', '')}",
            })
            merged_edges.append(edge)

        for raw in payload.get("hyperedges", []):
            members = [id_map[item] for item in raw.get("nodes", []) if item in id_map]
            if len(members) < 3:
                continue
            item = dict(raw)
            item.update({
                "id": f"y{year}__{raw.get('id', 'hyperedge')}",
                "nodes": members,
                "year": year,
                "section": section,
                "source_file": f"{section}/graph-corpus/{item.get('source_file', '')}",
            })
            merged_hyperedges.append(item)

        counts[str(year)] = {
            "section": section,
            "nodes": len(year_nodes),
            "edges": len(payload.get("links", [])),
            "hyperedges": len(payload.get("hyperedges", [])),
        }

    available = {node["id"] for node in merged_nodes}
    curated_edges: list[dict] = []
    curated_by_pair: dict[tuple[str, str], dict] = {}
    existing_by_pair = {
        tuple(sorted((str(edge["source"]), str(edge["target"])))): edge
        for edge in merged_edges
    }
    curated_link_count = 0
    missing: list[str] = []
    for thread_id, thread in THREADS.items():
        steps = thread["steps"]
        for item in steps:
            if item["id"] not in available:
                missing.append(item["id"])
        for left, right in zip(steps, steps[1:]):
            if left["id"] not in available or right["id"] not in available:
                continue
            curated_link_count += 1
            pair = tuple(sorted((left["id"], right["id"])))
            if pair in curated_by_pair:
                curated_by_pair[pair]["threads"].append(thread_id)
                curated_by_pair[pair]["source_location"] += f"; {thread['label']}"
                continue
            if pair in existing_by_pair:
                base_edge = existing_by_pair[pair]
                base_edge.setdefault("curated_threads", []).append(thread_id)
                base_edge["curated_lineage"] = True
                continue
            edge = {
                "source": left["id"],
                "target": right["id"],
                "relation": "curated_lineage",
                "confidence": "INFERRED",
                "confidence_score": 0.7,
                "weight": 1.0,
                "source_file": "중견 연구 계보 요약.md",
                "source_location": f"계보 스레드: {thread['label']}",
                "rationale": f"날짜와 연구 주제의 연속성에 따른 편집 계보: {left['phase']} → {right['phase']}",
                "edge_origin": "curated_longitudinal_genealogy",
                "semantic_edge": False,
                "thread": thread_id,
                "threads": [thread_id],
            }
            curated_edges.append(edge)
            curated_by_pair[pair] = edge
    if missing:
        raise RuntimeError(f"Curated genealogy nodes missing from year graphs: {sorted(set(missing))}")

    extraction = {
        "nodes": merged_nodes,
        "edges": merged_edges + curated_edges,
        "hyperedges": merged_hyperedges,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    audit = {
        "year_counts": counts,
        "base_nodes": len(merged_nodes),
        "base_edges": len(merged_edges),
        "curated_edges": len(curated_edges),
        "curated_links": curated_link_count,
        "hyperedges": len(merged_hyperedges),
        "curated_confidence": "INFERRED",
        "curated_semantic_edge": False,
    }
    return extraction, communities, audit


def overlay_css() -> str:
    return r"""
/* LONGITUDINAL_GENEALOGY_OVERLAY_START */
#genealogy-panel { padding: 12px; border-bottom: 1px solid #3d4058; background: linear-gradient(135deg, #12182a 0%, #1a1a2e 70%); }
#genealogy-panel h3 { color: #f4f7ff; font-size: 13px; margin: 0 0 7px; }
#genealogy-note { color: #9fa8c7; font-size: 9px; line-height: 1.4; margin-bottom: 8px; }
#genealogy-buttons { display: grid; gap: 5px; }
.genealogy-button { border: 1px solid var(--thread-color); color: var(--thread-color); background: transparent; border-radius: 5px; padding: 5px 7px; text-align: left; cursor: pointer; font-size: 10px; font-weight: 700; }
.genealogy-button.active { color: #141421; background: var(--thread-color); box-shadow: 0 0 14px color-mix(in srgb, var(--thread-color) 60%, transparent); }
#genealogy-steps { margin-top: 8px; max-height: 210px; overflow-y: auto; padding-right: 3px; }
.genealogy-step { display: grid; grid-template-columns: 43px 1fr; gap: 6px; padding: 4px; border-radius: 4px; cursor: pointer; }
.genealogy-step:hover { background: rgba(255,255,255,.06); }
.genealogy-date { color: #9fa8c7; font-size: 8px; }
.genealogy-phase { color: #f4f7ff; font-size: 10px; font-weight: 700; }
.genealogy-detail { color: #858eaa; font-size: 8px; line-height: 1.3; }
/* LONGITUDINAL_GENEALOGY_OVERLAY_END */
"""


def overlay_panel() -> str:
    return r"""
  <!-- LONGITUDINAL_GENEALOGY_PANEL_START -->
  <div id="genealogy-panel">
    <h3>2022–2026 연구 계보</h3>
    <div id="genealogy-note">계보선은 날짜와 주제 연속성으로 편집한 INFERRED 오버레이입니다. 주변 노드와 관계는 어둡게 하지 않고, 선택한 계보만 더 밝고 굵게 표시합니다.</div>
    <div id="genealogy-buttons"></div>
    <div id="genealogy-steps"></div>
  </div>
  <!-- LONGITUDINAL_GENEALOGY_PANEL_END -->
"""


def overlay_script() -> str:
    data = json.dumps(THREADS, ensure_ascii=False)
    return f"""
// LONGITUDINAL_GENEALOGY_SCRIPT_START
const GENEALOGY_THREADS = {data};
let genealogyActiveThread = null;
let genealogyOriginalPositions = {{}};
let genealogyHighlightedIds = new Set();
let genealogyOverlayEdgeIds = [];

function genealogyBaseNode(id) {{ return RAW_NODES.find(n => n.id === id); }}

function clearGenealogyHighlight(restoreView = false) {{
  genealogyOverlayEdgeIds.splice(0).forEach(id => edgesDS.remove(id));
  const restore = [...genealogyHighlightedIds].map(id => genealogyBaseNode(id)).filter(Boolean).map(n => ({{
    id: n.id, color: n.color, borderWidth: 1.5, size: n.size, font: n.font,
    opacity: 1, shadow: false, fixed: {{x: false, y: false}}, hidden: false,
  }}));
  if (restore.length) nodesDS.update(restore);
  Object.entries(genealogyOriginalPositions).forEach(([id, pos]) => network.moveNode(id, pos.x, pos.y));
  genealogyHighlightedIds = new Set();
  genealogyOriginalPositions = {{}};
  if (restoreView) network.fit({{animation: true}});
}}

function renderGenealogySteps(thread) {{
  const wrap = document.getElementById('genealogy-steps');
  wrap.innerHTML = thread.steps.map((item, i) => `<div class="genealogy-step" data-id="${{esc(item.id)}}"><span class="genealogy-date">${{esc(item.date)}}</span><span><div class="genealogy-phase">${{i + 1}}. ${{esc(item.phase)}}</div><div class="genealogy-detail">${{esc(item.detail)}}</div></span></div>`).join('');
  wrap.querySelectorAll('.genealogy-step').forEach(el => el.addEventListener('click', () => {{
    const id = el.dataset.id; network.focus(id, {{scale: 1.55, animation: true}}); network.selectNodes([id]); showInfo(id);
  }}));
}}

function selectGenealogyThread(threadId, fitPath = true) {{
  clearGenealogyHighlight(false);
  genealogyActiveThread = threadId;
  const thread = GENEALOGY_THREADS[threadId];
  const ids = thread.steps.map(item => item.id);
  genealogyHighlightedIds = new Set(ids);
  genealogyOriginalPositions = network.getPositions(ids);
  const color = thread.color;
  nodesDS.update(ids.map(id => {{
    const n = genealogyBaseNode(id);
    return {{id, color: {{background: color, border: '#ffffff', highlight: {{background: '#ffffff', border: color}}}}, borderWidth: 6, size: Math.max(30, n.size + 11), font: {{size: 15, color: '#ffffff', face: 'Segoe UI', bold: true, strokeWidth: 4, strokeColor: '#0f0f1a'}}, opacity: 1, shadow: {{enabled: true, color, size: 22, x: 0, y: 0}}, fixed: {{x: true, y: true}}, hidden: false}};
  }}));
  const spacing = 220;
  ids.forEach((id, i) => {{
    const x = (i - (ids.length - 1) / 2) * spacing;
    const y = i % 2 === 0 ? -96 : 96;
    network.moveNode(id, x, y);
  }});
  thread.steps.slice(0, -1).forEach((item, i) => {{
    const id = `genealogy-overlay-${{threadId}}-${{i}}`; genealogyOverlayEdgeIds.push(id);
    edgesDS.add({{id, from: item.id, to: thread.steps[i + 1].id, label: '', width: 8, color: {{color, opacity: 1}}, arrows: {{to: {{enabled: true, scaleFactor: 1.05}}}}, smooth: {{enabled: true, type: 'curvedCW', roundness: .11}}, shadow: {{enabled: true, color, size: 17, x: 0, y: 0}}, title: `${{thread.label}}: curated INFERRED lineage`, _genealogy: true}});
  }});
  document.querySelectorAll('.genealogy-button').forEach(btn => btn.classList.toggle('active', btn.dataset.thread === threadId));
  renderGenealogySteps(thread);
  if (fitPath) network.fit({{nodes: ids, animation: {{duration: 900, easingFunction: 'easeInOutQuad'}}}});
  network.redraw();
}}

function initializeGenealogyPanel() {{
  const buttons = document.getElementById('genealogy-buttons');
  buttons.innerHTML = Object.entries(GENEALOGY_THREADS).map(([id, t]) => `<button class="genealogy-button" data-thread="${{id}}" style="--thread-color:${{t.color}}">${{esc(t.label)}} (${{t.steps.length}})</button>`).join('');
  buttons.querySelectorAll('.genealogy-button').forEach(btn => btn.addEventListener('click', () => selectGenealogyThread(btn.dataset.thread)));
  selectGenealogyThread('shadow_visibility', true);
}}
initializeGenealogyPanel();
// LONGITUDINAL_GENEALOGY_SCRIPT_END
"""


def inject_overlay(html_path: Path) -> None:
    html = html_path.read_text(encoding="utf-8-sig")
    html = re.sub(r"<title>.*?</title>", "<title>중견 연구 계보 2022–2026</title>", html, count=1)
    html = html.replace("</style>", overlay_css() + "\n</style>", 1)
    html = html.replace('  <div id="info-panel">', overlay_panel() + '\n  <div id="info-panel">', 1)
    anchor = "\n</script>\n<script>\n// Render hyperedges as shaded regions"
    if anchor not in html:
        raise RuntimeError("Graphify HTML script insertion anchor not found")
    html = html.replace(anchor, overlay_script() + anchor, 1)
    html_path.write_text(html, encoding="utf-8")


def make_summary(output_root: Path, audit: dict) -> str:
    graph_uri = (output_root / "graphify-out" / "graph.html").as_uri()
    lines = [
        "---",
        "type: longitudinal-research-genealogy",
        f"updated: {date.today().isoformat()}",
        "years: [2022, 2023, 2024, 2025, 2026]",
        "tags: [연구노트, graphify, 계보]",
        "---",
        "",
        "# 중견 연구 계보 요약 (2022–2026)",
        "",
        "연차별 Graphify 그래프를 합치고, 날짜와 연구 주제의 연속성이 확인되는 연결을 별도의 편집 계보로 표시했다. 기존 연차 그래프의 관계는 그대로 보존했으며, 연차 사이 연결은 모두 `INFERRED`, `semantic_edge: false`로 구분했다.",
        "",
        "## 대화형 계보 그래프",
        "",
        f"- [2022–2026 연구 계보 graph.html](<{graph_uri}>)",
        "- [Graphify 보고서](graphify-out/GRAPH_REPORT.md)",
        "- [원시 그래프](graphify-out/graph.json)",
        "- [계보 감사 데이터](graphify-out/genealogy.json)",
        "",
        "그래프 왼쪽에서 계보를 선택하면 관련 노드와 연결만 밝고 굵게 강조된다. 주변 노드와 관계는 원래 밝기로 유지된다.",
        "",
        "## 추적된 네 계보",
        "",
    ]
    for thread in THREADS.values():
        lines.append(f"### {thread['label']}")
        lines.append("")
        lines.append(" → ".join(item["phase"] for item in thread["steps"]))
        lines.append("")
    lines += [
        "## 논리적 해석",
        "",
        "- 가장 연속적인 축은 `지지체적 오차·보정 → 방향/가시성 근사 → Shadow Tensor → TOMO 비교 → SFTF 후보 방향 → 독립 slicer 검증`이다.",
        "- 메쉬 분할 계보는 2022년의 가능성 조사에서 2025년의 실제 분할·군집 방법으로 이어지고, 2026년 SFTF-Clustering에서 지지 목적함수와 결합된다.",
        "- AI 협업은 기존 계보를 새로 만든 출발점이라기보다, 2022–2025년에 축적된 실패·근사·검증 기록을 빠르게 재구성하여 SFTF/PFTF로 명명하고 주장 범위를 교정한 촉매로 해석하는 편이 정확하다.",
        "",
        "## 남아 있는 논리 공백",
        "",
        "- 2024년 기록은 날짜 제목 페이지가 9개뿐이어서 2023→2025 전이의 중간 증거가 상대적으로 희박하다.",
        "- 2025년의 Shadow Tensor-Heat 유추가 실제 SFTF 수식 유도에 직접 사용됐다는 문서는 아직 확인되지 않아 그 연결은 낮은 강도의 편집 추론이다.",
        "- 2022년 메쉬 분할 조사와 2025년 MeshCNN·graph clustering 사이에는 구현 계승을 입증하는 직접 링크가 없으므로 개념 계보로만 표시했다.",
        "- PFTF 응용은 2026년에 빠르게 분기했으므로, 각 응용마다 `제안 → trusted solver → held-out 검증` 고리가 실제로 닫혔는지 별도 확인이 필요하다.",
        "",
        "## 감사 정보",
        "",
        f"- 원 그래프 노드: {audit['base_nodes']}",
        f"- 원 그래프 관계: {audit['base_edges']}",
        f"- 편집 계보 구간: {audit['curated_links']} (별도 `INFERRED` 관계 {audit['curated_edges']}개 + 기존 관계와 겹치는 구간; semantic edge 아님)",
        f"- 보존된 hyperedge: {audit['hyperedges']}",
    ]
    return "\n".join(lines) + "\n"


def update_index(index_path: Path, output_root: Path) -> None:
    if not index_path.exists():
        return
    text = index_path.read_text(encoding="utf-8-sig")
    start = "<!-- LONGITUDINAL_GENEALOGY_LINK_START -->"
    end = "<!-- LONGITUDINAL_GENEALOGY_LINK_END -->"
    block = (
        f"{start}\n"
        "## 2022–2026 통합 연구 계보\n\n"
        f"- 요약: [[{OUTPUT_FOLDER}/{SUMMARY_NAME.removesuffix('.md')}]]\n"
        f"- 대화형 그래프: [graph.html](<{(output_root / 'graphify-out' / 'graph.html').as_uri()}>)\n"
        "- 계보 연결은 날짜·주제 연속성에 따른 `INFERRED` 편집 오버레이이며, 원래 Graphify 관계와 구분된다.\n"
        f"{end}\n"
    )
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(block, text, count=1)
    else:
        heading = re.search(r"^# .+$", text, flags=re.MULTILINE)
        insert_at = heading.end() if heading else 0
        text = text[:insert_at] + "\n\n" + block + text[insert_at:]
    index_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vault_root", type=Path, help="Obsidian 연구노트 folder")
    parser.add_argument("--project-index", type=Path)
    args = parser.parse_args()

    vault_root = args.vault_root.resolve()
    output_root = vault_root / OUTPUT_FOLDER
    out = output_root / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)

    extraction, communities, audit = load_year_graphs(vault_root)
    (out / ".graphify_extract.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
    diagnostics = diagnose_extraction(extraction, directed=False, root=vault_root, extract_path=out / ".graphify_extract.json")
    (out / "diagnostics.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")

    graph = build_from_json(extraction, directed=False, root=vault_root)
    labels = {index: section for index, (_, section) in enumerate(SECTIONS)}
    cohesion = score_all(graph, communities)
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)
    if not to_json(graph, communities, str(out / "graph.json"), force=True, community_labels=labels):
        raise RuntimeError("Graphify declined to write longitudinal graph.json")

    detection = {
        "total_files": sum(item["nodes"] for item in audit["year_counts"].values()),
        "total_words": 0,
        "files": {"document": [section for _, section in SECTIONS]},
    }
    report = generate(
        graph, communities, cohesion, labels, gods, surprises, detection,
        {"input": 0, "output": 0, "note": "reuse of existing year graphs"},
        str(vault_root), suggested_questions=questions,
    )
    provenance_note = (
        "\n## Longitudinal Provenance\n\n"
        "Cross-year `curated_lineage` edges are editorial INFERRED links based on date and topic continuity; "
        "they are not Graphify-extracted semantic edges. See `genealogy.json` and the vault summary for the audit trail.\n"
    )
    (out / "GRAPH_REPORT.md").write_text(report + provenance_note, encoding="utf-8")
    (out / ".graphify_labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    to_html(graph, communities, str(out / "graph.html"), community_labels=labels)
    inject_overlay(out / "graph.html")

    genealogy = {
        "kind": "curated_longitudinal_genealogy",
        "semantic_edge": False,
        "confidence": "INFERRED",
        "audit": audit,
        "threads": THREADS,
        "diagnostics": diagnostics,
    }
    (out / "genealogy.json").write_text(json.dumps(genealogy, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / ".graphify_python").write_text(str(Path(__import__("sys").executable)), encoding="utf-8")
    (out / ".graphify_root").write_text(str(vault_root), encoding="utf-8")
    (out / "cost.json").write_text(json.dumps({"input": 0, "output": 0, "note": "merged existing graphs; no new semantic extraction"}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "build-summary.json").write_text(json.dumps({**audit, "diagnostics": diagnostics, "god_nodes": gods, "surprising_connections": surprises, "suggested_questions": questions}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_root / SUMMARY_NAME).write_text(make_summary(output_root, audit), encoding="utf-8")

    update_index(vault_root / INDEX_NAME, output_root)
    if args.project_index:
        update_index(args.project_index.resolve(), output_root)

    print(json.dumps({
        "output": str(output_root),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "hyperedges": len(extraction["hyperedges"]),
        "curated_edges": audit["curated_edges"],
        "dangling": diagnostics.get("dangling_endpoint_edges", 0),
        "self_loops": diagnostics.get("self_loop_edges", 0),
        "collapsed": diagnostics.get("undirected_same_endpoint_collapsed_edges", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
