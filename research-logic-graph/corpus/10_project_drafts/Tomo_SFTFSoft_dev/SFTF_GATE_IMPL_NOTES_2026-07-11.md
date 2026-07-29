# SFTF gate 구현·테스트 노트 — ste_smooth(B) + patch aggregation(A)

작성일: 2026-07-11 · 대상: `Tomo_SFTFSoft_dev`

## 구현 내용 (실제 소스 반영)

### `python/src/SFTF_Derivative/diff_sftf.py`
- **`overhang_gate`에 2개 모드 추가**:
  - `"smootherstep"` — C2 compact quintic `6u⁵−15u⁴+10u³` (핸드오프 Phase A). 밴드 밖 정확히 0/1, 조인트에서 1·2차 미분 0.
  - `"ste_smooth"` — **hard forward + compact C2 smootherstep backward**(제안 B). forward는 hard와 동일(누출 0), gradient는 밴드 안에서만 살아있고 hard 하강방향과 정렬 우수.
- **coplanar-patch aggregation (제안 A, S_g 항 한정)**:
  - `coplanar_patch_ids(V, F, cfg)` — `@torch.no_grad()` union-find. 간선 공유 + 법선각(`patch_normal_tol_deg`) + 평면offset(`patch_plane_tol`) tolerance로 동일평면 triangle 병합, **sharp crease는 넘지 않음**. 고정 membership.
  - `patch_aggregated_gate(normals, areas, n, patch_ids, cfg)` — `m_P=normalize(ΣAᵢmᵢ)` 면적가중 patch 법선에 게이트를 **patch당 1회** 평가 후 면으로 broadcast. V·n에 미분가능(membership만 고정).
  - `SFTFConfig`에 `gate_aggregate`("face"/"patch"), `patch_normal_tol_deg`, `patch_plane_tol` 추가.
  - `sftf_support_loss(..., patch_ids=None)` 인자 추가. `gate_supvol` S-항 게이트에서 `gate_aggregate=="patch"`이면 patch 경로 사용(그 외 기존과 동일).
- **회귀 0**: 기존 4모드(sigmoid/smoothstep/ste/hard) 분기·기본값 불변. patch 미사용 시 경로 완전 동일.

### `__init__.py`
- `coplanar_patch_ids`, `patch_aggregated_gate` export 추가.

### `tests/test_gate_modes.py` (torch, 기기에서 `uv run pytest`)
신규 테스트: smootherstep C2(정확 0/1·중앙 0.5·C2≪C1 경계곡률), ste_smooth(forward=hard·backward compact·밴드밖 grad 0), patch 불변성(잡음 법선에서 patch 게이트 면간 동일·평균법선 게이트와 일치·per-face는 변동), patch 미분가능성, union-find crease 존중, full-loss 6모드 유한·미분·STE류 forward=hard, patch full-loss 유한·미분·identity partition==per-face.

## 검증 (컨테이너)
컨테이너에서 **torch/trimesh 설치 불가**(PyPI 403 차단). 그래서 torch 코드는 py_compile로 구문 확인하고, **동일 수식을 numpy로 미러한 `scripts/sftf_impl_selftest.py`를 실제 실행**해 로직을 검증:

```
18/18 checks passed — ALL PASS
```
- smootherstep: 밴드밖 정확 0/1, 중앙 0.5, 조인트 1차 미분 ~0, **2차 미분 C1(smoothstep)의 <5%**(C2 서명).
- ste_smooth: forward==hard, backward=smootherstep′(밴드밖 정확히 0, 밴드안 nonzero).
- patch: 잡음 법선 500면에서 게이트 면간 동일, 평균법선 게이트와 1e-9 일치, per-face 변동 존재. **임계각 벗어난 x0=t−0.03에서 per-face S 오차 100%(34.98 vs 참 17.47) vs patch 5%(18.33)** — 벤치 결론 재확인.
- union-find: 동일평면 사각형 병합, 수직벽 분리, 정확히 2 patch.

> 주의: 임계각 *정확히* x0=t에선 smootherstep 홀대칭으로 per-face Jensen 갭이 우연히 상쇄되어 patch 이득이 안 보임(특이점). 이득은 t를 벗어난 근처에서 발현(벤치·self-test 확인).

## 다음 (기기에서)
1. `uv run python -m pytest tests/test_gate_modes.py -q` — 실제 torch 테스트 통과 확인.
2. `uv run python scripts/sweep_gate_family.py` / `shapeopt_gate_prescriptions.py --no-cura` — 신규 모드 포함 확장.
3. patch 경로 full shape-opt·Cura 지표 재확인(핸드오프 Phase C/D). membership 재클러스터 주기 튜닝.
4. 기본 `gate_mode` 변경은 증거 확보 후 별도 결정(핸드오프 범위밖 준수).
