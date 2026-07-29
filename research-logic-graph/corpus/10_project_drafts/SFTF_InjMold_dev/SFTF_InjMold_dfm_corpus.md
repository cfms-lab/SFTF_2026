# DFM-textbook moldability corpus (BUILDSPEC R7)

10 reproducible parts, draft 1.0deg. Ground truth = the exhaustive verifier (oracle) draw verdict, materialised as `.stl` + `manifest.json` so the same `load_folder -> oracle -> bench/calibrate.lomo` path ingests real Thingi10K/DFM STLs dropped beside them.

| part | tier | oracle GT | faces | DFM lesson |
|---|---|---|---|---|
| drafted_box | T0 | 0 side action(s) | 12 | clean draft: moldable along +z, no side actions |
| drafted_cone | T0 | 0 side action(s) | 192 | convex body: no undercut from any axis |
| cosmetic_panel | T0 | 0 side action(s) | 12 | no draft on a cosmetic wall -> high draft_penalty (a finish/ejection defect) though still 0 side actions |
| drafted_panel | T0 | 0 side action(s) | 12 | the corrected panel: 3deg draft clears the penalty |
| rect_tube | T1 | 0 side action(s) | 32 | side through-hole: clean along the bore axis (0); one slide if drawn across it |
| rect_tube_rotated | T2 | 0 side action(s) | 32 | off-axis bore -> bbox-6 misses the moldable axis the search recovers |
| twin_parallel_undercuts | T2 | 0 side action(s) | 64 | two coaxial bores: one draw frees both; drawn across, a single shared slide (set-cover merge) |
| two_perp_undercuts | T2 | 1 side action(s) | 64 | bores on perpendicular axes: aligning the draw to one needs a single slide; drawn across both, two |
| tilted_tube | T2 | 0 side action(s) | 32 | tilted bore: clean along the bore axis; drawn upright it needs an angled lifter, not a slide |
| sealed_shell | T3 | die-lock | 24 | fully enclosed cavity -> die-locked from every axis, needs a redesign |

Tiers: T0 trivially moldable · T1 one obvious side action · T2 competing axes / search needed · T3 die-lock.

> Thingi10K injection parts are **not** vendored here (no network); drop their `.stl` into this folder and `load_folder` + `write_corpus` pick them up with oracle GT identically.