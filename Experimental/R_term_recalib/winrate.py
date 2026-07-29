"""Per-mesh win rates of W_B vs V0 on the held-out D/E meshes."""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_and_calibrate import OUT, mesh_names, nms_basins  # noqa: E402

def score(d, a_hv, a_hm, a_bm, a_r):
    return a_hv*d["F_hv"] + d["F_bv"] + a_hm*d["F_hm"] + a_bm*d["F_bm"] + a_r*d["R"]

def m(d, s):
    order = np.lexsort((np.arange(len(s)), s))
    top1 = float(d["nrr"][order[0]])
    basin = float(np.min(d["nrr"][nms_basins(d["directions"], s)]))
    return top1, basin

wins_t, ties_t, wins_b, ties_b, rows = 0, 0, 0, 0, []
names = [n for g in ("D", "E") for n in mesh_names(g)]
for name in names:
    d = np.load(OUT / f"{name}_features.npz", allow_pickle=False)
    t0, b0 = m(d, score(d, 0.0, 0.0, 1.0, 1.0))   # V0
    t1, b1 = m(d, score(d, 0.25, 0.25, 0.5, 1.0)) # W_B
    rows.append((name, t0, t1, b0, b1))
    wins_t += t1 < t0 - 1e-9; ties_t += abs(t1 - t0) <= 1e-9
    wins_b += b1 < b0 - 1e-9; ties_b += abs(b1 - b0) <= 1e-9
    print(f"{name:24s} top1 {t0:.3f}->{t1:.3f}  basin24 {b0:.4f}->{b1:.4f}")
n = len(rows)
print()
print(f"top1  : W_B wins {wins_t}/{n}, ties {ties_t}, losses {n-wins_t-ties_t}")
print(f"basin : W_B wins {wins_b}/{n}, ties {ties_b}, losses {n-wins_b-ties_b}")
print(f"paired mean diff top1 {np.mean([r[2]-r[1] for r in rows]):+.4f}, "
      f"basin24 {np.mean([r[4]-r[3] for r in rows]):+.4f}")
