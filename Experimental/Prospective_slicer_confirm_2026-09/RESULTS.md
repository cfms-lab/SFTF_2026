# Prospective slicer confirmation — results

analyzed 2026-09-16T12:48:18.800537+00:00; meshes 70; raw ok rows 7697 / failed 3

## Primary (B=10, complete-case, SFTF minus uniform NRR; negative favors SFTF)

- cura_5_13: n=70 mean=+0.0033 [-0.0346, +0.0426] sd=0.1651 p=0.8669 w/t/l=41/0/29; Holm p=1.0000; excluded=0 -> **not confirmed**
- prusa_2_9_6: n=70 mean=+0.0155 [-0.0311, +0.0628] sd=0.2012 p=0.5218 w/t/l=37/0/33; Holm p=1.0000; excluded=0 -> **not confirmed**

**Regime verdict (pre-registered rule): not confirmed**

## Secondary

- cura_5_13_B5_complete: n=68 mean=+0.0434 [+0.0029, +0.0851] sd=0.1726 p=0.0413 w/t/l=34/0/34
- cura_5_13_B10_complete: n=70 mean=+0.0033 [-0.0344, +0.0424] sd=0.1651 p=0.8654 w/t/l=41/0/29
- cura_5_13_B20_complete: n=69 mean=+0.0345 [+0.0032, +0.0680] sd=0.1373 p=0.0394 w/t/l=33/0/36
- cura_5_13_B10_faces_50k_150k: n=53 mean=+0.0162 [-0.0318, +0.0649] sd=0.1804 p=0.5160 w/t/l=29/0/24
- cura_5_13_B10_faces_150k_250k: n=17 mean=-0.0367 [-0.0812, +0.0074] sd=0.0972 p=0.1374 w/t/l=12/0/5
- cura_5_13_B10_confirm80: n=33 mean=-0.0433 [-0.1025, +0.0193] sd=0.1840 p=0.1851 w/t/l=23/0/10
- cura_5_13_B10_new: n=37 mean=+0.0449 [+0.0034, +0.0900] sd=0.1355 p=0.0489 w/t/l=18/0/19
- prusa_2_9_6_B5_complete: n=70 mean=+0.0724 [+0.0190, +0.1295] sd=0.2382 p=0.0124 w/t/l=29/0/41
- prusa_2_9_6_B10_complete: n=70 mean=+0.0155 [-0.0320, +0.0630] sd=0.2012 p=0.5230 w/t/l=37/0/33
- prusa_2_9_6_B20_complete: n=70 mean=+0.0386 [+0.0023, +0.0751] sd=0.1559 p=0.0415 w/t/l=35/0/35
- prusa_2_9_6_B10_faces_50k_150k: n=53 mean=+0.0316 [-0.0250, +0.0887] sd=0.2082 p=0.2749 w/t/l=25/0/28
- prusa_2_9_6_B10_faces_150k_250k: n=17 mean=-0.0345 [-0.1136, +0.0469] sd=0.1741 p=0.4236 w/t/l=12/0/5
- prusa_2_9_6_B10_confirm80: n=33 mean=-0.0324 [-0.1107, +0.0505] sd=0.2329 p=0.4326 w/t/l=22/0/11
- prusa_2_9_6_B10_new: n=37 mean=+0.0584 [+0.0096, +0.1103] sd=0.1594 p=0.0282 w/t/l=15/0/22
- tomo_B5: n=70 mean=+0.0309 [+0.0104, +0.0544] sd=0.0959 p=0.0061 w/t/l=24/3/43
- tomo_B10: n=70 mean=+0.0243 [+0.0038, +0.0475] sd=0.0937 p=0.0310 w/t/l=21/3/46
- tomo_B20: n=70 mean=+0.0214 [+0.0057, +0.0402] sd=0.0746 p=0.0110 w/t/l=25/4/41
- engine_sign_agreement_B10: {'n': 70, 'agree': 62}
- tomo_vs_cura_sign_agreement_B10: 42
- tomo_vs_prusa_sign_agreement_B10: 42
- gate_accepted: 69

## Workflow cost

- sftf_k8192_mean_s: 10.047679272857204
- sftf_k8192_max_s: 93.266776199991
- cura_5_13_mean_slice_s: 16.89794114058007
- cura_5_13_overhead_B10_mean: 0.0631017168022077
- cura_5_13_overhead_B10_max: 0.25415679639441585
- cura_5_13_overhead_B10_pooled: 0.059460967399915375
- prusa_2_9_6_mean_slice_s: 4.038074107610426
- prusa_2_9_6_overhead_B10_mean: 0.24908067363960812
- prusa_2_9_6_overhead_B10_max: 0.8311405086796362
- prusa_2_9_6_overhead_B10_pooled: 0.2488235481840383
