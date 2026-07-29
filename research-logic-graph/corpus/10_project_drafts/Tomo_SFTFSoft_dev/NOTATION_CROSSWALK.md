# SFTFSoft notation crosswalk

작성일: 2026-07-15
적용 버전: `SFTFSoft-v1-centroid`
상태: legacy-baseline semantics 고정; 본문 수치와 구현은 변경하지 않음

## 핵심 대응

| 현재 원고 | 계열 표준 | 해석 |
|---|---|---|
| source face \(i\) | face-level legacy source | SFTF-v2 surface sample과 다름 |
| centroid affinity \(a_{ij}\) | \(a_{ij}^{\mathrm{cent}}\) | ray-hit opacity가 아님 |
| \(\pi_{ij}\), \(\pi_i^{\mathrm{bed}}\) | \(\pi_{ij}^{\mathrm{cent}}\), \(\pi_{iB}^{\mathrm{cent}}\) | centroid/kNN attention |
| hard receiver \(t_i\) | \(H^{\mathrm{sftf}}\)의 output | support-admissible ray router |
| \(J_w=w_RR+w_PP+w_BB\) | legacy weighted objective | SFTF-v2 score와 동일하지 않음 |
| \(L_{\mathrm{SFTF}}\) | centroid-relaxed loss | DFSVR union volume과 동일하지 않음 |

## sharp-limit 문장의 정확한 범위

\(\pi^{\mathrm{cent}}\)의 temperature가 0으로 가면 positive score margin 아래
affinity maximizer에 집중한다. hard ray receiver로의 수렴은 다음 별도 조건이
있을 때만 corollary다.

\[
\operatorname*{arg\,max}_{j\in\mathcal C(i)\cup\{B\}}
a_{ij}^{\mathrm{cent}}=t_i^{\mathrm{hard}}.
\]

ray가 맞지 않는 face의 centroid가 더 가까우면 sharpening은 오배정을
강화한다. 따라서 본 원고를 EB-DFSVR의 ray-consistent first-hit theorem으로
인용하지 않는다.

## revision에서 적용할 변경

1. 모든 attention probability에 `cent` superscript를 붙인다.
2. 첫 Method 문단에 `SFTFSoft-v1-centroid`를 표시한다.
3. 결론의 convergence 문장은 `receiver agreement + positive margin` 조건을
   항상 함께 적는다.
4. `SFTF-v2-surface`, `DFSVR-v1-dense`, `EB-DFSVR-v2-sparse`와 수치적
   동일성을 주장하지 않는다.
5. critical angle은 공통 threshold \(t_d\)와 입력 angle semantics를 함께 기록한다.
