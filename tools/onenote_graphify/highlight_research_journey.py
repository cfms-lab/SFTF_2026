"""Add a strong, explicitly curated research-journey overlay to graph.html.

The gold path is chronological editorial metadata, not a Graphify semantic
edge.  The base graph and graph.json remain untouched.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEAT_CONTEXT_ID = "editorial_2025_07_09_heat_map_shadow_tensor"
HEAT_CONTEXT_NODE = {
    "id": HEAT_CONTEXT_ID,
    "label": "2025 Heat-map 행렬 기반 Shadow Tensor 아이디어",
    "color": {
        "background": "#ff9f43",
        "border": "#ffd6a5",
        "highlight": {"background": "#ffd6a5", "border": "#ffffff"},
    },
    "size": 18.0,
    "font": {"size": 12, "color": "#ffffff"},
    "title": (
        "2025-07-09 선행 아이디어 (AMBIGUOUS precursor)\n"
        "Heat-map 행렬을 풀듯 Shadow Tensor를 계산할 수 있을지 제안한 ToDo.\n"
        "2026 SFTF 유도에 직접 사용됐다는 문서 증거는 아직 없음."
    ),
    "community": -1,
    "community_name": "편집 선행 아이디어",
    "source_file": "중견4차년도(2025)/graph-corpus/038 2025-07-09 Bone활용(4).md:59",
    "file_type": "editorial_context",
    "degree": 1,
}


JOURNEY_STEPS = [
    {
        "id": HEAT_CONTEXT_ID,
        "date": "2025-07-09",
        "phase": "Heat-map 선행 아이디어",
        "detail": "Shadow Tensor를 Heat-map 행렬처럼 풀 수 있을지 제안한 미확인 선행 직관",
        "confidence": "AMBIGUOUS",
        "semantic_edge": False,
    },
    {
        "id": "004_2026_05_19_whichllm_test_note",
        "date": "2026-05-19",
        "phase": "AI 도구 탐색",
        "detail": "문제와 장비에 맞는 LLM을 비교하며 AI 협업 방식을 잡음",
    },
    {
        "id": "005_2026_05_20_shadow_tensor_shadow_tensor",
        "date": "2026-05-20",
        "phase": "기존 문제 복기",
        "detail": "가시성과 occlusion 문제를 Shadow Tensor로 다시 구조화",
    },
    {
        "id": "008_shadow_tensor_mathematica_note",
        "date": "2026-05-29–06-15",
        "phase": "연속 계산 실험",
        "detail": "Mathematica 실험을 반복해 아이디어의 형태와 실패 조건을 탐색",
    },
    {
        "id": "012_2026_06_19_eigenvector_tomo_sftf_validation",
        "date": "2026-06-19",
        "phase": "SFTF 정식화·초기 검증",
        "detail": "Support Tensor와 eigenvector 방향 후보를 TOMO 결과와 비교",
    },
    {
        "id": "graph_corpus_025_2026_06_24_codex__paper_review_note",
        "date": "2026-06-24",
        "phase": "AI 비판으로 주장 교정",
        "detail": "최종 솔버 주장을 후보 생성기·warm-start 포지셔닝으로 제한",
    },
    {
        "id": "graph_corpus_029_2026_06_28_chatgpt__source_response_tensor",
        "date": "2026-06-27–28",
        "phase": "핵심 개념 추상화·파생",
        "detail": "source–response 비대칭 텐서로 Cluster·Soft·사출·Drape를 연결",
    },
    {
        "id": "graph_corpus_033_2026_06_28_sftf___cura_slicer_validation",
        "date": "2026-06-28–07-02",
        "phase": "독립 도구 검증",
        "detail": "TomoNV 내부 비교를 넘어 Cura 지지량으로 검증 사다리를 확립",
    },
    {
        "id": "graph_corpus_043_2026_07_03_vss_int16_document",
        "date": "2026-07-03–04",
        "phase": "오류·음성 결과 수용",
        "detail": "int16 오류 수정 뒤 원고와 적용 범위를 다시 평가",
    },
    {
        "id": "graph_corpus_048_2026_07_08_pftf_kdop_document",
        "date": "2026-07-08",
        "phase": "PFTF로 개념 전이",
        "detail": "방향 컬링·접촉장·압박밴드로 문제 구조를 확장",
    },
    {
        "id": "graph_corpus_051_2026_07_09_sftf_pftf_document",
        "date": "2026-07-09",
        "phase": "신규성 경계 정리",
        "detail": "기존 수학과 문제·관찰·정식화의 신규성을 분리",
    },
    {
        "id": "graph_corpus_058_2026_07_14_re100_document",
        "date": "2026-07-14",
        "phase": "새 연구주제로 재적용",
        "detail": "RE100 입지 문제에 PFTF와 held-out 검증 사다리를 적용",
    },
]


CSS = r"""
/* RESEARCH_JOURNEY_OVERLAY_START */
#journey-panel { padding: 12px; border-bottom: 1px solid #3d321d; background: linear-gradient(135deg, #251f12 0%, #1a1a2e 72%); }
#journey-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
#journey-head h3 { font-size: 13px; color: #ffd166; letter-spacing: .03em; }
#journey-toggle { border: 1px solid #ffd166; color: #1a1a2e; background: #ffd166; border-radius: 5px; padding: 4px 8px; font-weight: 700; cursor: pointer; }
#journey-toggle.off { color: #ffd166; background: transparent; }
#journey-note { margin: 7px 0; color: #b9a77a; font-size: 10px; line-height: 1.35; }
#journey-steps { max-height: 204px; overflow-y: auto; padding-right: 3px; }
.journey-step { display: grid; grid-template-columns: 22px 1fr; gap: 7px; padding: 5px 3px; border-radius: 5px; cursor: pointer; }
.journey-step:hover, .journey-step.active { background: rgba(255, 209, 102, .12); }
.journey-index { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; background: #ffd166; color: #1a1a2e; font-size: 10px; font-weight: 800; }
.journey-step.ambiguous .journey-index { background: #ff9f43; }
.journey-step.ambiguous .journey-phase::after { content: ' · 미확인 선행 직관'; color: #ffb76b; font-size: 8px; font-weight: 500; }
.journey-date { color: #d6c38e; font-size: 9px; }
.journey-phase { color: #fff4cf; font-size: 11px; font-weight: 700; }
.journey-detail { color: #93886b; font-size: 9px; line-height: 1.3; margin-top: 2px; }
#journey-template { margin-top: 7px; padding-top: 7px; border-top: 1px solid #3d321d; color: #a89b78; font-size: 9px; line-height: 1.4; }
/* RESEARCH_JOURNEY_OVERLAY_END */
"""


PANEL = r"""
  <!-- RESEARCH_JOURNEY_PANEL_START -->
  <div id="journey-panel">
    <div id="journey-head">
      <h3>AI → SFTF/PFTF 연구 여정</h3>
      <button id="journey-toggle" type="button">강조 ON</button>
    </div>
    <div id="journey-note">금색선은 Graphify가 추출한 인과 edge가 아니라 날짜 기록을 바탕으로 구성한 연구 여정 오버레이입니다. 첫 Heat-map 노드는 2026 SFTF에 직접 사용됐다는 증거가 없는 AMBIGUOUS 선행 아이디어입니다.</div>
    <div id="journey-steps"></div>
    <div id="journey-template">재사용 흐름: 미확인 선행 직관 → AI 도구 탐색 → 문제 복기 → 반복 실험 → 정식화 → 비판 → 독립 검증 → 오류 수용 → 주장 제한 → 도메인 전이</div>
  </div>
  <!-- RESEARCH_JOURNEY_PANEL_END -->
"""


def journey_script() -> str:
    steps = json.dumps(JOURNEY_STEPS, ensure_ascii=False)
    return f"""
// RESEARCH_JOURNEY_SCRIPT_START
const JOURNEY_STEPS = {steps};
const JOURNEY_IDS = JOURNEY_STEPS.map(step => step.id);
const JOURNEY_ID_SET = new Set(JOURNEY_IDS);
const JOURNEY_STEP_BY_ID = new Map(JOURNEY_STEPS.map(step => [step.id, step]));
const JOURNEY_EDGE_IDS = [];
let journeyMode = false;

function renderJourneySteps() {{
  const wrap = document.getElementById('journey-steps');
  wrap.innerHTML = JOURNEY_STEPS.map((step, i) => `
    <div class="journey-step ${{step.confidence === 'AMBIGUOUS' ? 'ambiguous' : ''}}" data-journey-id="${{esc(step.id)}}">
      <span class="journey-index">${{i + 1}}</span>
      <span><div class="journey-date">${{esc(step.date)}}</div><div class="journey-phase">${{esc(step.phase)}}</div><div class="journey-detail">${{esc(step.detail)}}</div></span>
    </div>`).join('');
  wrap.querySelectorAll('.journey-step').forEach(el => {{
    el.addEventListener('click', () => {{
      const id = el.dataset.journeyId;
      network.focus(id, {{scale: network.getScale(), animation: true}});
      network.selectNodes([id]);
      showInfo(id);
      wrap.querySelectorAll('.journey-step').forEach(x => x.classList.toggle('active', x === el));
    }});
  }});
}}

function journeyEdgeData() {{
  return JOURNEY_STEPS.slice(0, -1).map((step, i) => {{
    const next = JOURNEY_STEPS[i + 1];
    const id = `research-journey-${{i}}`;
    JOURNEY_EDGE_IDS.push(id);
    return {{
      id, from: step.id, to: next.id,
      label: '',
      title: step.confidence === 'AMBIGUOUS'
        ? `${{step.date}} ${{step.phase}} → ${{next.date}} ${{next.phase}} (AMBIGUOUS editorial precursor; no direct-use evidence)`
        : `${{step.date}} ${{step.phase}} → ${{next.date}} ${{next.phase}} (curated chronological overlay)`,
      width: step.confidence === 'AMBIGUOUS' ? 6 : 8,
      color: {{color: step.confidence === 'AMBIGUOUS' ? '#ff9f43' : '#ffd166', opacity: 1}},
      arrows: {{to: {{enabled: true, scaleFactor: 1.1}}}},
      smooth: {{enabled: true, type: 'curvedCW', roundness: 0.12}},
      shadow: {{enabled: true, color: step.confidence === 'AMBIGUOUS' ? 'rgba(255,159,67,.75)' : 'rgba(255,209,102,.75)', size: 18, x: 0, y: 0}},
      dashes: step.confidence === 'AMBIGUOUS' ? [9, 7] : false,
      _journey: true,
    }};
  }});
}}

function setJourneyMode(enabled) {{
  journeyMode = enabled;
  const btn = document.getElementById('journey-toggle');
  btn.textContent = enabled ? '강조 ON' : '강조 OFF';
  btn.classList.toggle('off', !enabled);

  if (enabled) {{
    // Highlight only the curated path.  Unrelated nodes and their edges remain
    // at their normal brightness so the surrounding research context is still
    // readable while the path is emphasized.  This is deliberately a
    // coordinate-free visual overlay: toggling it must preserve the relaxed
    // layout exactly as it is.
    nodesDS.update(RAW_NODES.filter(n => JOURNEY_ID_SET.has(n.id)).map(n => {{
      const step = JOURNEY_STEP_BY_ID.get(n.id);
      const isAmbiguous = step && step.confidence === 'AMBIGUOUS';
      const color = isAmbiguous ? '#ff9f43' : '#ffd166';
      const border = isAmbiguous ? '#ffd6a5' : '#fff4cf';
      return {{
        id: n.id,
        color: {{background: color, border, highlight: {{background: border, border: '#ffffff'}}}},
        borderWidth: 6,
        size: Math.max(30, n.size + 11),
        font: {{size: 15, color: '#ffffff', face: 'Segoe UI', bold: true, strokeWidth: 4, strokeColor: '#0f0f1a'}},
        opacity: 1,
        shadow: {{enabled: true, color: isAmbiguous ? 'rgba(255,159,67,.8)' : 'rgba(255,209,102,.8)', size: 22, x: 0, y: 0}},
        hidden: false,
      }};
    }}));

    JOURNEY_EDGE_IDS.splice(0).forEach(id => edgesDS.remove(id));
    edgesDS.add(journeyEdgeData());
  }} else {{
    JOURNEY_EDGE_IDS.splice(0).forEach(id => edgesDS.remove(id));
    nodesDS.update(RAW_NODES.filter(n => JOURNEY_ID_SET.has(n.id)).map(n => ({{
      id: n.id,
      color: n.color,
      borderWidth: 1.5,
      size: n.size,
      font: n.font,
      opacity: 1,
      shadow: false,
    }})));
  }}
  network.redraw();
}}

renderJourneySteps();
document.getElementById('journey-toggle').addEventListener('click', () => setJourneyMode(!journeyMode));
// RESEARCH_JOURNEY_SCRIPT_END
"""


def strip_existing_overlay(html: str) -> str:
    patterns = [
        r"\n?/\* RESEARCH_JOURNEY_OVERLAY_START \*/.*?/\* RESEARCH_JOURNEY_OVERLAY_END \*/\n?",
        r"\n?  <!-- RESEARCH_JOURNEY_PANEL_START -->.*?<!-- RESEARCH_JOURNEY_PANEL_END -->\n?",
        r"\n?// RESEARCH_JOURNEY_SCRIPT_START.*?// RESEARCH_JOURNEY_SCRIPT_END\n?",
    ]
    for pattern in patterns:
        html = re.sub(pattern, "\n", html, flags=re.DOTALL)
    html = re.sub(
        r"\s*setTimeout\(\(\) => setJourneyMode\(true(?:,\s*true)?\), 80\);\n?",
        "\n",
        html,
    )
    return html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("--journey-json", type=Path)
    args = parser.parse_args()

    html_path = args.html.resolve()
    html = strip_existing_overlay(html_path.read_text(encoding="utf-8-sig"))

    raw_match = re.search(r"const RAW_NODES = (\[.*?\]);\nconst RAW_EDGES", html, flags=re.DOTALL)
    if not raw_match:
        raise RuntimeError("RAW_NODES block not found")
    raw_nodes = [
        node for node in json.loads(raw_match.group(1))
        if node.get("id") != HEAT_CONTEXT_ID
    ]
    raw_nodes.append(HEAT_CONTEXT_NODE)
    html = html[:raw_match.start(1)] + json.dumps(raw_nodes, ensure_ascii=False) + html[raw_match.end(1):]
    available = {node["id"] for node in raw_nodes}
    missing = [step["id"] for step in JOURNEY_STEPS if step["id"] not in available]
    if missing:
        raise RuntimeError(f"Journey node IDs missing from graph: {missing}")

    html = re.sub(r"<title>.*?</title>", "<title>중견5차년도(2026) — AI에서 SFTF/PFTF까지</title>", html, count=1)
    html = html.replace("</style>", CSS + "\n</style>", 1)
    html = html.replace('  <div id="info-panel">', PANEL + '\n  <div id="info-panel">', 1)
    html = html.replace(
        "  network.setOptions({ physics: { enabled: false } });\n",
        "  network.setOptions({ physics: { enabled: false } });\n  setTimeout(() => setJourneyMode(true), 80);\n",
        1,
    )
    anchor = "\n</script>\n<script>\n// Render hyperedges as shaded regions"
    if anchor not in html:
        raise RuntimeError("Graphify script insertion anchor not found")
    html = html.replace(anchor, journey_script() + anchor, 1)
    html_path.write_text(html, encoding="utf-8")

    journey_path = args.journey_json or html_path.with_name("research-journey.json")
    journey_path.write_text(
        json.dumps(
            {
                "kind": "curated_chronological_overlay",
                "semantic_edge": False,
                "title": "AI 사용에서 SFTF/PFTF 연구로 이어진 과정",
                "contains_editorial_context": True,
                "editorial_context_node": HEAT_CONTEXT_NODE,
                "reusable_pattern": [
                    "미확인 선행 직관",
                    "AI 도구 탐색",
                    "문제 복기",
                    "반복 계산 실험",
                    "수식·개념 정식화",
                    "AI 비판과 주장 교정",
                    "독립 도구 검증",
                    "오류·음성 결과 수용",
                    "주장 범위 제한",
                    "다른 도메인으로 전이",
                ],
                "steps": JOURNEY_STEPS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Highlighted {len(JOURNEY_STEPS)} journey steps in {html_path}")


if __name__ == "__main__":
    main()
