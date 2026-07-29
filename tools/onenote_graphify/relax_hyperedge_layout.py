"""Inject deterministic hyperedge-aware node relaxation into Graphify HTML.

The stock Graphify renderer connects hyperedge members in extraction order,
which can create concave or self-crossing regions.  This postprocessor:

1. lays each hyperedge's members out as a compact cluster,
2. separates cluster centers with iterative relaxation,
3. pushes unrelated nodes outside the cluster envelopes, and
4. renders each region from the true convex hull of its member positions.

The semantic graph and graph.json are not changed.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MARKER = "// Render hyperedges as shaded regions"


def relaxation_script(hyperedges: list[dict]) -> str:
    payload = json.dumps(hyperedges, ensure_ascii=False)
    return f"""{MARKER}
const hyperedges = {payload};
// HYPEREDGE_RELAXATION_START
const HYPEREDGE_HULL_PADDING = 52;
const HYPEREDGE_CLUSTER_GAP = 84;

function convexHull(points) {{
  if (points.length <= 2) return points.slice();
  const sorted = points.slice().sort((a, b) => a.x === b.x ? a.y - b.y : a.x - b.x);
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower = [];
  for (const p of sorted) {{
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }}
  const upper = [];
  for (let i = sorted.length - 1; i >= 0; i--) {{
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }}
  lower.pop(); upper.pop();
  return lower.concat(upper);
}}

function expandedHull(points, padding = HYPEREDGE_HULL_PADDING) {{
  const hull = convexHull(points);
  if (!hull.length) return [];
  const cx = hull.reduce((s, p) => s + p.x, 0) / hull.length;
  const cy = hull.reduce((s, p) => s + p.y, 0) / hull.length;
  return hull.map(p => {{
    const dx = p.x - cx, dy = p.y - cy;
    const d = Math.hypot(dx, dy) || 1;
    return {{x: p.x + padding * dx / d, y: p.y + padding * dy / d}};
  }});
}}

function relaxHyperedgeLayout() {{
  const allPositions = network.getPositions();
  const valid = hyperedges.map((h, index) => {{
    const nodes = h.nodes.filter(id => allPositions[id]);
    const positions = nodes.map(id => allPositions[id]);
    const cx = positions.reduce((s, p) => s + p.x, 0) / Math.max(1, positions.length);
    const cy = positions.reduce((s, p) => s + p.y, 0) / Math.max(1, positions.length);
    const journeyAnchors = (typeof JOURNEY_ID_SET !== 'undefined')
      ? nodes.filter(id => JOURNEY_ID_SET.has(id)) : [];
    const anchor = journeyAnchors.length ? journeyAnchors[0] : null;
    const anchorPos = anchor ? allPositions[anchor] : null;
    return {{
      ...h, index, nodes,
      center: anchorPos ? {{x: anchorPos.x, y: anchorPos.y}} : {{x: cx, y: cy}},
      fixedCenter: Boolean(anchorPos),
      anchor,
      radius: 90 + Math.max(0, nodes.length - 4) * 12,
    }};
  }}).filter(h => h.nodes.length >= 2);

  // Relax hyperedge centers. Journey anchors stay fixed; free clusters move
  // around them. Shared-member clusters may touch at that member, but their
  // interiors are kept apart by the same center-distance constraint.
  for (let iteration = 0; iteration < 90; iteration++) {{
    let moved = false;
    for (let i = 0; i < valid.length; i++) {{
      for (let j = i + 1; j < valid.length; j++) {{
        const a = valid[i], b = valid[j];
        let dx = b.center.x - a.center.x, dy = b.center.y - a.center.y;
        let distance = Math.hypot(dx, dy);
        if (distance < 1e-6) {{
          const angle = (i * 2.399963 + j * 0.713) % (Math.PI * 2);
          dx = Math.cos(angle); dy = Math.sin(angle); distance = 1;
        }}
        const minimum = a.radius + b.radius + HYPEREDGE_CLUSTER_GAP;
        if (distance >= minimum) continue;
        const push = (minimum - distance) * 0.53;
        const ux = dx / distance, uy = dy / distance;
        if (a.fixedCenter && b.fixedCenter) continue;
        if (a.fixedCenter) {{ b.center.x += ux * push * 2; b.center.y += uy * push * 2; }}
        else if (b.fixedCenter) {{ a.center.x -= ux * push * 2; a.center.y -= uy * push * 2; }}
        else {{
          a.center.x -= ux * push; a.center.y -= uy * push;
          b.center.x += ux * push; b.center.y += uy * push;
        }}
        moved = true;
      }}
    }}
    if (!moved) break;
  }}

  const memberships = new Map();
  valid.forEach(h => h.nodes.forEach(id => {{
    if (!memberships.has(id)) memberships.set(id, []);
    memberships.get(id).push(h);
  }}));

  // Place unique members on deterministic rings. A highlighted journey node
  // remains the cluster anchor, preserving the chronological emphasis.
  valid.forEach(h => {{
    const unique = h.nodes.filter(id => memberships.get(id).length === 1 && id !== h.anchor);
    const start = -Math.PI / 2 + h.index * 0.47;
    unique.forEach((id, i) => {{
      const angle = start + (Math.PI * 2 * i / Math.max(1, unique.length));
      network.moveNode(id, h.center.x + Math.cos(angle) * h.radius, h.center.y + Math.sin(angle) * h.radius);
    }});
    if (h.anchor) network.moveNode(h.anchor, h.center.x, h.center.y);
  }});

  // A node belonging to several hyperedges is placed between their centers so
  // the regions meet at the shared semantic member instead of overlapping.
  memberships.forEach((groups, id) => {{
    if (groups.length < 2) return;
    const x = groups.reduce((s, h) => s + h.center.x, 0) / groups.length;
    const y = groups.reduce((s, h) => s + h.center.y, 0) / groups.length;
    network.moveNode(id, x, y);
  }});

  // Keep unrelated nodes outside every hyperedge envelope. Only ordinary
  // nodes are moved here; members of other hyperedges stay with their cluster.
  const hyperedgeNodeIds = new Set(memberships.keys());
  const current = network.getPositions();
  Object.entries(current).forEach(([id, position]) => {{
    if (hyperedgeNodeIds.has(id)) return;
    let x = position.x, y = position.y;
    for (let pass = 0; pass < 4; pass++) {{
      valid.forEach(h => {{
        let dx = x - h.center.x, dy = y - h.center.y;
        let distance = Math.hypot(dx, dy);
        const minimum = h.radius + HYPEREDGE_HULL_PADDING + 64;
        if (distance >= minimum) return;
        if (distance < 1e-6) {{
          const angle = (id.length * 0.731 + h.index) % (Math.PI * 2);
          dx = Math.cos(angle); dy = Math.sin(angle); distance = 1;
        }}
        const shift = minimum - distance + 8;
        x += dx / distance * shift;
        y += dy / distance * shift;
      }});
    }}
    if (x !== position.x || y !== position.y) network.moveNode(id, x, y);
  }});
  network.redraw();
}}

network.on('afterDrawing', function(ctx) {{
  hyperedges.forEach(h => {{
    const positions = h.nodes
      .map(nid => network.getPositions([nid])[nid])
      .filter(p => p !== undefined);
    if (positions.length < 3) return;
    const hull = expandedHull(positions);
    if (hull.length < 3) return;
    const cx = hull.reduce((s, p) => s + p.x, 0) / hull.length;
    const cy = hull.reduce((s, p) => s + p.y, 0) / hull.length;
    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = '#6366f1';
    ctx.strokeStyle = '#6366f1';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(hull[0].x, hull[0].y);
    hull.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 0.4;
    ctx.stroke();
    ctx.globalAlpha = 0.8;
    ctx.fillStyle = '#8b8cff';
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(h.label, cx, cy - 5);
    ctx.restore();
  }});
}});

setTimeout(() => relaxHyperedgeLayout(), 180);
// HYPEREDGE_RELAXATION_END"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    args = parser.parse_args()

    html_path = args.html.resolve()
    html = html_path.read_text(encoding="utf-8-sig")
    marker_index = html.find(MARKER)
    if marker_index < 0:
        raise RuntimeError("Graphify hyperedge renderer marker not found")
    script_end = html.find("\n</script>", marker_index)
    if script_end < 0:
        raise RuntimeError("Hyperedge script closing tag not found")
    block = html[marker_index:script_end]
    match = re.search(r"const hyperedges = (\[.*?\]);", block, flags=re.DOTALL)
    if not match:
        raise RuntimeError("Hyperedge data block not found")
    hyperedges = json.loads(match.group(1))
    html = html[:marker_index] + relaxation_script(hyperedges) + html[script_end:]
    html_path.write_text(html, encoding="utf-8")
    print(f"Relaxed renderer for {len(hyperedges)} hyperedges in {html_path}")


if __name__ == "__main__":
    main()
