# SFTF 논문 수정 지시서 3 — 잔여 정합성/표기 (SFTF\_draft.tex)

> 대상 파일: `SFTF_draft.tex` (happy-method + budget-matched baseline 포함 최신본).
> 목적: 남은 사소한 불일치 3건(숫자 오타, "Uniform" 용어 충돌, 결론-초록 강조 불일치)을 정리한다.
> 규칙: **표의 수치는 변경 금지.** 라벨/본문 텍스트만 수정하고, 추가 문장의 숫자는 기존 표값
> (`tab:budget-curve`/`tab:budget-matched-baseline`)과 일치하는 것만 사용했다. `\ref`/`\label` 유지.

---

## 수정 1 (필수) — "36 meshes" → "35 meshes" 오타

본문 전체가 35개(A–E = 5+5+5+10+10)인데 각주 한 곳만 36으로 적혀 있다.

**현재 (find):**
```latex
\footnote{To handle a large-scale batch that sweeps $36$ meshes over $5$ critical angles
```
**교체 (replace):**
```latex
\footnote{To handle a large-scale batch that sweeps $35$ meshes over $5$ critical angles
```
(만약 의도적으로 36개를 돌렸다면, 본문의 다른 "35"들과 어느 메시가 추가됐는지 맞춰서 반대로 통일하라.
기본은 35로 통일.)

---

## 수정 2 (필수) — "Uniform" 라벨 충돌 제거

두 표에서 "Uniform"이 정반대를 뜻한다:
`tab:happy-method`의 "Uniform top-30" = **SFTF seed를 모든 메시에 균일 적용**(SFTF 기반),
`tab:budget-matched-baseline`의 "Uniform matched" = **비-SFTF 기하 farthest-first 축**.
독자가 두 표를 비교할 때 혼동하므로 이름을 분리한다.

**(2a) `tab:happy-method`의 행 라벨 (find):**
```latex
Uniform top-$30$ & 5/5 & 1.01 & 1.06 & 5.43\% & 5/5\\
```
**(replace):**
```latex
All-mesh top-$30$ & 5/5 & 1.01 & 1.06 & 5.43\% & 5/5\\
```

**(2b) 본문의 같은 항목 언급 (find):**
```latex
The adaptive policy recovers the same maximum ratio as the uniform top-$30$ budget,
```
**(replace):**
```latex
The adaptive policy recovers the same maximum ratio as the all-mesh top-$30$ budget,
```

**(2c) `tab:budget-matched-baseline`의 행 라벨 (find):**
```latex
Uniform matched & 1.64 & 1.38 & 2.79 & 3.57\% & 4/5\\
```
**(replace):**
```latex
Uniform-axis matched & 1.64 & 1.38 & 2.79 & 3.57\% & 4/5\\
```

**(2d) baseline 설명 문장 (find):**
```latex
The uniform control uses the same $512$ Fibonacci-sphere axes in a purely geometric farthest-first order,
```
**(replace):**
```latex
The uniform-axis control uses the same $512$ Fibonacci-sphere axes in a purely geometric farthest-first order,
```

**(2e) happy-method 절의 마무리 문장 (find):**
```latex
are substantially more useful than non-adaptive uniform or random windows at the same grid budget.
```
**(replace):**
```latex
are substantially more useful than non-adaptive uniform-axis or random windows at the same grid budget.
```

---

## 수정 3 (권장) — 결론과 초록의 강조점 일치

초록은 지역검증 헤드라인(top-20, $3.57\%$, mean $1.13$)을 전면에 내세우는데, 결론은 ranking-only/tensor 위주라
강조점이 어긋난다. §Conclusion에서 후보 선택을 설명하는 문단 끝 문장
`...to choose promising orientations to pass to slicer/TOMO verification.` **뒤에** 다음 문장을 추가하라.

```latex
When used this way, verifying the $\pm 10^\circ$ neighborhoods of only the top-$20$ candidates recovers a mean
support-volume ratio of $1.13$ (maximum $1.58$) while inspecting $3.57\%$ of the $1^\circ$ grid, and the
happy-method automatically widens this budget only for detected hard cases (\S\ref{sec:happy-method}).
```
(이 숫자들은 `tab:budget-curve`/`tab:budget-matched-baseline`의 기존 값과 일치하므로 새 수치가 아니다.)

---

## 적용 후 확인 (Definition of Done)

- [ ] 파일 전체에서 메시 개수가 35로 통일됨(36 잔존 없음).
- [ ] "Uniform top-30"이 "All-mesh top-30"으로, "Uniform matched"가 "Uniform-axis matched"로 바뀌어
      두 표의 라벨이 서로 다른 의미로 명확히 구분됨.
- [ ] 결론에 지역검증 헤드라인 문장이 추가되어 초록과 강조점이 일치함(숫자는 기존 표값과 동일).
- [ ] 표의 어떤 수치도 변경되지 않음. LaTeX 정상 컴파일, 모든 `\ref`/`\label` 유지.
