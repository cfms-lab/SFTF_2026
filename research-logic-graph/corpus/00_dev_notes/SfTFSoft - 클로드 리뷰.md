# SfTFSoft - 클로드 리뷰

Source: `D:\__SFTF_Projects(2026)\_dev_notes\SfTFSoft - 클로드 리뷰.mht`

SfTFSoft - 클로드 리뷰









2026년 7월 1일
수요일



오후 2:20









결론부터



주제 적합성은 매우 좋고, 핵심 기여(하드 ray-cast → soft attention
미분가능화 + 실제 프로덕션
슬라이서(Cura 15.04/DP103)로의 검증)는 PiAM에 실을
수 있는 급입니다. 다만 현재 원고
그대로면 "borderline / major revision" 위험이 있습니다. 게재 불가 수준은 아니지만, 리뷰어가 확실히 물고 늘어질 약점이 몇 개 뚜렷합니다. 아래를 손보면 자신 있게 낼
수 있습니다.



강점 (PiAM 기준에서 실제로 통하는 것)




검증이 프록시가 아니라 실물 툴체인: TomoNV(voxel
estimator)에 머물지 않고 실제 Cura support-only mass와 대조, 8 mesh 전부 양의 상관 +0.83
(95% CI [+.77,+.89]), TomoNV +0.26 대비 명확히 우위. AM 저널이 좋아하는 "예측이 실제
재료량을 맞추나?"에 정면으로 답함.


수치적 엄밀성: FD gradient 일치 3×10⁻¹⁰, ablation,
end-to-end percentile, 런타임/스케일 부록까지 — 재현 가능하고 정직하게 서술됨.


한계를 스스로 명시(rank vs absolute, mesh 해상도가 speed가
아니라 fidelity 변수, degenerate optima) — 성숙한 서술.




리뷰어가 반드시 지적할 약점




자기
선행연구(SFTF)와의 차별성 = salami 위험. 같은
저널에 SFTF 원논문을 이미 냈다면, 에디터가 "이건 그 논문의 미분가능 버전 + Cura 검증일 뿐 아닌가"를
먼저 물을 것. Introduction에서 "미분가능화가
여는 것(vertex-gradient shape opt, label-free physics loss)"을 선행논문이 절대 못
하던 신규 능력으로 더 강하게 프레이밍해야 함.


$S_g$ 게이트가 슬라이서의 60° 규칙 자체를 내장 → "정답을 넣고 정답을 맞혔다"는 비판. 실제로 gate가
TomoNV 상관은 낮추고 Cura 상관만 올리는 표(본문에 있음)가 이 비판을 오히려 부추길 수 있음. **기여는 게이트가 아니라
"미분가능 구조 안에서 슬라이서 규칙을 원칙적으로·전이가능하게 넣는 방식"**임을 명시적으로 방어할 것.


End-to-end 이득이 작음: percentile 0.286 →
0.273. 헤드라인 응용(더 나은 방향 선택)에서 1.3 퍼센타일
개선은 리뷰어가 "실용적 의미?"라고 칠 지점. 통계적 유의성/여러 seed/베이스라인(random,
TomoNV-driven) 대비를 붙이거나, 이 결과의 프레이밍을 "상관"이 아니라 "저-support
basin으로의 유도"로 낮춰 잡아야 함.


검증 폭이 좁음: 슬라이서 1종(legacy Cura 15.04)·재료 1종(PLA/DP103)·프로파일 1개.
AM 풀페이퍼로는 얇게 보임. 최소한 다른 support angle/밀도 한두 설정, 또는 다른 재료 1종이라도 추가하면 방어력이
크게 오름.


문헌 근거가 얇다: 참고문헌 9개(그중 2개는 자기 생태계
sftf_engine/tomonv). SCI 풀페이퍼는 보통
25~40. Related Work가 각 주제당 1편씩만 인용 — build-orientation optimization,
self-supporting design, differentiable slicing/rendering 각각을 더 촘촘히 깔아야
"분야를 안다"는 신호가 됨. 이건 게재 확률에
비해 고치기 가장 쉬운 약점이니 우선순위 최상.


분량: 본문
~2100단어(pandoc 총 ~2900). 풀 research article로는 짧아 short communication처럼 읽힘.
PiAM에 short communication 트랙이 없으면, 위 2·4·5를 채우며 자연스럽게 풀페이퍼 분량으로 키우는 게 맞음.




추천 (우선순위 순)




참고문헌 25편+로 보강, Related Work 2문단 확장 — 리스크 대비 노력 최소, 효과 큼.


검증에
슬라이서 설정/재료 1축이라도 추가 → "single-profile" 비판 차단.


Introduction/Contribution에서 미분가능화 고유 가치(vertex-grad, learning physics term)를
선행 SFTF 대비 신규 능력으로 재프레이밍 → salami·novelty 방어.


End-to-end
실험에 seed 여러 개 + 유의성, 프레이밍 톤다운.




이 4개를 처리하면 PiAM 재출(again) 대상으로 "낼 만하다"에서
"낼 만하고 통과 기대할 만하다"로 올라갑니다. 지금 그대로 내면 아마 major revision을 받고 위 항목들을 어차피
요구받을 것입니다 — 선제적으로 채워서
내는 걸 권합니다.



원하시면 (1) 참고문헌 보강 후보를 semantic-scholar로 실제로 찾아
references.bib에 추가하고 Related Work를
확장하거나, (2) Introduction 재프레이밍 초안을 한/영 lockstep으로 써드리겠습니다. 어느 쪽부터 할까요?


















OneNote에서 작성되었습니다.
