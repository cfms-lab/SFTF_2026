# SFTF 본문 1° 전파 지시서 (ESM은 1°, 본문은 아직 3°)

> 대상: 본문 `SFTF_draft.tex` (ESM `SFTF_supplementary.tex`는 이미 1°로 일관).
> 문제: A–E 5그룹 타이밍/임계각 데이터가 1°로 재생성되어 ESM Table S1·S3은 1°인데, **본문은 아직 3°**라
> Table 10(요약)과 Table S1(상세)이 ~9–12× 모순된다. 본문 전체를 1°로 통일한다.
> 규칙: 아래 수치는 ESM S1(1°)에서 산출. py·C++ 시간은 격자 무관이라 불변. **표 생성 스크립트가 있으면 그 출력으로
> 교차검증**하고, 손계산 값과 다르면 스크립트 출력을 우선한다.

---

## 수정 1 (필수) — 속도배수 갱신 (3° → 1°)

3° 기준 "1.4–34× Python / 10–5,160× C++"를 **1° 기준 "≈8–382× Python / ≈57–56,000× C++"**로 바꾼다.
(1° TOMO sweep이 ~9–12× 느려져 배수가 커짐 — 논문에 유리한 방향.)

적용 위치 3곳:
- **초록**: 5그룹 속도 언급 문장.
- **기여 목록 (v)**: `... showing 1.4--34$\times$ Python and 10--5{,}160$\times$ C++ speedups relative to TOMO\_CPU on a 3$^\circ$ sweep.`
  → `... showing $8$--$382\times$ Python and $57$--$56{,}000\times$ C++ speedups relative to TOMO\_CPU on a 1$^\circ$ sweep.`
- **§4.4 본문**: `Over all 35 meshes, Python SFTF is 1.4--34$\times$ faster than TOMO\_CPU, while SFTF\_C++ is 10--5{,}160$\times$ faster.`
  → `Over all 35 meshes, Python SFTF is $8$--$382\times$ faster than TOMO\_CPU, while SFTF\_C++ is $57$--$56{,}000\times$ faster.`

---

## 수정 2 (필수) — 본문의 "3°" → "1°" 문자열 교체

A–E 감사 격자를 가리키는 모든 "3$^\circ$"(`3\textdegree` 또는 `$3^\circ$`)를 1°로 교체:
- **§4.4 도입**: `on the same 3$^\circ$, $\theta_c=60^\circ$ sweep setting` → `on the same 1$^\circ$, $\theta_c=60^\circ$ sweep setting`.
- **Table 5 캡션**: `... ratio-valid 3$^\circ$, $\theta_c = 60^\circ$ TOMO\_CPU records` → `... ratio-valid 1$^\circ$, $\theta_c = 60^\circ$ TOMO\_CPU records`.
- **Table S1 참조 문맥**(있다면) 및 기타 "3° sweep/audit/grid" 표현 전부 1°로.
> 주의: 본문의 다른 1° 표현(5-메시 정확도)은 그대로 둔다. 바꾸는 건 **A–E 감사/타이밍 관련 3°**만.

---

## 수정 3 (필수) — Table 10(그룹 평균) 1° 값으로 교체

CPU·CUDA 시간과 두 속도비 열만 바뀐다(**py·C++ 열은 격자 무관이라 현재 값 유지**).
표 본문(데이터 행)을 아래로 교체:

```latex
A & 42.75 & 15.36 & 0.32 & 8.9    & $54$--$382\times$  & $0.23$--$0.58$\\
B & 42.45 & 14.94 & 0.38 & 9.3    & $58$--$269\times$  & $0.28$--$0.45$\\
C & 51.48 & 60.13 & 1.85 & 183.6  & $23$--$37\times$   & $0.80$--$1.40$\\
D & 53.58 & 112.39 & 2.17 & 124.5 & $13$--$129\times$  & $0.46$--$3.27$\\
E & 643.75 & 740.88 & 15.57 & 3123.5 & $8.3$--$59\times$ & $1.06$--$1.69$\\
```
(열 순서가 `CPU(s) CUDA(s) py(s) C++(ms) CPU/py CUDA/CPU`인 경우. 현재 표의 열 순서에 맞춰 배치하라.
py·C++ 열은 현재 Table 10 값과 동일하므로 변경 없음.)

> 검증: 표 생성 스크립트가 있으면 S1(1°)로부터 다시 뽑아 위 값과 대조. CUDA가 단순 A/B에선 빠르고($<1$)
> 유기·대형 C/D/E에선 종종 느린($>1$) 정성적 패턴은 1°에서도 유지되므로 §4.4의 해당 서술은 그대로 둔다.

---

## 수정 4 (필수) — 각주 2 및 §3.2 재서술 (격자 분리 근거 소멸)

이제 5-메시 정확도와 A–E 감사가 **둘 다 1°**이므로 "3°라서 분리/9× 운운" 설명은 틀린다.

- **각주 2**(page 10, "The five-group audit uses a coarser 3° … about 9× smaller …") → 삭제하거나 다음으로 교체:
  ```latex
  \footnote{Both the five-mesh accuracy benchmark and the A--E audit use a $1^\circ$, $\theta_c=60^\circ$ TOMO\_CPU grid; the A--E audit additionally reports per-mesh timing and scalability over the $35$-mesh set.}
  ```
- **§3.2 끝 문장**(현재 "five-mesh accuracy results use the stored 1° grids; the A–E audit uses a coarser 3° grid … not mixed with the 1° headline …") → 다음으로 교체:
  ```latex
  All TOMO\_CPU grids in this paper use a $1^\circ$, $\theta_c=60^\circ$ resolution: the five-mesh set provides the headline accuracy reference, while the A--E set is used for scalability and held-out implementation audits.
  ```

---

## 수정 5 (확인 요망) — Table 5(AVE 감사)와 그 인용 수치

Table 5(A–E AVE 감사)도 1° 데이터로 재생성되었는지 확인하라.
- **budget %는 격자에 거의 무관**(±10° 윈도우/전체 셀 비율이 3°·1°에서 ~동일)하므로 7.25%·4.96% 등은 거의 그대로일 가능성이 높다.
- **정확도 비율(top-10 max 12.44, AVE 후 1.62, 그룹별 max)**은 1°에서 미세하게 달라질 수 있으니, **재생성된 1° 감사 출력으로 대조**하라.
- 초록·본문의 "max 12.44 → 1.62 at 4.96%" 수치도 Table 5와 **반드시 동일**하게 유지.
- 만약 Table 5가 아직 3° 캐시라면, S1과 같은 1° 그리드로 **재생성**해야 A–E 내부 격자가 통일된다.
  미확인 상태면 `% TODO: confirm Table 5 audit regenerated at 1deg; verify ratios/budget against 1deg cache` 주석을 남겨라.

---

## 적용 후 확인 (Definition of Done)

- [ ] 본문에서 A–E 관련 "3°"가 모두 "1°"로 바뀜(5-메시 정확도의 1°는 그대로).
- [ ] 속도배수가 초록·기여(v)·§4.4에서 8–382× / 57–56,000×로 일관됨.
- [ ] Table 10 CPU·CUDA·속도비 열이 1° 값으로 교체되고, py·C++ 열은 불변. 스크립트 출력과 대조 완료.
- [ ] 각주 2·§3.2의 격자 분리 설명이 "둘 다 1°"로 재서술됨(모순 문구 잔존 없음).
- [ ] Table 5 캡션이 1°이고, 그 수치가 1° 감사와 일치(또는 TODO 주석). 초록의 12.44/1.62/4.96%가 Table 5와 일치.
- [ ] Table 10(본문)과 Table S1(ESM)이 더 이상 모순되지 않음(같은 1° 데이터의 요약/상세).
- [ ] LaTeX 정상 컴파일, 표·그림·인용 정상.
