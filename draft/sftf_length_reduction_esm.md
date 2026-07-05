# SFTF 논문 분량 축소 지시서 (PiAM 2,000–4,000단어 권고) — ESM 활용

> 대상: 본문 `SFTF_draft.tex` + 신규 보충자료 `SFTF_supplementary.tex`.
> 목표: 본문 단어 수를 PiAM research paper 권고(2,000–4,000)에 최대한 근접시키되, **작업물은 삭제하지 않고**
> 비핵심 표·그림·세부 분석을 ESM(Electronic Supplementary Material)으로 이동한다.
> 현실 주의: 방법 유도 + 핵심 결과를 유지하면 본문이 4,000을 다소 넘길 수 있다. 이는 권고치이며 ESM과 함께라면
> 통상 허용되므로, **"권고치에 근접 + 비핵심 전량 ESM 이전"**을 목표로 한다(억지 삭제로 핵심을 훼손하지 말 것).
> 규칙: 표·수치 자체는 변경 금지(이동/재번호만). `\label`은 유지하되 ESM 이전 항목은 S-번호로 재라벨.

---

## 0. 메커니즘 (Codex 먼저 수행)

1. 새 파일 `SFTF_supplementary.tex`를 만든다(독립 컴파일 가능한 최소 프리앰블 + S-번호 캡션).
   ```latex
   \documentclass[11pt,a4paper]{article}
   \usepackage{kotex,amsmath,amssymb,graphicx,booktabs,float,geometry,hyperref}
   \usepackage[labelfont=bf]{caption}
   \geometry{margin=25mm}
   \renewcommand{\thetable}{S\arabic{table}}
   \renewcommand{\thefigure}{S\arabic{figure}}
   \title{Electronic Supplementary Material:\\ Fast Candidate Generation for Support-Minimizing Build Orientation (SFTF)}
   \date{}
   \begin{document}\maketitle
   % moved tables/figures go here, in the order listed in Section 2 below
   \end{document}
   ```
2. 본문에서 표/그림 블록을 **잘라내어** 위 파일로 옮기고, 그 자리에는 한 줄 포인터를 남긴다:
   예) `... (Supplementary Table~S1).` / `... (Supplementary Fig.~S1).`
   본문 측 포인터는 `\ref`를 쓰지 말고 "Supplementary Table~S\#"처럼 **고정 문자열**로 적는다(파일이 분리되므로).
   ESM으로 옮긴 표/그림의 `\label`은 `tab:..` → `stab:..`, `fig:..` → `sfig:..`로 바꾸고, 본문에 남아 있던
   그 항목으로의 `\ref`가 있으면 모두 고정 문자열 포인터로 교체한다(댕글링 참조 방지).
3. 옮긴 순서대로 S1, S2 … 번호가 매겨지도록 `SFTF_supplementary.tex`에 배치한다.

---

## 1. 각주 삭제 (1순위, 최소 위험·최대 효과)

본문의 **개념 정의용 각주**를 삭제한다(AM 독자에게 상식). 아래 주제의 `\footnote{...}`를 제거:
Rayleigh quotient, 고윳값/고유벡터, positive semidefinite, SVD/특이값, nuclear norm, Spearman 상관,
ridge regression, stratified sampling, Fibonacci sphere(golden angle), NMS, cross-validation(LOMO),
min–max 정규화, z-score 정규화, ray casting, structure/orientation tensor.
**예외(남길 것):** "rank tuning은 본 논문 고유 용어"라는 설명 각주 1개, 그리고 5그룹 sweep 그리드($3^\circ$/$1^\circ$,
$9\times$) 각주.

---

## 2. ESM으로 이동 (2·3순위, 최대 감량)

아래 표·그림을 `SFTF_supplementary.tex`로 이동하고, 본문에는 결과 문장 1개 + 포인터만 남긴다.

### 표 (이동)
- `tab:fivegroup-timing` (35-메시 4-구현 전체 타이밍) → **S1**. 본문엔 그룹 평균표(`tab:fivegroup-impl`)만 유지.
- `tab:fivegroup-structure` (R/P/B/hit 분해) → **S2**. 본문엔 "볼록형은 $B$만, 유기형은 $R,P,B$ 공존" 한 문장.
- `tab:critangle` (임계각별 $v_{ss}$) → **S3**. 본문엔 "$\theta_c$↑ → $v_{ss}$ 단조감소, 최적 방향 이동" 한 문장.
- `tab:sampling` (coarse 방향수별 oracle) → **S4**. 본문엔 "happy는 $512$에서 oracle $4.35$, $2048$에서 $1.91$" 한 문장.
- `tab:ablation` (목적함수 best-of-3 ablation) → **S5**. 본문엔 `tab:feature-corr`만 유지하고
  "nuclear/$\sigma_1$는 후보 선택을 바꾸지 않음, tensor-only 변형이 최악" 한 문장.
- `tab:unified-b3` (J vs $\tilde R$ best-of-3) → **S6**. 본문엔 `tab:unified-corr`(상관) 유지 + "happy 제외 평균 $2.82\to2.50$" 한 문장.

### 그림 (이동)
- `fig:five-group-best-worst` (Polyscope best/worst 오버레이; TOMO-검증 아님) → **S(다음 번호)**.
- Bunny $K_{ray}$ 관련 그림(예: `fig:bunny-kray3000` 및 동類 sampling 그림) → ESM.
- 부록 landscape 5개 중 **happy(before/after)와 dragon 1개만 본문 유지**, 나머지(bunny·manikin·lucy contour) → ESM.

> `\ref`로 이 항목들을 부르던 본문 위치는 모두 "Supplementary Table~S\#/Fig.~S\#" 고정 문자열로 교체.

---

## 3. 본문 압축 (4·5순위)

- **§Related Work**: 텐서/이방성 계열(Gaynor·Garcke·Shin) 비교를 3–4문장으로 압축, 본 연구와의 차별점 1문장만 강조.
- **§Computational Acceleration and Final Candidate Rescoring**: first-hit fallback·캐싱 프로파일링 수치($15.7\to1.5$s 등)는
  ESM 또는 1문장으로 축약("구현 수준 가속으로 결과 불변, 세부는 ESM").
- **§Five-Group 전체**: 타이밍 표를 ESM(S1)으로 보냈으므로 본문은 "fixed-cost vs adaptive-cost" 대비 + 속도배수
  ($1.4$–$34\times$, C++ $10$–$5{,}160\times$) + "알고리즘 축 > 백엔드 축" 결론을 **한 단락**으로 통합.
  TOMO_CPU vs CUDA 상세 논의는 2문장으로 축약.
- **§Robustness**(critical-angle matching, dimensional normalization): 각 결론 1문장만 남기고 수치 세부는 ESM 각주/문장으로.
- **중복 프레이밍 통합**: "SFTF는 대체가 아니라 warm-start"와 "ground-node 통합" 설명이 Abstract·Intro·Method·§unified·
  Conclusion에 반복됨. 각 개념을 **최초 등장 위치 1곳**에만 충실히 두고, 이후 재언급은 1줄로 축약.

---

## 4. 절대 유지 (본문에 남길 핵심 — 손대지 말 것)

- SFTF 비대칭 텐서 정의(§Method)와 ground-node 유도 Eq.~\eqref{eq:Rtilde} 전체.
- `tab:budget-curve`, `tab:budget-matched-baseline` (warm-start 핵심 근거).
- `tab:happy-method`, `tab:happy-method-g5` (happy-method; g5는 필요시 그룹열만 남겨 소폭 압축 가능).
- `tab:feature-corr`(상관), `tab:lomo-cv`(교차검증), `tab:unified`(PCA·Support Tensor 비교), `tab:unified-corr`.
- `tab:sftf-tomo-comparison`(저장 그리드 정확도; 캡션·주석은 압축 가능, 표값 유지).
- happy before/after 그림 1개.

---

## 5. 적용 후 확인 (Definition of Done)

- [ ] `SFTF_supplementary.tex`가 단독 컴파일되고, 이동 표/그림이 S1, S2 … 순서로 번호 매겨짐.
- [ ] 본문에서 이동 항목은 모두 "Supplementary Table~S\#/Fig.~S\#" 포인터로 대체되고, 댕글링 `\ref` 없음.
- [ ] 1순위 정의성 각주가 삭제됨(예외 2개만 잔존).
- [ ] §Five-Group·§Robustness·§Related Work가 지정대로 압축되고, 중복 프레이밍이 1곳으로 통합됨.
- [ ] 4번 "절대 유지" 항목이 본문에 그대로 있음. 표·수치 변경 없음.
- [ ] **본문 단어 수를 측정해 보고**(예: `texcount SFTF_draft.tex`), 결과를 주석이나 커밋 메시지에 남김.
      목표는 권고 상한 근접; 초과 시 §3 압축을 추가 적용. `% WORDCOUNT: <측정값>`
- [ ] 본문/ESM 모두 LaTeX 정상 컴파일, 그림·표 번호·인용 정상.
