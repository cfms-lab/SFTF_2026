# SFTF 파이프라인에 Pareto 다목적 후처리 추가 — 코딩 에이전트 작업 지시서

> 이 문서는 코딩 에이전트(Claude Code, Codex 등)에 그대로 전달하는 작업 사양서입니다.
> 목표는 기존 SFTF(Support Flow Tensor Field) 후보 생성 파이프라인에 **Pareto 비지배 필터**를
> 후처리 단계로 추가하여, 단일 스칼라 가중합 `J = R + P + B` 의 단위·가중치 의존성을 우회하고
> "서로 절충되는 좋은 빌드 방향 후보들"을 사용자에게 제시할 수 있게 하는 것입니다.

---

## 0. 먼저 할 일 (에이전트에게)

1. 이 저장소에서 SFTF 후보 생성 코드를 찾아 다음을 파악하라.
   탐색 힌트: `angular_nms`, `theta_basin`, `R + B` / `Rtilde`, `candidate` / `coarse` / `cone`,
   `normals` / `centroid` / `bbox` 같은 심볼을 grep 하면 관련 함수와 자료구조를 빠르게 찾을 수 있다.
   - 후보 풀(coarse 512 + cone refine)을 만드는 함수와, 각 후보가 들고 있는 자료구조.
   - 각 후보에 이미 계산되어 있는 특징값: `J, R, P, B, H(hit), sigma1..3, S(nuclear)`,
     빌드 방향 단위벡터 `n`, 그리고 yaw/pitch 매핑.
   - 최종 후보 선택에 쓰이는 **angular NMS (top-k basin, `theta_basin=12deg`)** 함수.
   - 메시 기하 캐시 `D_mesh = {m_i(normals), A_i(area), c_i(centroid), V(vertices), D(bbox diag), alpha=1/D, ...}`.
2. 아래 사양대로 `sftf/pareto.py`(또는 프로젝트 관례에 맞는 위치)에 새 모듈을 추가하라.
3. 후보 풀 생성 직후 ~ angular NMS 직전 사이에 Pareto 단계를 끼워 넣어라(§4 통합 지점).
4. 기존 `J` 기반 경로는 **삭제하지 말고** 플래그(`use_pareto: bool = False`)로 선택 가능하게 하라.
   기본값은 False로 두어 기존 결과 재현성을 보존한다.

---

## 1. 배경 (변경 이유)

현재 목적함수는
```
J(n) = R(n) + P(n) + B(n)   (lambda_R = lambda_P = lambda_B = 1)
```
형태의 **가중합 스칼라화**다. 문제점:
- 항들의 단위가 다르다: `R, P ~ area^2`, `B ~ area`. 그냥 더하면 스케일 큰 항이 결과를 지배한다.
- 가중치를 1로 고정해 물리적 정당성이 약하다(정규화 시 상관 0.52→0.14로 붕괴하는 현상이 이미 관측됨).
- 가중합은 비볼록 Pareto front의 일부 해에 도달하지 못한다는 이론적 한계가 있다.

Pareto 방식은 **목적을 하나로 합치지 않고 지배 관계로 비교**하므로 위 문제를 우회한다.
후보 풀이 이미 이산적·소규모(약 1,292개)이므로 비지배 필터는 사실상 공짜로 얹을 수 있다.

---

## 2. 목적(objective) 정의

모든 목적은 **"작을수록 좋음(minimize)"** 으로 통일한다. 기본 3개 목적을 사용한다.
전부 빌드 방향 `n`(단위벡터)과 기존 메시 캐시만으로 계산 가능하다.

| 이름 | 정의 | 의미 | 비고 |
|---|---|---|---|
| `f_support` | `Rtilde(n) = R(n) + B(n)` | 통합 서포트 비용(서포트 부피 대리값) | 이미 계산됨. 논문에서 J보다 예측력 높은 항 |
| `f_height` | `(max_v (v·n) - min_v (v·n)) / D` | 빌드 방향 프린트 높이(레이어 수/시간 대리값) | 정점 V만 있으면 계산 |
| `f_overhang` | `sum_i max(0, -m_i·n) · A_i` | 총 오버행 면적(표면 품질/접촉흔적 대리값) | O_i·A_i 합, 이미 부분 계산됨 |

설계 메모:
- `f_support`는 가능하면 `Rtilde = R + B`를 쓴다(논문 §unified 결론). 단 TOMO Mss 실측값이 있으면 그걸 우선 사용해도 된다.
- 목적은 2~4개 사이로 유지하라. 너무 많으면 거의 모든 후보가 비지배가 되어 필터가 무력해진다(차원의 저주).
- 추가 목적 후보(선택): 베이스 접촉 안정성(밑면적), `P`(자기지지 면적, 단 부호 주의: 클수록 자기지지가 많아 "좋음"이므로 최소화하려면 `-P`로 넣어야 함).
  기본 3목적에는 포함하지 않는다. 도입 시 부호를 명시적으로 주석 처리하라.

---

## 3. 참조 구현 (numpy)

> 그대로 써도 되고, 저장소 스타일(타입 힌트/네이밍)에 맞춰 다듬어도 된다.
> 핵심 계약(입출력 형태와 "전부 minimize" 규약)은 바꾸지 말 것.

```python
import numpy as np


def compute_objectives(n, V, normals, areas, R, B, D):
    """주어진 빌드 방향 n에 대한 목적 벡터(전부 minimize)를 반환.

    Parameters
    ----------
    n : (3,)   unit build direction
    V : (Nv,3) vertices
    normals : (Nf,3) outward face normals (m_i)
    areas   : (Nf,)  face areas (A_i)
    R, B    : float  이미 계산된 Rayleigh / build-plate 항
    D       : float  bbox diagonal

    Returns
    -------
    (3,) array: [f_support, f_height, f_overhang]
    """
    n = n / (np.linalg.norm(n) + 1e-12)

    f_support = float(R + B)                       # Rtilde, minimize

    proj = V @ n
    f_height = float((proj.max() - proj.min()) / D)  # minimize

    overhang = np.maximum(0.0, -(normals @ n))     # O_i = max(0, -m_i·n)
    f_overhang = float(np.sum(overhang * areas))   # minimize

    return np.array([f_support, f_height, f_overhang], dtype=float)


def pareto_mask(costs):
    """Pareto 비지배 마스크. 모든 열을 minimize 한다고 가정.

    costs : (n_candidates, n_objectives)
    return: (n_candidates,) bool — True면 비지배(Pareto-optimal)

    c가 i를 지배 <=> all(c <= costs[i]) and any(c < costs[i]).
    복잡도 O(n^2 * m). 후보 ~수천 개 규모에서 충분히 빠름.
    """
    costs = np.asarray(costs, dtype=float)
    n = costs.shape[0]
    efficient = np.ones(n, dtype=bool)
    for i in range(n):
        if not efficient[i]:
            continue
        dominates_i = (np.all(costs <= costs[i], axis=1)
                       & np.any(costs < costs[i], axis=1))
        dominates_i[i] = False
        if np.any(dominates_i):
            efficient[i] = False
    return efficient


def knee_point(front_costs):
    """Pareto front 위에서 기본 추천 1개를 고른다.

    각 목적을 front 내 min-max로 [0,1] 정규화한 뒤,
    이상점(utopia=원점)에 가장 가까운 후보의 (front 내) 인덱스를 반환.
    front가 1개면 0을 반환.
    """
    fc = np.asarray(front_costs, dtype=float)
    if len(fc) == 1:
        return 0
    lo = fc.min(axis=0)
    span = np.ptp(fc, axis=0)
    span[span == 0] = 1.0
    norm = (fc - lo) / span
    dist = np.linalg.norm(norm, axis=1)   # 원점(이상점)까지 거리
    return int(np.argmin(dist))


def weighted_pick(front_costs, weights):
    """선호 가중치가 주어졌을 때 front 내 최선 후보 인덱스.
    weights는 양수, 합이 1일 필요는 없음. 정규화 후 가중합 최소.
    """
    fc = np.asarray(front_costs, dtype=float)
    lo = fc.min(axis=0)
    span = np.ptp(fc, axis=0)
    span[span == 0] = 1.0
    norm = (fc - lo) / span
    w = np.asarray(weights, dtype=float)
    return int(np.argmin(norm @ w))
```

---

## 4. 통합 지점 (파이프라인 배선)

기존 흐름:
```
generate_candidates() → 각 후보 features(J,R,P,B,...) → angular NMS(top-k basin) → TOMO 검증
```

변경 후 흐름(플래그 ON일 때):
```
generate_candidates()
  → 각 후보 features + objective 벡터 계산        (compute_objectives)
  → pareto_mask 로 비지배 후보만 선별              (pareto_mask)
  → 비지배 후보에 기존 angular NMS(theta_basin) 적용  ← 함수 재사용
  → (옵션) knee_point / weighted_pick 로 기본 추천 표시
  → 선별된 대표 후보들을 TOMO 검증으로 전달
```

구현 스케치(기존 후보 객체 리스트를 `cands`라 가정):
```python
def select_pareto_candidates(cands, D_mesh, theta_basin=12.0,
                             weights=None, top_k=3):
    V, normals, areas, D = (D_mesh["V"], D_mesh["normals"],
                            D_mesh["areas"], D_mesh["D"])

    costs = np.array([
        compute_objectives(c.n, V, normals, areas, c.R, c.B, D)
        for c in cands
    ])                                   # (n, 3)

    mask = pareto_mask(costs)
    front = [c for c, keep in zip(cands, mask) if keep]
    front_costs = costs[mask]

    # 같은 basin 중복 제거: 기존 angular NMS 재사용(점수 대신 f_support 오름차순 정렬 후 적용)
    order = np.argsort(front_costs[:, 0])           # f_support 기준
    front_sorted = [front[i] for i in order]
    reps = angular_nms(front_sorted, theta_basin)   # ← 기존 함수 호출

    # 기본 추천 1개(설명용). 사용자가 weights 주면 그걸로.
    fc = np.array([compute_objectives(r.n, V, normals, areas, r.R, r.B, D)
                   for r in reps])
    pick = (weighted_pick(fc, weights) if weights is not None
            else knee_point(fc))

    return reps[:top_k], reps[pick], front, front_costs
```

주의:
- `angular_nms`의 실제 시그니처에 맞춰 인자(정렬 키, 거리 함수)를 조정하라.
  거리는 기존과 동일하게 `d(a,b)=arccos(n_a·n_b)` 사용(부호 유지, `|·|` 아님).
- Pareto 후보가 너무 적거나(<3) 너무 많으면(거의 전부) 로그로 경고를 남겨라.
  거의 전부가 비지배라면 목적 수를 줄이거나 목적 간 상관이 높다는 신호다.

---

## 5. 부호·규약 체크리스트 (반드시 검증)

- [ ] 모든 목적이 **minimize** 방향인가? (`f_support, f_height, f_overhang` 모두 작을수록 좋음 ✓)
- [ ] 자기지지 면적 `P`처럼 "클수록 좋은" 양을 목적에 넣을 땐 `-P`로 부호를 뒤집었는가?
- [ ] `n`과 `-n`이 다른 빌드 자세를 의미하는 기존 규약(yaw/pitch)이 목적 계산에도 일관 적용되는가?
      특히 `f_height`는 `n`/`-n`에 대해 동일하지만, `f_support`(R,B)는 방향 의존이므로 후보별 `n`을 그대로 써라.
- [ ] `D`(bbox diagonal)로 정규화한 `f_height`가 메시 스케일에 불변인가?

---

## 6. 테스트 (작성 요망)

`tests/test_pareto.py`:

1. **toy dominance**: `costs = [[100,50],[120,30],[130,60]]` →
   `pareto_mask` 가 `[True, True, False]` 를 반환해야 한다(세 번째가 첫 번째에 지배됨).
2. **all non-dominated**: 대각으로 트레이드오프되는 점들은 전부 True.
3. **single point**: 후보 1개면 `pareto_mask`=`[True]`, `knee_point`=0.
4. **knee point**: 정규화 후 원점에 가장 가까운 후보가 선택되는지 합성 데이터로 확인.
5. **regression**: `use_pareto=False`일 때 기존 top-k 결과가 바이트 단위로 동일(재현성).
6. **invariance**: 메시를 균일 스케일/회전했을 때 Pareto front 집합(후보 인덱스)이 보존되는지.

---

## 7. (선택) 논문용 한 문단 초안

> We additionally provide a Pareto post-processing mode. Instead of collapsing the
> three cost terms into the scalar `J = R + P + B`, each candidate orientation is
> evaluated on minimization objectives — a unified support cost `R̃ = R + B`, the
> build-direction print height, and the total overhang area — and we retain only the
> non-dominated candidates before angular non-maximum suppression. Because the SFTF
> candidate pool is already small and discrete, the dominance filter is `O(n²m)` and
> negligible in cost. This avoids the unit-mismatch and fixed-weight assumptions of the
> weighted-sum scalarization, and naturally yields a small set of trade-off
> orientations that we present to the user (with a knee-point default), consistent with
> the top-k basin philosophy.

---

## 8. 수용 기준 (Definition of Done)

- `sftf/pareto.py`(+테스트) 추가, 기존 테스트 전부 통과.
- `use_pareto=True` 경로가 동작하고, 비지배 후보 → angular NMS → TOMO 검증까지 연결됨.
- `use_pareto=False`에서 기존 결과 재현(회귀 테스트 통과).
- 5개 표준 메시(Bunny, manikin, dragon, happy, lucy) 중 최소 1개에서 Pareto front 크기와
  knee 추천 방향을 로그로 출력해 sanity check 가능.
