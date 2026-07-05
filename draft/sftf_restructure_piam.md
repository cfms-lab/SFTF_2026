# SFTF 논문 구조 재배치 지시서 — PiAM(Progress in Additive Manufacturing)용

> 대상 파일: `SFTF_draft.tex`
> 목적: PiAM은 섹션 구조를 강제하지 않으나, 현재 원고는 최상위 `\section`이 ~14개로 지나치게 평평하다.
> 이를 계산·방법론 논문에 맞는 7개 최상위 섹션(저자의 섬유·고분자식 IMRaD 정신을 유지하되 계산 논문으로 매핑)으로
> 재계층화한다. **본문 텍스트·표·수치·`\label`은 일절 바꾸지 말 것.** 바꾸는 것은 오직 헤딩 명령
> (`\section`↔`\subsection`↔`\subsubsection`)과 그 묶음 순서뿐이다.

---

## 핵심 규칙 (Codex 필독)

1. **내용 불변**: 단락 텍스트, 수식, 표, 그림, `\label{...}`, `\ref{...}`, `\cite{...}`는 그대로 둔다.
2. **레벨 강등은 연쇄적으로**: 어떤 `\section`을 `\subsection`으로 내리면, 그 안에 있던 기존 `\subsection`은
   모두 `\subsubsection`으로 한 단계씩 함께 내려야 한다(번호 계층이 깨지지 않도록).
3. **라벨 보존으로 참조 안전**: 섹션 번호는 자동 재계산되므로 `\ref`는 건드릴 필요 없다. `\label`도 그대로 둔다.
4. 적용 후 **LaTeX가 오류 없이 컴파일되고 목차(\tableofcontents가 있다면)와 모든 상호참조가 정상**인지 확인한다.

---

## 목표 최상위 구조 (7개 \section + 부록)

1. `\section{Introduction}`
2. `\section{Method}`  ← 신설 묶음
3. `\section{Evaluation Protocol and Datasets}`  ← 신설 묶음
4. `\section{Results and Discussion}`  ← 신설 묶음
5. `\section{Conclusion}`
6. `\section*{Statements and Declarations}`  (PiAM 필수, 이미 존재 — 유지)
7. References (`\bibliography` 등 — 유지)
8. Appendix (부록 — 유지, 단 \appendix 이후로 모음)

---

## 매핑 표 (현재 헤딩 → 새 위치/레벨)

> "현재"는 SFTF\_draft.tex의 헤딩 텍스트 기준. 새 레벨로 바꾸되 텍스트는 동일하게 유지.

### 1. Introduction (변경 없음 — 그대로 유지)
- `\section{Introduction}` 및 그 하위 `\subsection` 4개(Build Orientation…, Related Work, Optimal Orientation Search…MSST, GPU-MSST…, This Study…)는 **현 상태 유지**.

### 2. Method (다음 현재 `\section`들을 이 섹션의 `\subsection`으로 강등하여 이 순서로 모음)
- `The Baseline (Symmetric) Support Tensor and Its Limitations` → `\subsection`
- `Per-Direction Support Flow Tensor Field` → `\subsection`
- `Ray Casting and Valid Support Relationships` → `\subsection`
- `Build Plate Term` → `\subsection`
  - 그 하위 `Virtual Ground Node Interpretation of the Build Plate` → `\subsubsection`(연쇄 강등)
- `Per-Direction Objective Function` → `\subsection`
- `Spherical Sampling and Local Re-search` → `\subsection`
- `Computational Acceleration and Final Candidate Rescoring` → `\subsection`
  - 그 하위 `Final Candidate Rescoring Based on TOMO Results` → `\subsubsection`
- `Current Implementation Pseudocode` → `\subsection`

즉 `\section{Method}`를 새로 만들고 위 항목들을 그 아래로 넣는다(원래 순서 보존).

### 3. Evaluation Protocol and Datasets
- `Comparison Targets and Evaluation Protocol` → 이 섹션의 첫 `\subsection`.
- (선택, 권장) 현재 5-group 절 안의 `Experimental Setup`(하드웨어/소프트웨어/데이터셋 A–E 설명)을 이 섹션으로
  **이동**하여 `\subsection{Datasets and Experimental Setup}`으로 둔다. 이동이 부담되면 생략하고 원위치 유지해도 됨
  (그 경우 이 섹션은 평가 프로토콜만 포함). `% NOTE: optional move` 주석을 남겨라.

### 4. Results and Discussion (다음 현재 `\section`들을 이 섹션의 `\subsection`으로 강등하여 이 순서로 모음)
- `Comparison with Stored TOMO_CPU Results` → `\subsection`
  - 그 하위 `Marking the Optimal Orientation Based on Top-k Basins…` → `\subsubsection`
- `Method Analysis: Local Verification, Feature Contribution, Cross-Validation, Comparison with Existing Methods`
  → `\subsection`. 단 제목이 길므로 `\subsection{Accuracy and Feature Analysis}` 정도로 줄이고,
  그 아래 기존 하위절들(Local TOMO Verification Budget Curve, Happy-Method…, Feature Correlation…Ablation,
  Reformulation into a Unified Tensor…, Cross-Validation of Rank Tuning, Unified Comparison with Existing Methods,
  Additional Robustness Analysis…)은 모두 `\subsubsection`으로 한 단계 강등.
- `Verification against Four Implementations on a Controlled Five-Group Shape Set` → `\subsection`.
  그 아래 기존 하위절들(Experimental Setup[§3로 옮기지 않은 경우], Overall Computation Time…, Group-wise Averages…,
  Scalability…, Per-Direction Cost Structure…, Support Volume…Critical Angle, Agreement…, Discussion: Ray Budget K_ray)
  은 모두 `\subsubsection`으로 강등.

### 5. Conclusion (변경 없음)

### 6. Statements and Declarations (변경 없음 — PiAM 필수, 이미 충족)

### 부록 (변경 없음)
- `\appendix` 이후의 `TOMO_CPU v_ss Contour Landscapes` 등은 부록으로 유지. (Ground-node 증명, rank-tuning 상세가
  본문 뒤 부록에 있다면 함께 \appendix 뒤에 둔다.)

---

## PiAM 형식 요건 체크 (구조와 별개로 점검)

- [ ] **Abstract 150–250 단어** 범위인지 확인(현재 초록 단어 수 세기). 벗어나면 길이 조정.
- [ ] **Keywords 4–6개**인지 확인(현재 keyword 개수 점검).
- [ ] 제목면 요건: 제목·저자·소속·교신저자·ORCID. (double-anonymous 제출이면 저자정보는 별도 title page로 분리)
- [ ] **Statements and Declarations** 존재 — 충족(유지).
- [ ] 아티클 타입별 분량 가이드(Research/Technical Paper 등)는 PiAM 공식 제출 페이지에서 현재 수치를 확인하고,
      본 원고가 길므로 한도 초과 여부를 점검. `% TODO: verify PiAM word-count limit for chosen article type`

---

## 적용 후 확인 (Definition of Done)

- [ ] 최상위 `\section`이 Introduction / Method / Evaluation Protocol and Datasets / Results and Discussion /
      Conclusion / Statements and Declarations(+References, Appendix) 구조로 정리됨.
- [ ] 강등된 모든 헤딩의 자식 헤딩이 한 단계씩 함께 강등되어 계층이 일관됨.
- [ ] 본문 텍스트·표·수치·`\label`·`\cite` 변경 없음.
- [ ] LaTeX 정상 컴파일, 모든 `\ref` 정상, 그림/표 번호 깨짐 없음.
- [ ] Abstract 단어 수·Keywords 개수·분량 한도 점검 완료(또는 TODO 표시).
