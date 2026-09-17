"""Exploratory hybrid-policy analysis on the 70 prospective meshes + Figure 8 (with panel c).

The hybrid hypothesis (B=10 as uniform-5 + SFTF top-5) was formed after the primary
analysis; see GATE part 2 for the prespecified reanalysis on the 30-mesh holdout panel
(part2_mixed_policy_holdout30.json). Run hybrid_sensitivity.py afterwards (its block is
preserved on re-runs).
"""
import json, shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

R = json.load(open('prospective_results.json', encoding='utf-8')); rows = R['rows']; S = R['summary']
C = json.load(open('policy_cells.json', encoding='utf-8'))
raw = [json.loads(l) for l in open('slicer_raw.jsonl', encoding='utf-8') if l.strip()]
sup = {}
for r in raw:
    if r.get('ok') and np.isfinite(float(r['support_volume_mm3'])):
        sup[(r['study_id'], r['engine'], int(r['grid_flat']))] = float(r['support_volume_mm3'])


def nrr(v, lo, hi):
    return 0.0 if abs(hi - lo) <= 1e-12 else (v - lo) / (hi - lo)


def stats(d, seed):
    d = np.asarray(d, float); r = np.random.default_rng(seed)
    idx = r.integers(0, len(d), size=(10000, len(d))); b = d[idx].mean(1)
    signs = r.choice([-1.0, 1.0], size=(100000, len(d))); perm = (signs * d[None, :]).mean(1); obs = d.mean()
    return {'n': int(len(d)), 'mean': float(obs), 'median': float(np.median(d)), 'sd': float(d.std(ddof=1)),
            'ci': [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
            'p': float((1 + np.sum(np.abs(perm) >= abs(obs) - 1e-15)) / (100000 + 1)),
            'wtl': [int((d < -1e-9).sum()), int((np.abs(d) <= 1e-9).sum()), int((d > 1e-9).sum())]}


per = []
for r in rows:
    sid = r['study_id']; c = C[sid]; e = {'study_id': sid, 'stratum': r['stratum'], 'source_set': r['source_set']}
    for eng in ('cura_5_13', 'prusa_2_9_6'):
        s = {f: sup[(sid, eng, f)] for f in c['union'] if (sid, eng, f) in sup}; lo, hi = min(s.values()), max(s.values())
        b = lambda cells: [s[f] for f in cells if f in s]
        u5, s5, u10, s10, u20 = b(c['uniform']['5']), b(c['sftf']['5']), b(c['uniform']['10']), b(c['sftf']['10']), b(c['uniform']['20'])
        e[f'{eng}_u10'] = nrr(min(u10), lo, hi); e[f'{eng}_s10'] = nrr(min(s10), lo, hi); e[f'{eng}_mix10'] = nrr(min(u5 + s5), lo, hi)
        e[f'{eng}_u20'] = nrr(min(u20), lo, hi); e[f'{eng}_mix20'] = nrr(min(u10 + s10), lo, hi)
        e[f'{eng}_hit_s10'] = e[f'{eng}_s10'] < 1e-12; e[f'{eng}_hit_u10'] = e[f'{eng}_u10'] < 1e-12; e[f'{eng}_hit_mix10'] = e[f'{eng}_mix10'] < 1e-12
    gp = ('../R_term_recalib/confirm80_grids/%s.npz' % sid) if r['source_set'] == 'confirm80' else 'tomo_grids/%s.npz' % sid
    with np.load(gp, allow_pickle=False) as d:
        g = np.asarray(d['vss_grid']).reshape(-1)
    lo, hi = g.min(), g.max(); f = lambda cells: nrr(g[np.asarray(cells)].min(), lo, hi)
    e['tomo_u10'] = f(c['uniform']['10']); e['tomo_mix10'] = f(c['uniform']['5'] + c['sftf']['5'])
    e['tomo_u20'] = f(c['uniform']['20']); e['tomo_mix20'] = f(c['uniform']['10'] + c['sftf']['10'])
    per.append(e)

A = {}
for eng, seed in (('cura_5_13', 30), ('prusa_2_9_6', 31)):
    A[f'{eng}_mix10_minus_u10'] = stats([e[f'{eng}_mix10'] - e[f'{eng}_u10'] for e in per], seed)
    A[f'{eng}_mix10_minus_s10'] = stats([e[f'{eng}_mix10'] - e[f'{eng}_s10'] for e in per], seed + 10)
    A[f'{eng}_mix20_minus_u20'] = stats([e[f'{eng}_mix20'] - e[f'{eng}_u20'] for e in per], seed + 20)
    for st in ('faces_50k_150k', 'faces_150k_250k'):
        A[f'{eng}_mix10_minus_u10_{st}'] = stats([e[f'{eng}_mix10'] - e[f'{eng}_u10'] for e in per if e['stratum'] == st], seed + 40)
    for src in ('confirm80', 'new'):
        A[f'{eng}_mix10_minus_u10_{src}'] = stats([e[f'{eng}_mix10'] - e[f'{eng}_u10'] for e in per if e['source_set'] == src], seed + 50)
    A[f'{eng}_hits_B10'] = {'sftf': int(sum(e[f'{eng}_hit_s10'] for e in per)), 'uniform': int(sum(e[f'{eng}_hit_u10'] for e in per)), 'mixed': int(sum(e[f'{eng}_hit_mix10'] for e in per))}
A['tomo_mix10_minus_u10'] = stats([e['tomo_mix10'] - e['tomo_u10'] for e in per], 32)
A['tomo_mix20_minus_u20'] = stats([e['tomo_mix20'] - e['tomo_u20'] for e in per], 33)
out = {'note': 'Exploratory (post hoc) hybrid-policy analysis on the 70 prospective meshes; hypothesis formed after the primary analysis (2026-09-17). Re-evaluated under a prespecified plan on the previously analyzed 30-mesh holdout panel (part2_mixed_policy_holdout30.json, GATE part 2).', 'analyses': A, 'rows': per}
_prev = Path('hybrid_policy_70_exploratory.json')
if _prev.is_file():
    _old = json.loads(_prev.read_text(encoding='utf-8'))
    for k in ('post_hoc_sensitivity_2026_09_17',):
        if k in _old:
            out[k] = _old[k]
json.dump(out, open('hybrid_policy_70_exploratory.json', 'w'), indent=1)
for k, v in A.items():
    print(k, (f"n={v['n']} mean={v['mean']:+.4f} [{v['ci'][0]:+.4f},{v['ci'][1]:+.4f}] p={v['p']:.4f} w/t/l={v['wtl']}" if 'mean' in v else v))

# ---------------- Figure 8 with panel (c) ----------------
P2 = json.load(open('part2_mixed_policy_holdout30.json'))


def st2(d, seed):
    d = np.asarray(d); r = np.random.default_rng(seed); idx = r.integers(0, len(d), size=(10000, len(d))); b = d[idx].mean(1)
    return d.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5)


hv = {}
for eng, seed in (('cura_5_13', 20260919), ('prusa_2_9_6', 20260920)):
    hv[eng] = st2([e[f'{eng}_mix10'] - e[f'{eng}_u10'] for e in P2['rows']], seed)
t = P2['secondary']['tomo60 mix10-u10']; hv['tomo'] = (t['mean'], t['ci'][0], t['ci'][1])
print('holdout hybrid CIs:', {k: tuple(round(float(x), 4) for x in v) for k, v in hv.items()})

MINUS = '\u2212'
fig, axes = plt.subplots(1, 3, figsize=(7.26, 2.55), dpi=300, gridspec_kw={'width_ratios': [1.2, 1, 1]})
col = {'cura_5_13': '#1f77b4', 'prusa_2_9_6': '#d62728', 'tomo': '#2ca02c'}
lab = {'cura_5_13': 'CuraEngine', 'prusa_2_9_6': 'PrusaSlicer', 'tomo': 'TOMO'}
ax = axes[0]
for eng in ('cura_5_13', 'prusa_2_9_6'):
    x = np.sort([r[eng + '_diff_10'] for r in rows])
    ax.plot(np.arange(1, 71), x, marker='o', ms=1.8, lw=0.7, color=col[eng], label=lab[eng])
ax.axhline(0, color='k', lw=0.5, ls='--'); ax.set_xlabel('Meshes ordered by contrast (n = 70)', fontsize=7)
ax.set_ylabel('SFTF ' + MINUS + ' uniform NRR, B = 10', fontsize=7); ax.tick_params(labelsize=6)
ax.legend(fontsize=6, frameon=False, loc='upper left'); ax.text(-0.25, 1.03, 'a', transform=ax.transAxes, fontsize=9, fontweight='bold')
ax = axes[1]; budgets = [5, 10, 20]; xp = np.arange(3); w = 0.22
for i, key in enumerate(('cura_5_13', 'prusa_2_9_6', 'tomo')):
    m = []; lo = []; hi = []
    for b in budgets:
        v = S['secondary'][f'{key}_B{b}_complete' if key != 'tomo' else f'tomo_B{b}']
        m.append(v['mean']); lo.append(v['mean'] - v['bootstrap_ci95'][0]); hi.append(v['bootstrap_ci95'][1] - v['mean'])
    ax.errorbar(xp + (i - 1) * w, m, yerr=[lo, hi], fmt='o', ms=3, capsize=1.5, lw=0.8, color=col[key], label=lab[key])
orig = {'cura_5_13': (-0.0362, -0.0955, 0.0225), 'prusa_2_9_6': (-0.0465, -0.1193, 0.0281), 'tomo': (-0.0329, -0.0610, -0.0089)}
for i, key in enumerate(('cura_5_13', 'prusa_2_9_6', 'tomo')):
    m_, l, h = orig[key]
    ax.errorbar([1 + (i - 1) * w + 0.07], [m_], yerr=[[m_ - l], [h - m_]], fmt='s', mfc='white', ms=3, capsize=1.5, lw=0.7, color=col[key])
ax.errorbar([], [], fmt='s', mfc='white', color='gray', ms=3, label='original 12-mesh subgroup')
ax.axhline(0, color='k', lw=0.5, ls='--'); ax.set_xticks(xp); ax.set_xticklabels([f'B = {b}' for b in budgets], fontsize=7)
ax.set_ylabel('SFTF ' + MINUS + ' uniform NRR (mean, 95% CI)', fontsize=7); ax.tick_params(labelsize=6)
ax.legend(fontsize=5, frameon=False, loc='lower right'); ax.text(-0.3, 1.03, 'b', transform=ax.transAxes, fontsize=9, fontweight='bold')
ax = axes[2]; xp = np.arange(2)
for i, key in enumerate(('cura_5_13', 'prusa_2_9_6', 'tomo')):
    a = A[f'{key}_mix10_minus_u10']
    m = [a['mean'], hv[key][0]]; lo = [a['mean'] - a['ci'][0], hv[key][0] - hv[key][1]]; hi = [a['ci'][1] - a['mean'], hv[key][2] - hv[key][0]]
    ax.errorbar(xp + (i - 1) * w, m, yerr=[lo, hi], fmt='D', ms=3, capsize=1.5, lw=0.8, color=col[key], label=lab[key])
ax.axhline(0, color='k', lw=0.5, ls='--'); ax.set_xticks(xp)
ax.set_xticklabels(['70 prospective meshes\n(exploratory; n = 70)', 'original holdout panel, reanalysis\n(prespecified; slicers n = 30, TOMO n = 60)'], fontsize=5.6)
ax.set_ylabel('Hybrid(5+5) ' + MINUS + ' uniform NRR, B = 10', fontsize=7); ax.tick_params(labelsize=6)
ax.legend(fontsize=5.5, frameon=False, loc='lower left'); ax.text(-0.3, 1.03, 'c', transform=ax.transAxes, fontsize=9, fontweight='bold')
fig.tight_layout(w_pad=1.0)
fig.savefig('figure8_prospective.png', dpi=300)
shutil.copy('figure8_prospective.png', r'D:\__SFTF_Projects(2026)\Tomo_SFTF_dev\draft\TDP_v2.2\2026-09-16_TDP_rev1\Figure8_prospective_confirmation.png')
print('fig8 px', Image.open('figure8_prospective.png').size)
