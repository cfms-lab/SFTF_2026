"""Post hoc sensitivity checks for the hybrid analysis on the 70 prospective meshes (2026-09-17 review).

1. Complete-case: two Cura crashes (P012, P034) hit a uniform-5 cell, so the hybrid value on those
   meshes is the minimum over 9 of 10 attempted directions (best-available). Recompute the Cura
   hybrid-minus-uniform-10 contrast excluding them (seed 30, the seed of the exploratory analysis).
2. Adverse tail: how many meshes the hybrid is worse than uniform-10 on, and the largest per-mesh
   loss, for SFTF alone and for the hybrid, on the 70 meshes and on the 30 holdout meshes.
Appends the results to hybrid_policy_70_exploratory.json under 'post_hoc_sensitivity_2026_09_17'.
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
H = json.loads((HERE / "hybrid_policy_70_exploratory.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "prospective_results.json").read_text(encoding="utf-8"))
P2 = json.loads((HERE / "part2_mixed_policy_holdout30.json").read_text(encoding="utf-8"))
raw = [json.loads(l) for l in (HERE / "slicer_raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
C = json.loads((HERE / "policy_cells.json").read_text(encoding="utf-8"))


def stats(d, seed, n_boot=10000, n_perm=100000):
    d = np.asarray(d, float); r = np.random.default_rng(seed)
    idx = r.integers(0, len(d), size=(n_boot, len(d))); b = d[idx].mean(1)
    signs = r.choice([-1.0, 1.0], size=(n_perm, len(d))); perm = (signs * d[None, :]).mean(1); obs = d.mean()
    return {"n": int(len(d)), "mean": float(obs), "median": float(np.median(d)), "sd": float(d.std(ddof=1)),
            "ci": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
            "p": float((1 + np.sum(np.abs(perm) >= abs(obs) - 1e-15)) / (n_perm + 1)),
            "wtl": [int((d < -1e-9).sum()), int((np.abs(d) <= 1e-9).sum()), int((d > 1e-9).sum())]}


# which meshes have a failed cell inside the hybrid (uniform-5 or SFTF top-5) set, per engine
failed = {}
for r in raw:
    if not r.get("ok"):
        failed.setdefault((r["study_id"], r["engine"]), set()).add(int(r["grid_flat"]))
affected = {eng: sorted(sid for (sid, e), cells in failed.items() if e == eng and (set(C[sid]["uniform"]["5"]) | set(C[sid]["sftf"]["5"])) & cells)
            for eng in ("cura_5_13", "prusa_2_9_6")}
rows = H["rows"]
out = {"note": "Post hoc sensitivity checks requested by the 2026-09-17 internal review; not part of the pre-specified analyses.",
       "meshes_with_failed_hybrid_cell": affected, "complete_case": {}, "adverse_tail": {}}
for eng, seed in (("cura_5_13", 30), ("prusa_2_9_6", 31)):
    keep = [e for e in rows if e["study_id"] not in affected[eng]]
    out["complete_case"][eng] = stats([e[f"{eng}_mix10"] - e[f"{eng}_u10"] for e in keep], seed)
    d_s = np.array([e[f"{eng}_s10"] - e[f"{eng}_u10"] for e in rows]); d_m = np.array([e[f"{eng}_mix10"] - e[f"{eng}_u10"] for e in rows])
    out["adverse_tail"][f"{eng}_70"] = {"sftf_worse_than_uniform": int((d_s > 1e-9).sum()), "hybrid_worse_than_uniform": int((d_m > 1e-9).sum()),
                                        "max_loss_sftf": float(d_s.max()), "max_loss_hybrid": float(d_m.max()),
                                        "max_gain_sftf": float(d_s.min()), "max_gain_hybrid": float(d_m.min())}
    p = P2["rows"]
    d_s2 = np.array([e[f"{eng}_s10"] - e[f"{eng}_u10"] for e in p]); d_m2 = np.array([e[f"{eng}_mix10"] - e[f"{eng}_u10"] for e in p])
    out["adverse_tail"][f"{eng}_30"] = {"sftf_worse_than_uniform": int((d_s2 > 1e-9).sum()), "hybrid_worse_than_uniform": int((d_m2 > 1e-9).sum()),
                                        "max_loss_sftf": float(d_s2.max()), "max_loss_hybrid": float(d_m2.max())}
H["post_hoc_sensitivity_2026_09_17"] = out
(HERE / "hybrid_policy_70_exploratory.json").write_text(json.dumps(H, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
