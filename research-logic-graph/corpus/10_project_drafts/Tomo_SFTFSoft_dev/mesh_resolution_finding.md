# 메쉬 해상도(데시메이트) 권고 — 새 논문용 노트

> 전달: SFTF↔슬라이서 검증 시 **메쉬를 데시메이트하지 말 것**(또는 ≥30k면 유지). 데시메이트는
> SFTF의 support-volume 항 정확도를 *인위적으로* 떨어뜨린다. 아래 데이터·기전·검증·권고와
> 바로 붙여 쓸 수 있는 국문/영문 문단을 담았다. (측정: 2026-06-30, Bunny 69k)

## 1. 핵심 주장
미분가능 SFTF의 support-volume 예측(`sftf_support_loss`, `w_supvol`)과 **슬라이서 실제 서포트
부피**의 순위상관(Spearman)은 **입력 메쉬 면수에 단조 증가**한다. 즉 데시메이트할수록 상관이
떨어지므로, SFTF의 슬라이서 일치도를 보고할 때는 원본(또는 고해상도) 메쉬를 써야 한다.

## 2. 데이터 (Bunny 69k, supvol 구성, vs Cura(legacy 15.04) 서포트 부피)

| 입력 면수 | Spearman | Pearson |
|---:|---:|---:|
| 6,000 (강한 데시메이트) | 0.263 | 0.563 |
| 15,000 | 0.460 | 0.649 |
| 30,000 | 0.590 | 0.719 |
| 40,000 | **0.631** | **0.745** |
| 69,662 (원본) | 미측정* | — |

\* 원본은 면쌍 all-pairs(≈69k²)를 float64+autograd로 잡으면 ~134 GB가 필요해 단일 PC(61 GB)에선
스왑이 발생. `torch.no_grad()`+float32로 40k까지는 안전(commit ≈15 GB). 추세상 원본은 ~0.65 부근.
실측이 필요하면 (a) true-kNN 메모리 상한 구현 또는 (b) ≥40k 데시메이트로 충분.

설정: `SFTFConfig(w_supvol=1.0, gate_supvol=True, supvol_to_bed=True)`, knn=48, 단위대각 정규화,
yaw/pitch 30°→60° 격자. 기준은 legacy CuraEngine 15.04(3DWOX와 동일 엔진)의 DP103 PLA
서포트(everywhere/lines/60°/20%, 밀도 1.21 g/cm³).

## 3. 검증 — 이 낮은 값은 *하니스 결함이 아니라 실제 신호*
동일 하니스(같은 Cura 서포트 격자·같은 yaw/pitch 규약)에 **검증된 서포트 예측기 TOMO(mss)**를
통과시키면 **Spearman 0.953 / Pearson 0.969** 가 나온다. 즉 비교 파이프라인·회전 규약은 정확하며,
데시메이트에서 관찰된 하락은 SFTF가 잃는 표면 정보 때문이지 측정 버그가 아니다.

## 4. 기전 (왜 데시메이트가 해치나)
supvol 항 `S(n)`은 **면별 overhang(처짐 정도)×낙하높이**를 적분해 서포트 부피를 추정한다.
Quadric decimation은 작은 면을 병합·평활하는데, 이때 사라지는 미세 overhang 면이 바로 `S(n)`이
합산하는 신호다. 따라서 데시메이트는 supvol 추정의 *변별력*을 직접 떨어뜨려 방향별 순위가
무뎌진다(거친 격자와 겹치면 0.2까지 하락).

## 5. 권고 (논문/실무)
1. **SFTF↔슬라이서 부피 검증 시 데시메이트 금지**(부득이하면 ≥30k면, 본문에 면수 명시).
2. TOMO 같은 **복셀 기반 기준은 데시메이트에 둔감**(256³ 복셀화)하므로 속도용 데시메이트 허용 —
   둘의 민감도가 다름을 구분해 서술.
3. 메모리: 원본 메쉬에서 supvol을 평가할 땐 **`no_grad`+float32 또는 true-kNN**으로 O(F²) 폭주를 피한다.

## 6. 바로 붙여 쓸 문단

### 국문
> SFTF의 support-volume 항과 슬라이서 실제 서포트 부피의 순위상관은 입력 메쉬 해상도에 단조
> 의존한다(Bunny: 6k면 ρ=0.26 → 30k면 0.59 → 40k면 0.63). 이는 supvol 항이 면별 overhang을
> 적분하기 때문으로, quadric decimation이 미세 overhang을 평활하면 변별력이 사라진다. 동일
> 비교 하니스에 복셀 기반 TOMO를 넣으면 ρ=0.95가 나와 파이프라인 자체는 정확함을 확인했다.
> 따라서 SFTF의 슬라이서 일치도 평가에는 데시메이트하지 않은(또는 ≥30k면) 메쉬를 사용한다.

### English
> The rank correlation between the SFTF support-volume term and a slicer's actual support volume
> increases monotonically with input-mesh resolution (Bunny: ρ=0.26 at 6k faces → 0.59 at 30k →
> 0.63 at 40k). Because the support-volume term integrates per-face overhang, quadric decimation
> smooths away the fine overhangs the term sums, eroding its discriminative power. Routing a
> voxel-based predictor (TOMO) through the *same* comparison harness yields ρ=0.95, confirming the
> pipeline and convention are correct and that the decimation drop is a genuine information loss,
> not a measurement artifact. We therefore evaluate SFTF–slicer agreement on undecimated meshes
> (or ≥30k faces) and report the mesh resolution.

## 7. 재현 포인터
- 데시메이트 sweep: `tmp/decim_sweep.py` (출력: 표 §2). 40k 단발: `tmp/soft_40k.py` → `tmp/soft_40k_step60.npz`.
- Cura 기준 격자: `_Cura_CLI`의 `reference.cura_reference_grid("(4)Bunny_69k.stl", step=30)` →
  `tmp/cura_ref_bunny_step30.npz`(support_grid).
- 하니스 앵커(TOMO↔Cura=0.953): `_Cura_CLI`의 `tomo_runner.compute_tomo_grid(..., metric="mss")`.
- 규약: `direction_from_yaw_pitch(yaw,pitch) = [-sinθp, cosθp·sinθy, cosθp·cosθy]`
  (= `_Cura_CLI`의 `mesh_rotation.rotation_matrix`ᵀ·ẑ, 검증됨).

## 8. 범위/한계 (정직)
- 단일 메쉬(Bunny), sweep은 거친 60° 격자(49점)·supvol_bed 구성 기준. **단조 추세는 강하나**,
  다른 메쉬(dragon/lucy/happy 등)와 30° 격자로 한 번 더 확인하면 일반화 주장에 안전.
- 원본 69k 절대 상한값은 미측정(메모리). 추세 외삽치(~0.65)이며 본문엔 "≥40k에서 0.63, 추세상
  포화"로 보수적으로 기술 권장.
