"""Add a coordinate-free research-transfer gate overlay to Graphify HTML.

The teal path is a curated analytical checklist derived from the graph.  It is
not added to graph.json and must not be mistaken for an extracted causal path.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


GATE_STEPS = [
    {
        "id": "graph_corpus_029_2026_06_28_chatgpt__source_response_tensor",
        "phase": "1. 비대칭 구조 확인",
        "detail": "source와 response가 구분되며 최종 수식에서도 비대칭 정보가 살아남는지 확인",
        "source": "023 2026-06-28 chatGPT_ 비대칭텐서 문제.md",
    },
    {
        "id": "graph_corpus_046_2026_07_05_cfmsgccode_observability_gap",
        "phase": "2. 관측가능성 Gate",
        "detail": "목표 판정변수와 설계 의도가 실제 입력에서 관측 가능한지 확인",
        "source": "039 2026-07-05 cfmsGCCode 다시 시작.md",
    },
    {
        "id": "graph_corpus_048_2026_07_08_pftf_kdop_narrow_phase_cost_scaling",
        "phase": "3. 병목 일치 Gate",
        "detail": "줄이려는 연산이 실제 wall-clock 병목을 지배하는지 확인",
        "source": "041 2026-07-08 PFTF_kDOP의 novelty.md",
    },
    {
        "id": "graph_corpus_033_2026_06_28_sftf___cura_slicer_validation",
        "phase": "4. 독립 검증 Gate",
        "detail": "내부 proxy와 분리된 trusted solver 또는 물리 ground truth로 평가",
        "source": "027 2026-06-28 SFTF - Derivative.md",
    },
    {
        "id": "graph_corpus_042_2026_07_03_sftf_group_e_int16_overflow_masking",
        "phase": "5. 반증·오류 감사",
        "detail": "버그와 음성 결과가 기존 우위를 은폐했는지 provenance 기준으로 재검사",
        "source": "035 2026-07-03 Sftf group e 오류 발견.md",
    },
    {
        "id": "graph_corpus_042_2026_07_03_sftf_group_e_organic_scope_reframing",
        "phase": "6. 주장 범위 제한",
        "detail": "실패 조건을 보존하고 방어 가능한 적용 범위로 주장을 재프레이밍",
        "source": "035 2026-07-03 Sftf group e 오류 발견.md",
    },
]


CSS = r"""
/* RESEARCH_TRANSFER_GATE_OVERLAY_START */
#transfer-gate-panel { padding: 11px 12px; border-bottom: 1px solid #244d4d; background: linear-gradient(135deg, #102b2b 0%, #171a2b 76%); }
#transfer-gate-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
#transfer-gate-head h3 { font-size: 13px; color: #56e0d3; letter-spacing: .03em; }
#transfer-gate-toggle { border: 1px solid #56e0d3; color: #102323; background: #56e0d3; border-radius: 5px; padding: 4px 8px; font-weight: 700; cursor: pointer; }
#transfer-gate-toggle.off { color: #56e0d3; background: transparent; }
#transfer-gate-note { margin: 7px 0; color: #8db9b5; font-size: 10px; line-height: 1.35; }
#transfer-gate-steps { max-height: 178px; overflow-y: auto; padding-right: 3px; }
.transfer-gate-step { display: grid; grid-template-columns: 22px 1fr; gap: 7px; padding: 5px 3px; border-radius: 5px; cursor: pointer; }
.transfer-gate-step:hover, .transfer-gate-step.active { background: rgba(86, 224, 211, .12); }
.transfer-gate-index { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; background: #56e0d3; color: #102323; font-size: 10px; font-weight: 800; }
.transfer-gate-phase { color: #d9fffb; font-size: 11px; font-weight: 700; }
.transfer-gate-detail { color: #82aaa7; font-size: 9px; line-height: 1.3; margin-top: 2px; }
/* RESEARCH_TRANSFER_GATE_OVERLAY_END */
"""


PANEL = r"""
  <!-- RESEARCH_TRANSFER_GATE_PANEL_START -->
  <div id="transfer-gate-panel">
    <div id="transfer-gate-head">
      <h3>연구 전이 Gate</h3>
      <button id="transfer-gate-toggle" class="off" type="button">Gate OFF</button>
    </div>
    <div id="transfer-gate-note">청록색 경로는 Graphify가 추출한 인과 edge가 아니라, 여러 프로젝트의 성공·실패 기록에서 정리한 재사용 연구 점검표입니다.</div>
    <div id="transfer-gate-steps"></div>
  </div>
  <!-- RESEARCH_TRANSFER_GATE_PANEL_END -->
"""


def gate_script() -> str:
    steps = json.dumps(GATE_STEPS, ensure_ascii=False)
    return f"""
// RESEARCH_TRANSFER_GATE_SCRIPT_START
const TRANSFER_GATE_STEPS = {steps};
const TRANSFER_GATE_IDS = TRANSFER_GATE_STEPS.map(step => step.id);
const TRANSFER_GATE_ID_SET = new Set(TRANSFER_GATE_IDS);
const TRANSFER_GATE_EDGE_IDS = [];
let transferGateMode = false;

function renderTransferGateSteps() {{
  const wrap = document.getElementById('transfer-gate-steps');
  wrap.innerHTML = TRANSFER_GATE_STEPS.map((step, i) => `
    <div class="transfer-gate-step" data-transfer-gate-id="${{esc(step.id)}}">
      <span class="transfer-gate-index">${{i + 1}}</span>
      <span><div class="transfer-gate-phase">${{esc(step.phase)}}</div><div class="transfer-gate-detail">${{esc(step.detail)}}</div></span>
    </div>`).join('');
  wrap.querySelectorAll('.transfer-gate-step').forEach(el => {{
    el.addEventListener('click', () => {{
      const id = el.dataset.transferGateId;
      network.focus(id, {{scale: network.getScale(), animation: true}});
      network.selectNodes([id]);
      showInfo(id);
      wrap.querySelectorAll('.transfer-gate-step').forEach(x => x.classList.toggle('active', x === el));
    }});
  }});
}}

function transferGateEdgeData() {{
  return TRANSFER_GATE_STEPS.slice(0, -1).map((step, i) => {{
    const next = TRANSFER_GATE_STEPS[i + 1];
    const id = `research-transfer-gate-${{i}}`;
    TRANSFER_GATE_EDGE_IDS.push(id);
    return {{
      id, from: step.id, to: next.id,
      label: '',
      title: `${{step.phase}} → ${{next.phase}} (curated analytical gate; not an extracted causal edge)`,
      width: 7,
      color: {{color: '#56e0d3', opacity: 1}},
      arrows: {{to: {{enabled: true, scaleFactor: 1.05}}}},
      smooth: {{enabled: true, type: 'curvedCCW', roundness: 0.16}},
      shadow: {{enabled: true, color: 'rgba(86,224,211,.72)', size: 17, x: 0, y: 0}},
      dashes: [12, 5],
      _transferGate: true,
    }};
  }});
}}

function restoreTransferGateNodes() {{
  nodesDS.update(RAW_NODES.filter(n => TRANSFER_GATE_ID_SET.has(n.id)).map(n => ({{
    id: n.id,
    color: n.color,
    borderWidth: 1.5,
    size: n.size,
    font: n.font,
    opacity: 1,
    shadow: false,
  }})));
  if (typeof journeyMode !== 'undefined' && journeyMode && typeof setJourneyMode === 'function') {{
    setJourneyMode(true);
  }}
}}

function applyTransferGateNodeStyles() {{
  nodesDS.update(RAW_NODES.filter(n => TRANSFER_GATE_ID_SET.has(n.id)).map(n => ({{
    id: n.id,
    color: {{background: '#1f9f98', border: '#a6fff7', highlight: {{background: '#56e0d3', border: '#ffffff'}}}},
    borderWidth: 6,
    size: Math.max(30, n.size + 11),
    font: {{size: 15, color: '#ffffff', face: 'Segoe UI', bold: true, strokeWidth: 4, strokeColor: '#071616'}},
    opacity: 1,
    shadow: {{enabled: true, color: 'rgba(86,224,211,.82)', size: 22, x: 0, y: 0}},
    hidden: false,
  }})));
}}

function setTransferGateMode(enabled) {{
  transferGateMode = enabled;
  const btn = document.getElementById('transfer-gate-toggle');
  btn.textContent = enabled ? 'Gate ON' : 'Gate OFF';
  btn.classList.toggle('off', !enabled);
  TRANSFER_GATE_EDGE_IDS.splice(0).forEach(id => edgesDS.remove(id));
  if (enabled) {{
    applyTransferGateNodeStyles();
    edgesDS.add(transferGateEdgeData());
  }} else {{
    restoreTransferGateNodes();
  }}
  network.redraw();
}}

renderTransferGateSteps();
document.getElementById('transfer-gate-toggle').addEventListener('click', () => setTransferGateMode(!transferGateMode));
const journeyToggleForGate = document.getElementById('journey-toggle');
if (journeyToggleForGate) {{
  journeyToggleForGate.addEventListener('click', () => {{
    if (transferGateMode) setTimeout(() => {{ applyTransferGateNodeStyles(); network.redraw(); }}, 0);
  }});
}}
// RESEARCH_TRANSFER_GATE_SCRIPT_END
"""


def strip_existing_gate(html: str) -> str:
    patterns = [
        r"\n?/\* RESEARCH_TRANSFER_GATE_OVERLAY_START \*/.*?/\* RESEARCH_TRANSFER_GATE_OVERLAY_END \*/\n?",
        r"\n?  <!-- RESEARCH_TRANSFER_GATE_PANEL_START -->.*?<!-- RESEARCH_TRANSFER_GATE_PANEL_END -->\n?",
        r"\n?// RESEARCH_TRANSFER_GATE_SCRIPT_START.*?// RESEARCH_TRANSFER_GATE_SCRIPT_END\n?",
    ]
    for pattern in patterns:
        html = re.sub(pattern, "\n", html, flags=re.DOTALL)
    return html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("--gate-json", type=Path)
    args = parser.parse_args()

    html_path = args.html.resolve()
    html = strip_existing_gate(html_path.read_text(encoding="utf-8-sig"))
    raw_match = re.search(r"const RAW_NODES = (\[.*?\]);\s*const RAW_EDGES", html, flags=re.DOTALL)
    if not raw_match:
        raise RuntimeError("RAW_NODES block not found")
    available = {node["id"] for node in json.loads(raw_match.group(1))}
    missing = [step["id"] for step in GATE_STEPS if step["id"] not in available]
    if missing:
        raise RuntimeError(f"Transfer-gate node IDs missing from graph: {missing}")

    html = html.replace("</style>", CSS + "\n</style>", 1)
    panel_anchor = "  <!-- RESEARCH_JOURNEY_PANEL_END -->"
    if panel_anchor in html:
        html = html.replace(panel_anchor, panel_anchor + "\n" + PANEL, 1)
    else:
        html = html.replace('  <div id="info-panel">', PANEL + '\n  <div id="info-panel">', 1)

    script_anchor = "\n</script>\n<script>\n// Render hyperedges as shaded regions"
    if script_anchor not in html:
        raise RuntimeError("Graphify script insertion anchor not found")
    html = html.replace(script_anchor, gate_script() + script_anchor, 1)
    html_path.write_text(html, encoding="utf-8")

    gate_path = args.gate_json or html_path.with_name("research-transfer-gate.json")
    gate_path.write_text(
        json.dumps(
            {
                "kind": "curated_research_transfer_gate",
                "semantic_edge": False,
                "title": "재사용 가능한 연구 전이 Gate",
                "warning": "이 경로는 분석적 체크리스트이며 Graphify가 추출한 인과 경로가 아니다.",
                "steps": GATE_STEPS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Added {len(GATE_STEPS)} transfer-gate steps to {html_path}")


if __name__ == "__main__":
    main()
