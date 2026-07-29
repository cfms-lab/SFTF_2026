# 복합재 드레이프 논문 투고 전 점검 (검토일: 2026-07-06 · 갱신: 2026-07-06)

> 대상: `SFTF_Composite_dev/draft/main_en.tex`(영문 SCI판) + `main.tex`(국문,
> 섬유공학회지판). 기준: 삼부작 공통 체크리스트(§A 상호인용, §C 일관성, §E 특허)
> + SCI 투고 표준.
>
> **진행 상황 (2026-07-06 갱신):** 원고 편집 항목은 거의 완료. `[x]` = 처리 완료,
> `[~]` = 부분 완료(잔여는 사람/로컬 판단), `[ ]` = 미착수(사람/로컬 몫).
> **남은 것은 편집이 아니라 판단·로컬 작업 4건뿐** — repo 생성·공개, 공저자 확정,
> 특허 여부 확인, 게재지 확정 + 클린 빌드. (하단 "남은 작업" 요약 참조.)

---

## 먼저 — 잘 되어 있는 것 (건드리지 말 것)

- **정직성 톤이 삼부작과 완전히 일관.** "Honest reading" 문단, "Discussion and
  honest limitations", Baraff 정직한 음성(요소별 전단 예측 ≈0), k-means가 강한
  베이스라인임을 인정, region-grow purity 1.000을 우월성으로 안 읽음(과분할
  효과 명시), matched-budget 주의. 초록에도 honest-negative가 실려 있음. 유지.
- **공유 그림 출처 표기 정확.** SFTF Fig.1(unified flow)·Bunny landscape가
  "(Reproduced from the prior work~\citep{sul_sftf})"로 명시됨. 삼부작 §C 요건 충족.
- **solver-in-the-loop 검증 존재.** Baraff–Witkin 천 솔버(cfmsDrape, 자체 DLL)
  + double-dome 벤치마크 + ARAP/LSCM 해석적 교차검증. 무실험 검증 완결.
- **PFTF 미참조 = 올바름.** 프레임워크 전방 인용 없이 깨끗하게 독립. 이대로 둘 것
  (통합은 나중에 PFTF 논문이 역인용). **PFTF 참조를 새로 넣지 말 것.**

---

## P1. 투고 전 반드시 (없으면 데스크 리젝/불비 반려)

### 1-1. 표준 선언부(Statements and Declarations) — ✅ 완료
Conclusion 뒤에 삼부작 문안으로 선언부 3종(영·국문 양쪽) 삽입 완료.
- [x] **Funding** — NRF-2022R1A2C1010072 삽입.
- [~] **Data availability** — 문안·repo URL(`github.com/cfms-lab/SFTFComposite_2026`)
      삽입 완료. **잔여(로컬): 해당 repo를 실제로 생성하고 public 전환**
      (드레이프 필드 코드·`app_case_cache/*.npz`·벤치마크 스크립트 패키징).
      tex에 경고 주석으로 명시됨.
- [x] **Use of AI-assisted tools** — 삼부작 동일 문안 삽입(영·국문).
- [x] **Declaration of conflicting interest / Ethical considerations / Consent**
      — 삽입.
- [x] **Author Contributions** — CRediT 문안 삽입(영·국문).

### 1-2. 저자 정보 블록 — ✅ 완료(공저자 결정만 잔여)
- [x] 소속(Kumoh National Institute of Technology, 소재디자인공학전공, Gumi 39177),
      이메일, ORCID 추가. 이름 `InHwan Sul`로 통일.
- [x] `\date{\today}` → `\date{}` (공란).
- [ ] **공저자 결정(사람)**: 최종 저자 명단 확정. 추가 시 저자 줄 + CRediT +
      교신저자 표기 함께 갱신(tex에 주석 표시해 둠).

### 1-3. 삼부작 상호인용 동기화 — ✅ 완료(게재지 확정 시 최종 갱신)
`references.bib`:
- [x] `sul_sftf`, `sul_sftfclustering`: `and others` 제거(단독저자), 이름 `InHwan`
      통일, 상태 `manuscript in preparation, 2025` → `submitted, 2026`.
- [~] 게재지·권/DOI는 **삼부작 행선지 확정 시** note를 실제 서지로 교체(주석 명시).

---

## P2. 투고 전 권장 (리뷰 1라운드에서 질문 나옴)

### 2-1. 실험 환경/하드웨어 명시 — ✅ 완료
- [x] "구현 환경" 문단(영·국문) 추가: Ryzen 9 9950X3D(16C/32T), 125GB, Windows 11,
      Python 3.12(NumPy/SciPy/Trimesh/scikit-learn) + Open3D + cfmsDrape.
      "보고된 실행 시간은 wall-clock" 명시. 삼부작 하드웨어와 일치.
      (부수: Baraff 소절에 `\label{sec:baraff}` 추가해 상호참조 연결.)

### 2-2. 국문판(main.tex) lockstep 확인 — ✅ 완료(수정 불필요)
- [x] forming·검증 수치 전면 대조 결과 **영·국문 완전 일치**: dome~5°/bowl~40°,
      Spearman 범위, 잔차~0.9cm·전단~19°·Spearman≈0, 4-fold, 더블돔
      39.1°/4.8°/45°/9434면, ARAP 교차검증 6.73e-5/5.83e-5, 타이밍 0.34s/0.22s,
      다트 0.98→0.42. 폐기 구버전값(6.8→9.6°, Spearman 0.1–0.2) 양쪽 모두 부재.
      07-05 재실행값이 양쪽에 이미 반영됨 → **편집 불필요**.

### 2-3. 특허 타이밍 확인 (체크리스트 §E) — [ ] 사람 확인 필요
- [ ] 복합재 드레이프 분할이 **특허 출원 대상인지 확인**. 대상이면 데이터공개
      repo 공개가 출원을 앞서지 않도록 공지예외(§30, 12개월) 타이밍 준수. 대상이
      아니면 제약 없음 — 지도교수/산학협력단과 확인.

### 2-4. locking angle 규약 — ✅ 이미 충족
- [x] 재료 의존 locking angle(기본 45°, 30–50° 범위)을 threshold와 함께 보고.
      삼부작 θc 규약의 복합재 대응으로 충분(확인 완료).

---

## P3. 저비용 정리

- [x] **참고문헌 보강 — 완료.** 복합재 forming/draping 3편 추가(서지 검증·DOI 포함,
      영·국문 lockstep 인용): Prodromou & Chen 1997(locking–주름), Wang·Paton·Page
      1999(kinematic 드레이핑), Boisse et al. 2011(성형 주름). bib 13 → 16편.
- [ ] **SCI 게재지 선정(사람)**: 영문판 "international SCI journal"만 명시.
      후보 — Composites Part A/B, Composite Structures, 또는 CAD/텍스타일 계열.
      국문판은 섬유공학회지로 확정.
- [ ] **클린 빌드(로컬)**: `svg` 패키지 → xelatex + inkscape 경로 필요. 투고 직전
      전체 빌드에서 미해결 참조 0건·그림 누락 0건 재확인(컨테이너엔 pics/·kotex
      자산이 없어 여기선 부분 검증만 수행함).
- [x] **Appendix 2D 패턴 면책 문구** — "first-cut layout, not a production cutting
      file" 이미 명시(양호). 유지.

---

## 남은 작업 (편집 아님 — 사람 판단 / 로컬 실행)

1. **[로컬] 공개 repo 생성·public 전환** — `SFTFComposite_2026`에 드레이프 코드·
   9메시 캐시·벤치마크 스크립트 패키징(단, 3번 특허 확인 후 공개).
2. **[사람] 공저자 최종 확정** — 명단 정해지면 저자 줄·CRediT·교신저자 갱신.
3. **[사람] 특허 대상 여부 확인** — 대상이면 §E 공지예외 타이밍부터.
4. **[사람] SCI 게재지 확정** → **[로컬] 클린 빌드**(참조·그림 0건) → 투고.
5. **[연동] bib 게재지 갱신** — 삼부작 행선지 확정 시 `sul_sftf`/`sul_sftfclustering`
   note를 실제 서지(권/DOI)로 교체.

## 하지 않을 것
- PFTF 프레임워크를 이 논문에 전방 인용(미출판 의존성 생성). 통합은 PFTF 논문이
  이 논문을 역인용해서 한다.
- 정직한 음성 결과(Baraff 요소별 전단 예측 ≈0)를 약화·은폐. 이 논문의 신뢰
  자산이다 — 삼부작과 동일 원칙.
- 다 된 원고를 PFTF 실증부로 접어 넣기(별도 독립 SCI로 내보내는 것이 확정).
