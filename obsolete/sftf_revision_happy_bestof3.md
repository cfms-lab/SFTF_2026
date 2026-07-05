# SFTF 논문 수정 지시서 — best-of-3(happy) 논리 일관성

> 대상 파일: `sftf_draft_byCODEX.tex` (또는 동일 본문의 `SFTF_draft_eng.tex`).
> 목적: best-of-3 값이 높은 happy 케이스를 다루는 서술의 **내부 모순**을 제거하고, 헤드라인 수치의
> 투명성을 높인다. 아래 항목을 순서대로 적용하라.
> 규칙: **숫자를 새로 지어내지 말 것.** 확인이 필요한 수치는 "확인 요망"으로 표시했고, 그 경우
> 저장소의 분석 스크립트/데이터로 실제 값을 검증한 뒤 반영하라. LaTeX 라벨/참조는 그대로 둔다.

---

## 문제 요약 (왜 고치는가)

- §unified는 happy 실패를 *"샘플링 한계 때문이지 스코어링 때문이 아니다(not scoring)"* 라고 단정한다.
- 그러나 §robustness와 표들은 정반대를 보인다:
  - `Table~\ref{tab:sampling}`: happy oracle ratio가 512에서 **4.35**, 2048/4096에서 **1.91**.
    → 방향 수를 늘리면 near-optimal이 후보 풀에 들어온다(순수 샘플링 문제라면 여기서 해결돼야 함).
  - 그럼에도 happy의 untuned $J$ best-of-3는 4096에서도 **10.51**. 즉 좋은 후보가 풀에 있어도 스코어가 못 고른다 → **스코어링 실패**.
  - 메인 설정(512)에서도 달성 **11.23** vs oracle **4.35** → 11.23/4.35 ≈ **2.6배**의 격차가 스코어링에서 발생.
- 결론: happy는 "후보 생성 실패"만이 아니라 **샘플링 + 스코어링 둘 다 실패**다.
  이를 "candidate generation failure"로만 규정해 평균에서 제외하는 현재 논리는 자기 데이터와 모순된다.

---

## 수정 1 (필수) — §unified의 "not scoring" 단정 제거

**위치:** `\label{sec:unified}` 섹션, `Table~\ref{tab:unified-b3}` 직전 문단.

**현재 텍스트 (find):**
```latex
happy is a separate case where the candidate pool itself does not include a near-optimal (\S\ref{sec:robustness}),
and on this mesh the unified term is rather worse, but this is due to a sampling limitation, not scoring.
```

**교체 텍스트 (replace):**
```latex
happy is reported separately as a hard case (\S\ref{sec:robustness}): at the default $512$ directions its
candidate pool does not include a near-optimal direction, and on this mesh the unified term is rather worse.
We emphasize that this failure is \emph{not} purely a sampling artifact. As shown in \S\ref{sec:robustness},
enriching the pool lowers happy's oracle ratio to about $1.91$, yet the achieved best-of-3 remains far above it,
so the residual gap is a scoring failure. happy is therefore limited at both the sampling and the scoring stages,
and we keep it out of the aggregate averages only to avoid letting a doubly-failing outlier dominate them,
not as a claim that scoring is adequate on it.
```

---

## 수정 2 (필수) — §robustness 서술과 표 캡션의 표현 통일

§robustness(line ~1175 부근)의 *"limitations in both sampling and scoring"* 가 정답 서술이다.
이와 충돌하는 "candidate generation failure" 단정 표현 2곳을 완화하라.

**(2a) LOMO 도입 문장 (find):**
```latex
Excluding happy, for which candidate generation itself fails (see the end of \S\ref{sec:cv} below and the oracle),
```
**(replace):**
```latex
Excluding happy, which fails at both the candidate-generation and the scoring stage (\S\ref{sec:robustness}; see the oracle below),
```

**(2b) `Table~\ref{tab:unified-b3}` 캡션 (find):**
```latex
On the average excluding happy (candidate generation failure, \S\ref{sec:robustness}), $\tilde R$ outperforms $J$.
```
**(replace):**
```latex
On the average excluding happy (a hard case that fails at both sampling and scoring, \S\ref{sec:robustness}), $\tilde R$ outperforms $J$.
```

---

## 수정 3 (필수) — 헤드라인 2.37이 happy 제외임을 abstract에 명시

**위치:** abstract.

**현재 텍스트 (find):**
```latex
On stored TOMO\_INT3 grids, cross-validated SFTF candidates achieved a best-of-three support-volume ratio of $2.37$, compared with $3.63$ for PCA axes and $4.30$ for symmetric Support Tensor eigenvectors.
```

**교체 텍스트 (replace):**
```latex
On stored TOMO\_INT3 grids, cross-validated SFTF candidates achieved a best-of-three support-volume ratio of $2.37$ on four of the five meshes (with the hard ``happy'' case, which fails at both the sampling and scoring stages, reported separately), compared with $3.63$ for PCA axes and $4.30$ for symmetric Support Tensor eigenvectors evaluated on the same four meshes.
```

(결론 \section{Conclusion} 에서도 2.37/비교 수치를 다시 언급한다면 동일하게 "four of five / happy separate" 단서를 한 번 더 넣어라.)

---

## 수정 4 (권장) — happy 격차의 샘플링/스코어링 성분 분해 추가

§robustness의 "Sampling Density and Candidate Generation Limit" 문단 끝에 다음 한 문단을 추가해,
제외가 cherry-picking이 아니라 분석임을 보여라. **숫자는 본 지시서 값을 그대로 쓰되 저장소 데이터와 대조 후 확정하라.**

```latex
\paragraph{Decomposing happy's gap.}
It is useful to split happy's large best-of-3 ratio into two multiplicative components: a
\emph{sampling} component, the oracle ratio caused by the pool not containing a near-optimal direction
($4.35$ at $512$ coarse directions, falling to $1.91$ at $2048$), and a \emph{scoring} component, the
ratio of the achieved best-of-3 to that oracle (about $11.23/4.35\approx2.6$ at $512$). Both components
are well above $1$, and the scoring component does not vanish even when the pool is enriched (the achieved
untuned-$J$ ratio is still $10.51$ at $4096$ while the oracle is $1.91$). This is why happy is treated as a
doubly hard case rather than a pure candidate-generation failure.
```

---

## 수정 5 (확인 요망) — Dimensional Normalization 문단의 "raw $J$ = 0.52"

**위치:** §robustness, "Dimensional Normalization of the Objective Function" 문단.

**현재 텍스트 (find):**
```latex
the Spearman correlation of raw $J$ drops greatly from $0.52$ to $0.14$ under min--max normalization
```

**문제:** 어떤 표에도 $J=0.52$는 없다. `Table~\ref{tab:feature-corr}`의 $J$는 Bunny $0.46$, 평균 $0.47$이고,
$0.52$는 `Table~\ref{tab:unified-corr}`의 $\tilde R$(Bunny) 값이다. baseline을 $J$로 적고 실제론 $\tilde R$ 값을
쓴 라벨 혼동으로 보인다.

**조치:** 저장소의 정규화 실험 스크립트/출력으로 이 실험이 (a) 어느 메시(또는 전체 평균)에서, (b) 어느 항
($J$ vs $\tilde R$)을 baseline으로 했는지 확인하라. 확정 후:
- baseline이 실제로 $J$였다면 `0.52`를 그 메시의 올바른 $J$ 값(예: Bunny면 `0.46`)으로 교체.
- baseline이 $\tilde R$였다면 문장의 `raw $J$`를 `the unified term $\tilde R$`로 교체.
**확인 전에는 숫자를 임의로 바꾸지 말고 `% TODO: verify baseline (J vs Rtilde) and value` 주석만 달아라.**

---

## 수정 6 (사소) — 제목 오타: "Tensor Flow" → "Tensor Field"

약어 SFTF = Support Flow Tensor **Field** 인데 제목만 "Flow"다.

**현재 텍스트 (find):**
```latex
\title{Fast Candidate Generation for Support-Minimizing Build Orientation in 3D Printing Using a Support Flow Tensor Flow}
```
**교체 텍스트 (replace):**
```latex
\title{Fast Candidate Generation for Support-Minimizing Build Orientation in 3D Printing Using a Support Flow Tensor Field}
```

---

## 적용 후 확인 (Definition of Done)

- [ ] §unified에 "not scoring" 단정이 더 이상 없고, happy를 "sampling+scoring 둘 다"로 일관되게 서술.
- [ ] abstract(및 결론)의 2.37/비교 수치에 "four of five / happy separate" 단서가 있음.
- [ ] §robustness에 happy 격차의 성분 분해 문단이 추가됨(숫자 저장소 대조 완료).
- [ ] 0.52 수치의 baseline을 검증해 수정했거나, 확정 전이라면 TODO 주석으로 표시.
- [ ] 제목이 "Support Flow Tensor Field"로 수정됨.
- [ ] LaTeX가 오류 없이 컴파일되고, 모든 `\ref`/`\label`이 깨지지 않음.
- [ ] 표의 어떤 수치도 변경하지 않았음(서술/캡션 텍스트만 수정).
