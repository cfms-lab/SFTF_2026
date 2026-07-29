"""Create a straight-axis comparison variant without modifying graph.html.

The union of the gold research-journey nodes and teal transfer-gate nodes is
placed on one chronological horizontal axis.  Hyperedge relaxation is adapted
so those axis nodes remain fixed while all hyperedge groups and unrelated
nodes are kept outside one another's envelopes.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


STRAIGHT_ORDER = [
    "editorial_2025_07_09_heat_map_shadow_tensor",
    "004_2026_05_19_whichllm_test_note",
    "005_2026_05_20_shadow_tensor_shadow_tensor",
    "008_shadow_tensor_mathematica_note",
    "012_2026_06_19_eigenvector_tomo_sftf_validation",
    "graph_corpus_025_2026_06_24_codex__paper_review_note",
    "graph_corpus_029_2026_06_28_chatgpt__source_response_tensor",
    "graph_corpus_033_2026_06_28_sftf___cura_slicer_validation",
    "graph_corpus_043_2026_07_03_vss_int16_document",
    "graph_corpus_042_2026_07_03_sftf_group_e_int16_overflow_masking",
    "graph_corpus_042_2026_07_03_sftf_group_e_organic_scope_reframing",
    "graph_corpus_046_2026_07_05_cfmsgccode_observability_gap",
    "graph_corpus_048_2026_07_08_pftf_kdop_document",
    "graph_corpus_048_2026_07_08_pftf_kdop_narrow_phase_cost_scaling",
    "graph_corpus_051_2026_07_09_sftf_pftf_document",
    "graph_corpus_058_2026_07_14_re100_document",
]


TARGET_RELAXATION_IDS = [
    "graph_corpus_059_2026_07_14_sftfsoft_diffsupport_t2_slicer_validation_gap",
    "graph_corpus_034_2026_06_29___soft_sftf_score",
    "graph_corpus_055_2026_07_11_physical_ai_parametric_data_factory",
    "graph_corpus_026_2026_06_26__dxf_seam_graph_matching",
    "graph_corpus_048_2026_07_08_pftf_kdop_differentiable_contact_field",
]


CSS = r"""
/* STRAIGHT_RESEARCH_LAYOUT_STYLE_START */
#straight-layout-note { padding: 8px 12px; border-bottom: 1px solid #39405c; color: #b8c2e6; background: #15192a; font-size: 10px; line-height: 1.4; }
#straight-layout-note strong { color: #ffffff; }
#edge-relax-status { margin-left: 6px; color: #8fe7c7; }
/* STRAIGHT_RESEARCH_LAYOUT_STYLE_END */
"""


PANEL = r"""
  <!-- STRAIGHT_RESEARCH_LAYOUT_PANEL_START -->
  <div id="straight-layout-note"><strong>직선형 비교본</strong> — 금색 연구 여정과 청록색 연구 전이 Gate의 합집합 16개 노드를 날짜 순 수평축에 고정했습니다. 두 경로는 편집·분석 오버레이이며 추출된 인과 edge가 아닙니다. <span id="edge-relax-status">edge 길이 relaxation 준비</span></div>
  <!-- STRAIGHT_RESEARCH_LAYOUT_PANEL_END -->
"""


def straight_script() -> str:
    order = json.dumps(STRAIGHT_ORDER, ensure_ascii=False)
    targets = json.dumps(TARGET_RELAXATION_IDS, ensure_ascii=False)
    return f"""
// STRAIGHT_RESEARCH_LAYOUT_SCRIPT_START
const STRAIGHT_LAYOUT_IDS = {order};
const STRAIGHT_LAYOUT_ID_SET = new Set(STRAIGHT_LAYOUT_IDS);
const TARGET_RELAXATION_IDS = {targets};
const TARGET_RELAXATION_ID_SET = new Set(TARGET_RELAXATION_IDS);
const STRAIGHT_LAYOUT_SPACING = 390;
let straightEdgeRelaxationRunning = false;
let straightEdgeRelaxationDone = false;
let straightOptimizedPositions = null;

function setStraightAxisPositions() {{
  const center = (STRAIGHT_LAYOUT_IDS.length - 1) / 2;
  STRAIGHT_LAYOUT_IDS.forEach((id, index) => {{
    network.moveNode(id, (index - center) * STRAIGHT_LAYOUT_SPACING, 0);
  }});
}}

function meanRawEdgeLength() {{
  const positions = network.getPositions();
  let total = 0, count = 0;
  RAW_EDGES.forEach(edge => {{
    const from = positions[edge.from], to = positions[edge.to];
    if (!from || !to) return;
    total += Math.hypot(to.x - from.x, to.y - from.y);
    count += 1;
  }});
  return count ? total / count : 0;
}}

function meanTargetEdgeLength() {{
  const positions = network.getPositions();
  let total = 0, count = 0;
  RAW_EDGES.forEach(edge => {{
    if (!TARGET_RELAXATION_ID_SET.has(edge.from) && !TARGET_RELAXATION_ID_SET.has(edge.to)) return;
    const from = positions[edge.from], to = positions[edge.to];
    if (!from || !to) return;
    total += Math.hypot(to.x - from.x, to.y - from.y);
    count += 1;
  }});
  return count ? total / count : 0;
}}

function edgeRelaxationWeight(edge, multiplier = 1) {{
  return multiplier * (edge.confidence === 'EXTRACTED' ? 2 : 1);
}}

// Weiszfeld relaxation minimizes the actual sum of edge lengths rather than
// the squared-length surrogate produced by an arithmetic barycenter.
function weightedGeometricMedian(samples, fallback) {{
  if (!samples.length) return {{x: fallback.x, y: fallback.y}};
  let weightSum = samples.reduce((sum, sample) => sum + sample.weight, 0) || 1;
  let point = {{
    x: samples.reduce((sum, sample) => sum + sample.x * sample.weight, 0) / weightSum,
    y: samples.reduce((sum, sample) => sum + sample.y * sample.weight, 0) / weightSum,
  }};
  for (let iteration = 0; iteration < 28; iteration++) {{
    let nx = 0, ny = 0, denominator = 0;
    for (const sample of samples) {{
      const distance = Math.max(0.001, Math.hypot(point.x - sample.x, point.y - sample.y));
      const scaled = sample.weight / distance;
      nx += sample.x * scaled;
      ny += sample.y * scaled;
      denominator += scaled;
    }}
    const next = {{x: nx / denominator, y: ny / denominator}};
    if (Math.hypot(next.x - point.x, next.y - point.y) < 0.05) return next;
    point = next;
  }}
  return point;
}}

function cappedMove(from, to, fraction, maximum) {{
  let dx = (to.x - from.x) * fraction;
  let dy = (to.y - from.y) * fraction;
  const distance = Math.hypot(dx, dy);
  if (distance > maximum) {{ dx *= maximum / distance; dy *= maximum / distance; }}
  return {{x: from.x + dx, y: from.y + dy}};
}}

function hyperedgeGeometry(h, positions) {{
  const members = h.nodes.filter(id => positions[id]);
  if (!members.length) return null;
  const center = {{
    x: members.reduce((sum, id) => sum + positions[id].x, 0) / members.length,
    y: members.reduce((sum, id) => sum + positions[id].y, 0) / members.length,
  }};
  const nominalRadius = 90 + Math.max(0, members.length - 4) * 12;
  const occupiedRadius = members.reduce(
    (maximum, id) => Math.max(maximum, Math.hypot(positions[id].x - center.x, positions[id].y - center.y)),
    nominalRadius,
  );
  return {{members, center, nominalRadius, occupiedRadius}};
}}

function projectOutsideUnrelatedHyperedges(id, point, currentPosition) {{
  let projected = {{x: point.x, y: point.y}};
  for (let pass = 0; pass < 5; pass++) {{
    const positions = network.getPositions();
    hyperedges.forEach(h => {{
      if (h.nodes.includes(id)) return;
      const geometry = hyperedgeGeometry(h, positions);
      if (!geometry) return;
      let dx = projected.x - geometry.center.x;
      let dy = projected.y - geometry.center.y;
      let distance = Math.hypot(dx, dy);
      const minimum = geometry.occupiedRadius + HYPEREDGE_HULL_PADDING + 64;
      if (distance >= minimum) return;
      if (distance < 0.001) {{
        dx = currentPosition.x - geometry.center.x;
        dy = currentPosition.y - geometry.center.y;
        distance = Math.hypot(dx, dy);
      }}
      if (distance < 0.001) {{ dx = 1; dy = 0; distance = 1; }}
      projected.x = geometry.center.x + dx / distance * (minimum + 6);
      projected.y = geometry.center.y + dy / distance * (minimum + 6);
    }});
  }}
  return projected;
}}

function shiftTargetHyperedgeGroups() {{
  const positions = network.getPositions();
  hyperedges.forEach(h => {{
    if (!h.nodes.some(id => TARGET_RELAXATION_ID_SET.has(id))) return;
    if (h.nodes.some(id => STRAIGHT_LAYOUT_ID_SET.has(id))) return;
    const geometry = hyperedgeGeometry(h, positions);
    if (!geometry) return;
    const memberSet = new Set(geometry.members);
    const samples = [];
    RAW_EDGES.forEach(edge => {{
      let memberId = null, neighborId = null;
      if (memberSet.has(edge.from) && !memberSet.has(edge.to)) {{ memberId = edge.from; neighborId = edge.to; }}
      else if (memberSet.has(edge.to) && !memberSet.has(edge.from)) {{ memberId = edge.to; neighborId = edge.from; }}
      if (!memberId || !positions[memberId] || !positions[neighborId]) return;
      const memberOffset = {{
        x: positions[memberId].x - geometry.center.x,
        y: positions[memberId].y - geometry.center.y,
      }};
      samples.push({{
        x: positions[neighborId].x - memberOffset.x,
        y: positions[neighborId].y - memberOffset.y,
        weight: edgeRelaxationWeight(edge, TARGET_RELAXATION_ID_SET.has(memberId) ? 5 : 1),
      }});
    }});
    if (!samples.length) return;
    const desiredCenter = weightedGeometricMedian(samples, geometry.center);
    const nextCenter = cappedMove(geometry.center, desiredCenter, 0.58, 210);
    const dx = nextCenter.x - geometry.center.x;
    const dy = nextCenter.y - geometry.center.y;
    geometry.members.forEach(id => network.moveNode(id, positions[id].x + dx, positions[id].y + dy));
  }});
}}

function moveOrdinaryTargetNodes() {{
  const hyperedgeMembers = new Set(hyperedges.flatMap(h => h.nodes));
  TARGET_RELAXATION_IDS.forEach(id => {{
    if (hyperedgeMembers.has(id) || STRAIGHT_LAYOUT_ID_SET.has(id)) return;
    const positions = network.getPositions();
    const current = positions[id];
    if (!current) return;
    const samples = [];
    RAW_EDGES.forEach(edge => {{
      const neighborId = edge.from === id ? edge.to : (edge.to === id ? edge.from : null);
      if (!neighborId || !positions[neighborId]) return;
      samples.push({{...positions[neighborId], weight: edgeRelaxationWeight(edge)}});
    }});
    if (!samples.length) return;
    const desired = weightedGeometricMedian(samples, current);
    const candidate = cappedMove(current, desired, 0.82, 240);
    const projected = projectOutsideUnrelatedHyperedges(id, candidate, current);
    network.moveNode(id, projected.x, projected.y);
  }});
}}

function orientTargetHyperedgeMembers() {{
  const placed = [];
  hyperedges.forEach(h => {{
    const targetMembers = h.nodes.filter(id => TARGET_RELAXATION_ID_SET.has(id));
    if (!targetMembers.length) return;
    let positions = network.getPositions();
    const geometry = hyperedgeGeometry(h, positions);
    if (!geometry) return;
    const memberSet = new Set(geometry.members);
    targetMembers.forEach((id, targetIndex) => {{
      positions = network.getPositions();
      const samples = [];
      RAW_EDGES.forEach(edge => {{
        const neighborId = edge.from === id ? edge.to : (edge.to === id ? edge.from : null);
        if (!neighborId || memberSet.has(neighborId) || !positions[neighborId]) return;
        samples.push({{...positions[neighborId], weight: edgeRelaxationWeight(edge)}});
      }});
      if (!samples.length) return;
      const desired = weightedGeometricMedian(samples, positions[id]);
      let angle = Math.atan2(desired.y - geometry.center.y, desired.x - geometry.center.x);
      let radius = Math.min(geometry.nominalRadius * 0.84, Math.hypot(desired.x - geometry.center.x, desired.y - geometry.center.y));
      radius = Math.max(radius, geometry.nominalRadius * 0.58);
      let candidate = {{x: geometry.center.x + Math.cos(angle) * radius, y: geometry.center.y + Math.sin(angle) * radius}};
      for (let attempt = 0; attempt < 6 && placed.some(p => Math.hypot(candidate.x - p.x, candidate.y - p.y) < 58); attempt++) {{
        angle += (targetIndex % 2 ? -1 : 1) * 0.42;
        candidate = {{x: geometry.center.x + Math.cos(angle) * radius, y: geometry.center.y + Math.sin(angle) * radius}};
      }}
      network.moveNode(id, candidate.x, candidate.y);
      placed.push(candidate);
    }});
  }});
}}

function applyTargetedEdgeRelaxation() {{
  // Alternate attraction and separation: this lets the affected hyperedge
  // approach its neighbors without violating the non-overlap envelopes.
  for (let iteration = 0; iteration < 16; iteration++) {{
    shiftTargetHyperedgeGroups();
    if (typeof relaxHyperedgeLayout === 'function') relaxHyperedgeLayout();
    moveOrdinaryTargetNodes();
    setStraightAxisPositions();
  }}
  orientTargetHyperedgeMembers();
  moveOrdinaryTargetNodes();
  setStraightAxisPositions();
  network.redraw();
}}

function restorePositionSnapshot(snapshot) {{
  Object.entries(snapshot).forEach(([id, position]) => network.moveNode(id, position.x, position.y));
}}

function applyStraightResearchLayout() {{
  setStraightAxisPositions();
  if (typeof relaxHyperedgeLayout === 'function') relaxHyperedgeLayout();
  // The adapted relaxation treats these as obstacles, but restore the exact
  // zero-y axis as a final invariant in case another listener moved a node.
  setStraightAxisPositions();
  network.redraw();
}}

function optimizeStraightEdgeLengths() {{
  if (straightEdgeRelaxationRunning || straightEdgeRelaxationDone) return;
  straightEdgeRelaxationRunning = true;
  applyStraightResearchLayout();
  const status = document.getElementById('edge-relax-status');
  const baselinePositions = network.getPositions();
  const baselineMean = meanRawEdgeLength();
  const baselineTargetMean = meanTargetEdgeLength();
  if (status) status.textContent = `전체 평균 ${{baselineMean.toFixed(1)}} / 지정 5개 ${{baselineTargetMean.toFixed(1)}} → relaxation 중…`;

  // Axis nodes stay fixed; all other nodes are free to minimize spring length.
  nodesDS.update(STRAIGHT_LAYOUT_IDS.map(id => ({{id, fixed: {{x: true, y: true}}}})));
  let finalized = false;
  const finalize = () => {{
    if (finalized) return;
    finalized = true;
    network.stopSimulation();
    network.setOptions({{physics: {{enabled: false}}}});
    applyStraightResearchLayout();
    let candidateMean = meanRawEdgeLength();
    if (candidateMean > baselineMean) {{
      restorePositionSnapshot(baselinePositions);
      setStraightAxisPositions();
      network.redraw();
      candidateMean = meanRawEdgeLength();
    }}

    const targetedBaselinePositions = network.getPositions();
    const targetedBaselineMean = candidateMean;
    const targetedBaselineTargetMean = meanTargetEdgeLength();
    applyTargetedEdgeRelaxation();
    let finalMean = meanRawEdgeLength();
    let finalTargetMean = meanTargetEdgeLength();
    // The local pass must improve the requested edges and may cost at most
    // half a percent globally; otherwise preserve the accepted global layout.
    if (finalTargetMean > targetedBaselineTargetMean || finalMean > targetedBaselineMean * 1.005) {{
      restorePositionSnapshot(targetedBaselinePositions);
      setStraightAxisPositions();
      network.redraw();
      finalMean = targetedBaselineMean;
      finalTargetMean = targetedBaselineTargetMean;
    }}
    straightOptimizedPositions = network.getPositions();
    if (status) status.textContent = `전체 평균 ${{baselineMean.toFixed(1)}} → ${{finalMean.toFixed(1)}} / 지정 5개 ${{baselineTargetMean.toFixed(1)}} → ${{finalTargetMean.toFixed(1)}}`;
    straightEdgeRelaxationRunning = false;
    straightEdgeRelaxationDone = true;
  }};

  network.once('stabilizationIterationsDone', finalize);
  network.setOptions({{
    physics: {{
      enabled: true,
      solver: 'barnesHut',
      barnesHut: {{
        gravitationalConstant: -5200,
        centralGravity: 0.05,
        springLength: 105,
        springConstant: 0.075,
        damping: 0.28,
        avoidOverlap: 0.85,
      }},
      stabilization: {{enabled: true, iterations: 700, updateInterval: 100, fit: false}},
      minVelocity: 0.18,
      timestep: 0.35,
    }},
  }});
  network.stabilize(700);
  setTimeout(finalize, 6000);
}}

setTimeout(() => optimizeStraightEdgeLengths(), 260);
['journey-toggle', 'transfer-gate-toggle'].forEach(buttonId => {{
  const button = document.getElementById(buttonId);
  if (button) button.addEventListener('click', () => setTimeout(() => {{
    if (straightOptimizedPositions) {{
      restorePositionSnapshot(straightOptimizedPositions);
      setStraightAxisPositions();
      network.redraw();
    }} else {{
      applyStraightResearchLayout();
    }}
  }}, 0));
}});
// STRAIGHT_RESEARCH_LAYOUT_SCRIPT_END
"""


def strip_existing_straight_layout(html: str) -> str:
    patterns = [
        r"\n?/\* STRAIGHT_RESEARCH_LAYOUT_STYLE_START \*/.*?/\* STRAIGHT_RESEARCH_LAYOUT_STYLE_END \*/\n?",
        r"\n?  <!-- STRAIGHT_RESEARCH_LAYOUT_PANEL_START -->.*?<!-- STRAIGHT_RESEARCH_LAYOUT_PANEL_END -->\n?",
        r"\n?// STRAIGHT_RESEARCH_LAYOUT_SCRIPT_START.*?// STRAIGHT_RESEARCH_LAYOUT_SCRIPT_END\n?",
    ]
    for pattern in patterns:
        html = re.sub(pattern, "\n", html, flags=re.DOTALL)
    return html


def adapt_hyperedge_relaxation(html: str) -> str:
    # graph.html may itself be the promoted straight-layout version.  In that
    # case strip_existing_straight_layout() removes the overlay script/panel,
    # while the hyperedge obstacle adaptation is intentionally retained.
    if "Straight-axis nodes are immovable obstacles" in html:
        return html

    old_anchor = """    const journeyAnchors = (typeof JOURNEY_ID_SET !== 'undefined')
      ? nodes.filter(id => JOURNEY_ID_SET.has(id)) : [];
    const anchor = journeyAnchors.length ? journeyAnchors[0] : null;"""
    new_anchor = """    const journeyAnchors = (typeof STRAIGHT_LAYOUT_ID_SET !== 'undefined')
      ? nodes.filter(id => STRAIGHT_LAYOUT_ID_SET.has(id))
      : ((typeof JOURNEY_ID_SET !== 'undefined') ? nodes.filter(id => JOURNEY_ID_SET.has(id)) : []);
    const anchor = journeyAnchors.length ? journeyAnchors[0] : null;"""
    if old_anchor not in html:
        raise RuntimeError("Hyperedge anchor-selection block not found")
    html = html.replace(old_anchor, new_anchor, 1)

    old_memberships = """  const memberships = new Map();"""
    combined_relaxation = r"""  // Straight-axis nodes are immovable obstacles. Alternate obstacle pushes
  // with group-group separation so moving a free hyperedge away from the axis
  // cannot make it overlap another hyperedge.
  if (typeof STRAIGHT_LAYOUT_ID_SET !== 'undefined') {
    const straightPositions = network.getPositions(STRAIGHT_LAYOUT_IDS);
    for (let iteration = 0; iteration < 70; iteration++) {
      let moved = false;
      valid.forEach(h => {
        if (h.fixedCenter) return;
        Object.entries(straightPositions).forEach(([id, position]) => {
          if (h.nodes.includes(id)) return;
          let dx = h.center.x - position.x, dy = h.center.y - position.y;
          let distance = Math.hypot(dx, dy);
          const minimum = h.radius + HYPEREDGE_HULL_PADDING + 78;
          if (distance >= minimum) return;
          if (distance < 1e-6) {
            const angle = (h.index * 1.917 + id.length * 0.271) % (Math.PI * 2);
            dx = Math.cos(angle); dy = Math.sin(angle); distance = 1;
          }
          const push = minimum - distance + 5;
          h.center.x += dx / distance * push;
          h.center.y += dy / distance * push;
          moved = true;
        });
      });
      for (let i = 0; i < valid.length; i++) {
        for (let j = i + 1; j < valid.length; j++) {
          const a = valid[i], b = valid[j];
          let dx = b.center.x - a.center.x, dy = b.center.y - a.center.y;
          let distance = Math.hypot(dx, dy);
          if (distance < 1e-6) {
            const angle = (i * 2.399963 + j * 0.713) % (Math.PI * 2);
            dx = Math.cos(angle); dy = Math.sin(angle); distance = 1;
          }
          const minimum = a.radius + b.radius + HYPEREDGE_CLUSTER_GAP;
          if (distance >= minimum) continue;
          const push = (minimum - distance) * 0.53;
          const ux = dx / distance, uy = dy / distance;
          if (a.fixedCenter && b.fixedCenter) continue;
          if (a.fixedCenter) { b.center.x += ux * push * 2; b.center.y += uy * push * 2; }
          else if (b.fixedCenter) { a.center.x -= ux * push * 2; a.center.y -= uy * push * 2; }
          else {
            a.center.x -= ux * push; a.center.y -= uy * push;
            b.center.x += ux * push; b.center.y += uy * push;
          }
          moved = true;
        }
      }
      if (!moved) break;
    }
  }

  const memberships = new Map();"""
    if old_memberships not in html:
        raise RuntimeError("Hyperedge memberships block not found")
    html = html.replace(old_memberships, combined_relaxation, 1)

    old_unique = """    const unique = h.nodes.filter(id => memberships.get(id).length === 1 && id !== h.anchor);"""
    new_unique = """    const unique = h.nodes.filter(id => memberships.get(id).length === 1 && id !== h.anchor
      && !(typeof STRAIGHT_LAYOUT_ID_SET !== 'undefined' && STRAIGHT_LAYOUT_ID_SET.has(id)));"""
    if old_unique not in html:
        raise RuntimeError("Hyperedge unique-member block not found")
    html = html.replace(old_unique, new_unique, 1)

    old_shared = """  memberships.forEach((groups, id) => {
    if (groups.length < 2) return;"""
    new_shared = """  memberships.forEach((groups, id) => {
    if (groups.length < 2) return;
    if (typeof STRAIGHT_LAYOUT_ID_SET !== 'undefined' && STRAIGHT_LAYOUT_ID_SET.has(id)) return;"""
    if old_shared not in html:
        raise RuntimeError("Hyperedge shared-member block not found")
    html = html.replace(old_shared, new_shared, 1)

    old_ordinary = """  Object.entries(current).forEach(([id, position]) => {
    if (hyperedgeNodeIds.has(id)) return;"""
    new_ordinary = """  Object.entries(current).forEach(([id, position]) => {
    if (hyperedgeNodeIds.has(id)) return;
    if (typeof STRAIGHT_LAYOUT_ID_SET !== 'undefined' && STRAIGHT_LAYOUT_ID_SET.has(id)) return;"""
    if old_ordinary not in html:
        raise RuntimeError("Hyperedge ordinary-node block not found")
    return html.replace(old_ordinary, new_ordinary, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    target = args.target.resolve()
    if source == target:
        raise RuntimeError("Source and target must differ; graph.html is read-only for this operation")
    html = strip_existing_straight_layout(source.read_text(encoding="utf-8-sig"))

    raw_match = re.search(r"const RAW_NODES = (\[.*?\]);\s*const RAW_EDGES", html, flags=re.DOTALL)
    if not raw_match:
        raise RuntimeError("RAW_NODES block not found")
    available = {node["id"] for node in json.loads(raw_match.group(1))}
    missing = [node_id for node_id in STRAIGHT_ORDER + TARGET_RELAXATION_IDS if node_id not in available]
    if missing:
        raise RuntimeError(f"Straight-layout node IDs missing from graph: {missing}")

    if "— 직선형 비교</title>" not in html:
        html = re.sub(r"<title>(.*?)</title>", r"<title>\1 — 직선형 비교</title>", html, count=1)
    html = html.replace("</style>", CSS + "\n</style>", 1)
    panel_anchor = "  <!-- RESEARCH_TRANSFER_GATE_PANEL_END -->"
    if panel_anchor not in html:
        raise RuntimeError("Transfer-gate panel anchor not found")
    html = html.replace(panel_anchor, panel_anchor + "\n" + PANEL, 1)

    script_anchor = "\n</script>\n<script>\n// Render hyperedges as shaded regions"
    if script_anchor not in html:
        raise RuntimeError("Graphify script insertion anchor not found")
    html = html.replace(script_anchor, straight_script() + script_anchor, 1)
    html = adapt_hyperedge_relaxation(html)
    target.write_text(html, encoding="utf-8")
    print(f"Created straight research graph with {len(STRAIGHT_ORDER)} axis nodes: {target}")


if __name__ == "__main__":
    main()
