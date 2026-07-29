# TDP manuscript handoff: clean-room review and rev1 continuation (2026-07-19)

내일 `Tomo_SFTF_dev`에서 TDP 원고 개정을 이어가기 위한 기록이다. 이 문서는 논문 패키지의 동결 심사 결과와 저자 판단, 현재 `rev1` 생성 상태를 연결한다.

## 1. 관련 경로

- 논문 작업 패키지:
  `D:\OneDrive\Documents\__PaperWorks\__InProgress\__SFTF논문작성(2026)\SFTF_TDP(2026)\2026-07-18_TDP_draft`
- 코드 저장소:
  `D:\__SFTF_Projects(2026)\Tomo_SFTF_dev`
- 동결된 심사 결과:
  `2026-07-18_TDP_draft\review_outputs\`
- 작업 중 수정본:
  `2026-07-18_TDP_draft\rev1\`
- DOCX 서식 기준:
  `2026-07-18_TDP_draft\SFTF_style_template.dotx`

## 2. clean-room peer review 결과

과거 대화·메모리·부모 저장소를 사용하지 않은 네 개의 격리 심사를 먼저 동결한 뒤 메타 심사를 수행했다.

- Editor/desk-risk: Major revision, confidence 91/100
- Technical/scientific: Major revision, confidence 93/100
- Statistics/reproducibility: Major revision, confidence 94/100
- Adversarial rejection: Reject, confidence 94/100
- Meta-review: Reject in present form, confidence 95/100

주요 산출물:

- `review_outputs/05_META_REVIEW.md`
- `review_outputs/CLAIM_EVIDENCE_MATRIX.md`
- `review_outputs/PRE_SUBMISSION_BLOCKERS.md`

심사 중 동결 manifest에 포함된 211개 원고·코드·결과 파일은 해시 불일치 0건이었다. 원고는 독립 보고서가 모두 동결될 때까지 수정하지 않았다.

## 3. policy lock에 대한 저자 판단

메타 심사는 finalized pre-outcome `policy_lock.json` 부재를 confirmatory/prospective claim의 치명적 결함으로 보았다. 그러나 TDP submission guideline은 일반 계산 연구에 prospective registration이나 policy lock을 의무화하지 않는다.

따라서 다음과 같이 정리한다.

1. 기존 60-mesh 결과에 사후 lock을 만들어 prospective evidence로 주장하지 않는다.
2. 새 untouched cohort를 즉시 수행할 필요는 없다.
3. 원고에서 `prospectively locked`, `confirmatory validation`, `pre-specified`, `independent confirmation` 같은 표현을 제거한다.
4. geometry-only hash selection과 manifest는 사실 그대로 보고한다.
5. 분석은 `retrospective evaluation`, `held-out evaluation`, 또는 `reference-model sensitivity evaluation`으로 표현한다.
6. lock 부재는 Methods/Limitations에서 짧게 공개하되 논문의 중심 결함처럼 과장하지 않는다.
7. post hoc budget/subgroup 결과는 exploratory/hypothesis-generating으로 제한한다.

핵심 결론: **TDP 투고를 위해 새 prospective cohort는 필수적이지 않다. 필요한 것은 claim calibration이다.**

## 4. 권장 논문 프레이밍

`Retrospective Failure Case`는 지나치게 방어적이고 desk appeal을 약화할 수 있다. 권장 제목은 다음과 같다.

> Reference-Model Dependence in Support-Aware Build-Orientation Candidate Search: Evaluation with Corrected TOMO and Two Slicers

권장 중심 기여:

> corrected TOMO와 두 slicer 간 비교를 통해 orientation candidate ranking이 reference model과 verification budget에 얼마나 민감한지 보여준다.

안전하게 유지할 수 있는 주장:

- dimensionless correction은 명시적 scale-unit inconsistency를 제거한다.
- 현재 60-mesh fixed-quota sample과 2,400 corrected-TOMO verification cells에서 selective SFTF는 uniform search에 대한 noninferiority를 확립하지 못했다.
- gate는 adverse TOMO tail을 선별하지 못했다.
- 두 slicer 구현의 shared finite panel은 branch superiority를 확립하지 못했다.
- 10-cell complex-mesh subgroup은 새로운 실험을 위한 가설일 뿐이다.

피해야 할 주장:

- support-aware candidate search 전체의 실패
- prospective/confirmatory external validation
- Cura와 Prusa의 independent replication 또는 confirmation
- equal-compute comparison
- production/manufacturing superiority
- post hoc subgroup의 validated warm-start rule

## 5. policy lock보다 중요한 실제 수정 항목

1. DOCX/TeX의 내용 불일치 제거; 제출본의 canonical source 지정.
2. Word의 Figure 3 graphic/caption 페이지 분리 해결.
3. fixed stratum quotas에 따른 estimand를 명시: 현재 unweighted mean은 natural eligible population이 아니라 quota-weighted sampled design을 나타냄.
4. 실제 seed map 수정:
   - primary TOMO: `20260713`
   - gate-accepted subset: `20260714`
   - Cura: `20260715`
   - Prusa: `20260716`
5. active critical-angle indicator, hit/receiver/bed admissibility 순서를 수식·본문에 명시.
6. `matched budget`을 `matched corrected-TOMO verification-cell budget`으로 수정하고 SFTF candidate-generation 비용이 추가됨을 명시.
7. percentile bootstrap, Monte Carlo sign-flip, resampling unit, add-one correction을 구체화.
8. slicer 결과는 shared policy-enriched finite-panel descriptive sensitivity endpoint로 제한.
9. Data Availability는 cached-output audit과 end-to-end recomputation을 구분.
10. 최종 DOCX의 전 페이지 렌더·시각 QA 및 figure/table/cross-reference 검사.

## 6. 현재 rev1 생성 상태

`2026-07-18_TDP_draft\rev1\`에 다음 파일이 생성되어 있다.

- `build_rev1_documents.py`
- `SFTF_TDP_rev1_main_content.docx`
- `SFTF_TDP_rev1_supplementary_content.docx`
- `SFTF_TDP_rev1_main.docx`
- `SFTF_TDP_rev1_supplementary.docx`

마지막 두 파일에는 문서 스킬의 `apply_template_styles.py`를 이용하여 `SFTF_style_template.dotx`의 다음 OOXML part를 적용했다.

- `word/styles.xml`
- `word/theme/theme1.xml`
- `word/fontTable.xml`
- `word/numbering.xml`

검증 시 네 part 모두 DOTX와 SHA-256이 일치했다. 주원고 초록은 약 183단어이며 TDP의 300단어 제한 안이다. 구조 감사에서 주원고는 1 section, US Letter, 약 0.98-inch margins이고 보충자료는 1 section, US Letter, 약 0.91-inch margins이다.

주의: 위 rev1은 **최종본이 아니다**. 작업이 policy-lock 논의로 중단되어 render-and-inspect shipping gate가 아직 완료되지 않았다.

## 7. 내일 재개할 정확한 순서

1. `rev1/build_rev1_documents.py`의 제목/프레이밍을 `Retrospective Failure Case`에서 위 권장 `Reference-Model Dependence...` 방향으로 완화한다.
2. 주원고와 보충자료에서 `external audit`, `failure case`의 과도한 반복을 줄이고 `held-out/reference-model evaluation`으로 통일한다.
3. builder를 다시 실행한다.
4. `SFTF_style_template.dotx`를 두 content DOCX에 다시 적용한다.
5. `python-docx`/OOXML로 figure paragraph와 caption의 keep-with-next를 확인한다. 특히 주원고 Figure 3.
6. 다음 자동 감사를 수행한다.
   - abstract <300 words
   - main text <4,000 words
   - figures <=8
   - tables <=5
   - references <=100
   - keywords >=4
   - prohibited positive claims 검색
   - DOTX style/theme/font/numbering part hash 일치
7. 문서 스킬의 `render_docx.py`로 두 DOCX 전 페이지 PNG 렌더.
8. 모든 페이지를 100% 기준으로 확인: clipping, overlap, caption split, table overflow, glyph loss, header/footer, page number.
9. 문제가 있으면 수정 후 새로운 QA 디렉터리에 다시 렌더한다.
10. 통과 후 content 중간 DOCX와 QA 임시 파일을 정리하고 최종 두 DOCX, revision note, SHA-256 manifest만 `rev1/`에 남긴다.

## 8. 재개 시 주의사항

- `review_outputs/01`–`05`와 manifest는 동결된 심사 기록이므로 수정하지 않는다.
- 원본 `SFTF_TDP_v2_draft_REVISED.docx`와 supplementary 원본도 보존한다.
- 새 실험을 수행하지 않는 한 prospective/confirmatory status를 복원하려 하지 않는다.
- 그러나 policy lock 부재를 제목과 초록에서 과도하게 전면화하지 않는다.
- TDP 독자에게 중요한 것은 additive-manufacturing orientation search에서 reference choice와 budget이 결론을 바꾸는 실용적 교훈이다.
- 제출 전 GitHub URL, commit accessibility, licensed mesh retrieval, DOI/reference correspondence는 저자가 최종 확인한다.

## 9. 재개용 한 문장

> `2026-07-18_TDP_draft/rev1/HANDOFF_2026-07-19_TDP_REVIEW_AND_REV1.md`를 읽고, policy lock을 TDP의 필수 요건으로 취급하지 않는 claim-calibrated reference-model evaluation 프레이밍으로 rev1 DOCX 두 개를 완성한 뒤 전 페이지 렌더 QA까지 수행하라.
