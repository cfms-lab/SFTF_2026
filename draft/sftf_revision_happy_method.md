# SFTF 논문 수정 지시서 2 — happy-method 서사 일관성 (SFTF\_draft\_eng.tex)

> 대상 파일: `SFTF_draft_eng.tex` (happy-method/escalation이 포함된 최신본).
> 목적: 새 happy-method(자동 hard-case escalation)와 충돌하는 옛 "candidate generation failure / not scoring"
> 서술을 통일하고, 검출기 in-sample 한계와 동일-budget baseline 부재를 보완한다.
> 규칙: **표의 수치는 절대 바꾸지 말 것.** 서술/캡션 텍스트만 수정. 새 숫자가 필요한 항목은 "TODO(데이터 필요)"로
> 표시했고, 그 경우 저장소 결과로 검증 전에는 숫자를 지어내지 말 것. `\ref`/`\label`/식 번호는 유지.

---

## 배경 (왜 고치는가)

happy-method는 happy를 **top-30 SFTF 후보 + ±10° 지역 윈도우 검증**으로 ratio $1.06$까지 해소한다
(Table~\ref{tab:happy-method}). 이는 **쓸만한 seed가 후보 풀의 top-30 안(즉 최적 basin의 ±10° 이내)에 이미
존재**했음을 뜻한다. 따라서 happy를 "candidate generation failure / pool에 near-optimal 없음 / scoring 무관"으로
규정한 옛 문장들은 happy-method 결과와 모순된다. happy는 **"날카로운 좁은 basin이라 ranking-only 점-평가가
과소평가하는 케이스이고, 지역 윈도우 검증으로 해소된다"**로 통일해야 한다.

---

## 수정 1a (필수) — §unified의 happy 문단

**현재 (find):**
```latex
happy is a separate case where the candidate pool itself does not include a near-optimal (\S\ref{sec:robustness}),
and on this mesh the unified term is rather worse, but this is due to a sampling limitation, not scoring.
```
**교체 (replace):**
```latex
happy is reported separately: at the default $512$ directions its candidate \emph{points} evaluate far from the
optimum under the ranking-only point metric (oracle $4.35$), and on this mesh the unified term is rather worse.
We stress that this reflects the narrow, sharp optimum basin of happy under point evaluation, not a failure of
candidate generation: as shown in \S\ref{sec:happy-method}, a usable seed lies within the top-$30$ pool (within a
$\pm 10^\circ$ window of the optimum), and local windowed verification recovers a ratio of about $1.06$.
```

## 수정 1b (필수) — Table~\ref{tab:unified-b3} 캡션

**현재 (find):**
```latex
On the average excluding happy (candidate generation failure, \S\ref{sec:robustness}), $\tilde R$ outperforms $J$.}
```
**교체 (replace):**
```latex
On the average excluding happy (a narrow-basin hard case under the ranking-only point metric, resolved by local
verification in \S\ref{sec:happy-method}), $\tilde R$ outperforms $J$.}
```

## 수정 1c (필수) — §cv의 happy 제외 문장

**현재 (find):**
```latex
Excluding happy, for which candidate generation itself fails (see the end of \S\ref{sec:cv} below and the oracle),
```
**교체 (replace):**
```latex
Excluding happy, whose narrow optimum basin makes the ranking-only point metric unrepresentative (it is instead
resolved by local windowed verification, \S\ref{sec:happy-method}; see also the oracle below),
```

---

## 수정 2 (필수) — §robustness 내부 자기모순 (point vs window)

**현재 (find):**
```latex
happy's oracle ratio is $4.35$ at $512$, so its default candidate centers do not sufficiently include the TOMO optimum basin.
```
**교체 (replace):**
```latex
happy's oracle ratio is $4.35$ at $512$: its default candidate \emph{points} evaluate far from the optimum, even
though, as \S\ref{sec:happy-method} shows, a top-$K$ center still lies within a $\pm 10^\circ$ window of the optimum
basin. That is, the pool covers the basin angularly but not as a low-$v_{ss}$ point.
```

---

## 수정 3 (권장) — 검출기 in-sample 한계 명시

§happy-method에서 Table~\ref{tab:happy-method} 직후 문단(adaptive policy가 budget을 줄인다는 문단) 끝에
다음 문장을 **추가**하라.

```latex
We note that the thresholds in Eq.~\eqref{eq:happy-trigger} were set so that the detector fires only on happy among
the five stored meshes, so Table~\ref{tab:happy-method} is in-sample for the detector. The cached A--E audit
(Table~\ref{tab:happy-method-g5}) is the held-out check; it is, however, limited to the $16$ ratio-valid records,
since the remaining meshes have nonpositive TOMO best at $\theta_c=60^\circ$ and leave the ratio undefined.
```

---

## 수정 4 (권장, TODO 데이터 필요) — 동일 budget baseline

리뷰어 핵심 반박: *"같은 $\sim$$3$--$5\%$ grid budget을 균일/무작위 seed 지역검증에 쓰면? SFTF seed가 정말 더
나은가?"* 현재 이 비교가 없다.

조치:
- 저장소에 **uniform-coarse seed(또는 random seed) + 동일 budget 지역검증** 결과가 있으면, Table~\ref{tab:happy-method}에
  baseline 행 1개(예: `Uniform $3.6\%$ seed`)를 추가하고 mean/max ratio를 채워라.
- 결과가 **없으면 숫자를 지어내지 말고**, §happy-method 끝에 한계로 한 문장만 추가하라:
```latex
A controlled comparison against uniform- or random-seed local verification at an equal grid budget is left as
future work; here we report SFTF-seeded verification only. % TODO: add equal-budget seed baseline if data exists
```

---

## 수정 5 (확인 요망) — "raw $J$ = 0.52" 불일치 (재지적)

**위치:** §robustness, "Dimensional Normalization of the Objective Function" 문단.

**현재 (find):**
```latex
the Spearman correlation of raw $J$ drops greatly from $0.52$ to $0.14$ under min--max normalization
```
**문제:** 표 어디에도 $J=0.52$ 없음. Table~\ref{tab:feature-corr}의 $J$는 Bunny $0.46$/평균 $0.47$, $0.52$는
Table~\ref{tab:unified-corr}의 $\tilde R$(Bunny) 값. baseline을 $J$로 적고 실제론 $\tilde R$ 값을 쓴 혼동으로 보임.

**조치:** 저장소 정규화 스크립트로 (a) 어느 메시/평균, (b) baseline이 $J$인지 $\tilde R$인지 확인 후:
- $J$가 맞으면 `0.52`를 올바른 $J$ 값으로 교체.
- $\tilde R$가 맞으면 `raw $J$`를 `the unified term $\tilde R$`로 교체.
확인 전에는 `% TODO: verify baseline (J vs Rtilde) and value` 주석만 달고 숫자 변경 금지.

---

## 수정 6 (선택, 사소) — $\eta\ge0.03$ 절대임계값의 과발화 가능성

§happy-method의 트리거 설명 부근에 한 문장 추가(정확도는 단조성으로 보존되나 budget 낭비 가능성 명시):
```latex
Because $\eta$ is an absolute normalized-support threshold, parts whose true minimal support is inherently large
may trigger escalation even near their optimum; this only spends extra verification budget and never degrades the
selected orientation, but it explains the relatively high trigger rate ($7/16$) in the A--E audit.
```

---

## 적용 후 확인 (Definition of Done)

- [ ] §unified·§cv·§robustness에서 happy를 "candidate generation failure / not scoring / pool에 near-optimal 없음"으로
      단정하는 표현이 모두 "narrow-basin under point metric, resolved by local verification"으로 통일됨.
- [ ] §robustness의 point vs $\pm10^\circ$ window 구분이 명확함(1476 vs 1479 모순 해소).
- [ ] tab:happy-method가 검출기 in-sample이고 A--E가 held-out임이 본문에 명시됨.
- [ ] 동일-budget seed baseline을 추가했거나, 없으면 한계 문장으로 명시(숫자 미조작).
- [ ] 0.52 수치의 baseline 검증 완료 또는 TODO 주석.
- [ ] 표의 어떤 수치도 변경하지 않음. LaTeX가 오류 없이 컴파일되고 모든 `\ref`/`\label` 정상.
