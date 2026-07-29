# RPJ revision handoff: generative-AI disclosure and compliance check (2026-07-24)

`Tomo_SFTF_dev`의 SFTF 논문은 현재 **Rapid Prototyping Journal
(RPJ, Emerald Publishing)**에 제출된 상태다. Revision letter가 도착하거나
편집부가 AI 사용을 문의할 때, 현재 선언문을 RPJ의 최신 정책에 맞추어
재검토·수정하기 위한 핸드오프다.

## 1. 현재 제출 원고의 선언문

현재 원고에는 다음 문구가 들어 있다.

> **Use of artificial intelligence tools**  
> AI coding assistants, including OpenAI Codex and Anthropic Claude Code, were
> used to assist with portions of research-code implementation,
> figure-generation scripts, and manuscript-support automation. All generated
> code, experimental results, and manuscript changes were reviewed and
> validated by the author.

이 문구가 사실관계를 완전히 반영하는지는 revision 전에 반드시 다시
확인한다. 특히 `manuscript-support automation`이 단순 형식화·교정인지,
번역·초안 작성·새 문단 생성까지 포함하는지 구분해야 한다.

## 2. RPJ/Emerald 공식 정책

2026-07-24 확인 기준:

- 생성형 AI로 제출 원고의 새 내용을 작성·초안화·생성하는
  **copywriting은 허용되지 않는다**.
- 저자가 이미 작성한 원문을 대상으로 문법, 가독성, 형식, 언어의 명료성을
  개선하는 **copy-editing은 허용된다**.
- AI 도구 사용자는 결과의 정확성·무결성에 전적인 책임을 지며, AI는 인간의
  저작과 판단을 대체해서는 안 된다.
- AI 사용은 투명하게 밝혀야 한다. 사용 도구의 명칭과 버전, 생성 또는 수정된
  내용을 Methods와 Acknowledgements 또는 그 밖의 적절한 절에 구체적으로
  기록해야 한다.
- AI가 만든 합성 이미지와, 검증된 코드가 실제 실험 데이터로부터 결정론적으로
  생성한 그래프·도표는 구분해야 한다. 이 논문의 그림이 후자라면 그 점을
  명시한다.
- 미고지 또는 부정확한 고지는 심사 중 거절이나 출판 후 조치로 이어질 수
  있으며, 최종 허용 여부는 편집자와 출판사가 판단한다.

공식 출처:

- RPJ Author Guidelines:
  <https://www.emeraldgrouppublishing.com/journal/rpj>
- Emerald Research and Publishing Ethics — Artificial Intelligence:
  <https://emeraldgrouppublishing.com/publish-with-us/ethics-integrity/research-publishing-ethics>
- Emerald statement on AI tools:
  <https://emeraldgrouppublishing.com/news-and-press-releases/emerald-publishings-stance-ai-tools-content-creation-and-peer-review>

정책은 revision 시점에 다시 확인한다. 이 문서는 2026-07-24의 정책
스냅샷이며, 이후 변경될 수 있다.

## 3. 현재 문구의 문제점

1. `including`은 사용한 도구 목록이 불완전할 수 있다는 인상을 준다. 실제
   사용 도구를 빠짐없이 열거하는 편이 낫다.
2. 도구의 정확한 모델명·버전 또는 확인 가능한 사용 시점이 없다.
3. `manuscript-support automation`은 AI가 원고 본문을 새로 작성했는지
   단순 교정했는지 판별할 수 없는 모호한 표현이다.
4. `generated code, experimental results`는 실험 결과 자체가 AI에 의해
   생성된 것처럼 읽힐 수 있다. 결과는 검증된 코드를 실행해 얻었으며 AI가
   데이터를 만들거나 조작하지 않았다는 식으로 분리해야 한다.
5. AI가 과학적 주장, 결과 해석, 참고문헌, 합성 이미지에 관여했는지가
   명시되지 않는다.
6. 사람의 검토·검증을 선언하는 것만으로 금지된 AI copywriting이 허용되는
   것은 아니다. 실제 사용 방식이 정책에 맞아야 한다.

## 4. Revision letter 도착 시 먼저 할 사실관계 감사

다음 항목을 파일·커밋·대화 기록을 근거로 구분한다. 사실을 확인하기 전에
허용되는 문구를 원고에 기계적으로 복사하지 않는다.

- [ ] 연구 아이디어와 가설은 저자가 수립했는가?
- [ ] 실험 설계와 평가 지표는 저자가 결정했는가?
- [ ] Codex/Claude가 작성 또는 수정한 코드 범위는 무엇인가?
- [ ] 모든 AI 보조 코드는 테스트·수치 대조 또는 수동 검토를 거쳤는가?
- [ ] figure-generation scripts는 실제 실험 데이터를 결정론적으로 시각화할
  뿐이며 생성형 이미지 모델을 사용하지 않았는가?
- [ ] 원고 본문은 저자가 먼저 작성했고 AI는 문법·가독성·형식만
  copy-editing했는가?
- [ ] AI가 초록·서론·논의·결론의 새 문장 또는 문단을 작성했는가?
- [ ] 한국어 원고의 영문 번역에 생성형 AI가 사용됐는가?
- [ ] AI가 주장, 결과 해석, 참고문헌 선택·생성에 관여했는가?
- [ ] 사용한 제품, 모델/버전, 사용 시기와 대상 절을 가능한 한 정확히
  복원했는가?
- [ ] 원고의 AI 선언과 투고 시스템의 AI 관련 답변이 일치하는가?

## 5. 사실관계별 대응

### A. 코드·도표 스크립트만 AI 보조를 받은 경우

원고 본문이 저자 작성이고 생성형 AI가 본문을 수정하지 않았다면,
`manuscript-support automation`과 `manuscript changes`를 삭제한다.
AI 보조 코드의 범위, 검증 방법, 실제 데이터 기반 결정론적 도표임을
명시한다.

### B. 저자 원고의 문법·표현만 copy-editing한 경우

아래 권장 선언문을 사실에 맞게 수정한다. `solely to copy-edit`는 실제로
새 과학적 내용이 생성되지 않았을 때만 사용한다. 사용 도구와 버전을 정확히
기록하고, revision cover letter와 투고 시스템에도 같은 내용을 반영한다.

### C. AI가 새 문단을 작성하거나 영문 번역을 수행한 경우

이를 단순 copy-editing으로 축소해 표현하지 않는다. Emerald 정책상
금지된 copywriting으로 판단될 가능성이 있으므로, revision을 제출하기 전에
편집부에 정확한 사용 범위를 알리고 다음 중 허용되는 조치를 문의한다.

1. 저자가 해당 부분을 독립적으로 다시 작성한 교체 원고 제출;
2. 상세 AI-use declaration을 포함한 수정 원고 제출;
3. 편집부가 요구할 경우 철회 후 정책을 충족하는 원고로 재투고.

선언문을 추가하는 것만으로 금지된 사용이 자동으로 치유된다고 가정하지 않는다.

## 6. 권장 선언문

다음 문구는 **코드·결정론적 도표 스크립트 보조와 저자 원문의
copy-editing만 있었던 것이 사실로 확인됐을 때** 사용하는 초안이다.
대괄호는 확인한 실제 정보로 교체한다.

> **Use of artificial intelligence tools**  
> OpenAI Codex ([exact model/version, if available]) and Anthropic Claude Code
> ([exact model/version, if available]) were used to assist with portions of
> the research-code implementation and with deterministic scripts used to
> generate figures from author-produced experimental data. They were also used
> solely to copy-edit and format author-written manuscript text for clarity
> and language consistency. The tools were not used to draft new scientific
> content, formulate claims, generate or interpret experimental results,
> create synthetic images, or select references. The author reviewed and
> tested all AI-assisted code, independently verified all reported results,
> figures, citations, and manuscript edits, and assumes full responsibility
> for the work.

원고 본문에 AI copy-editing이 전혀 없었다면 다음 두 문장을 삭제한다.

> They were also used solely to copy-edit and format author-written manuscript
> text for clarity and language consistency.  
> ... manuscript edits ...

저자가 여러 명이면 `the author`와 `assumes`를 각각 `the authors`와
`assume`으로 변경한다.

정확한 모델/버전을 복원할 수 없다면 임의로 만들지 않는다. 확인 가능한
제품명, 인터페이스, 사용 기간을 적고 버전 확인이 불가능함을 사실대로
편집부에 알린다.

## 7. 편집부 문의문 초안

이미 제출된 선언을 정정하거나 허용 범위를 확인해야 할 때 사용한다.

> **Subject: Clarification of generative-AI use for manuscript [ID]**  
> Dear Editorial Office,  
> We would like to clarify the use of generative-AI tools during the
> preparation of manuscript [ID and title]. The research design, experiments,
> analysis, conclusions, figures, and references were produced and verified
> by the author(s). [Tool and model/version] was used for [precise purpose,
> affected files/sections, and whether the use was code assistance,
> deterministic figure scripting, or copy-editing of author-written text].
> It was not used for [state only what is factually true]. We take full
> responsibility for the submitted work and have independently verified all
> affected material. Could you please advise whether you require a revised
> manuscript and submission-system declaration, and whether the described use
> complies with the journal policy?  
> Sincerely,  
> [Corresponding author]

AI가 새 문단 또는 번역문을 작성했다면 위 문의문에 그 사실과 affected
sections를 명확히 적고, 저자 독립 재작성본으로 교체할 수 있는지 질문한다.

## 8. Revision 완료 조건

- [ ] revision 시점의 RPJ/Emerald 정책을 공식 페이지에서 다시 확인했다.
- [ ] AI 사용 범위를 기록에 따라 재구성했다.
- [ ] 허용되는 copy-editing과 금지 가능성이 있는 copywriting을 구분했다.
- [ ] 선언문의 도구·버전·대상·검증 방법이 구체적이고 사실과 일치한다.
- [ ] 생성형 이미지가 아니라 실제 데이터의 결정론적 시각화임을 확인했다.
- [ ] 원고, cover/rebuttal letter, 투고 시스템의 AI 답변이 서로 일치한다.
- [ ] 필요한 경우 편집부에 선제적으로 문의하고 답변을 보존했다.
- [ ] 최종 revision에서 코드, 수치, 그림, 인용을 저자가 다시 검증했다.

## 9. 다음 세션 시작점

Revision letter가 도착하면 먼저 이 문서를 읽고, 제출된 원고와 투고 시스템의
AI 선언을 확보한다. 그 뒤 AI 사용 사실관계를 감사한 후, 편집부 답변과
정합되는 선언문·cover/rebuttal 문구를 작성한다. 사실관계 감사 전에는
`solely to copy-edit` 같은 허용 문구를 확정하지 않는다.
