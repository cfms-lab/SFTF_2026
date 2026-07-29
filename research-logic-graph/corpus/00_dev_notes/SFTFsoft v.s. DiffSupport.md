# SFTFsoft v.s. DiffSupport

Source: `D:\__SFTF_Projects(2026)\_dev_notes\SFTFsoft v.s. DiffSupport.mht`

SFTFsoft
v.s. DiffSupport









2026년 7월 14일
화요일



오후 8:19









기다리는 동안, 이
프로젝트의 결과가 대충 'D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev'보다 좀 나아졋나? 어때?






원본을 (README + JAX 패리티 문서 + r1‑r2 결과 로그) 훑어봤습니다.
솔직하게, 균형 잡힌 답을 드리면:



두 프로젝트는 성격이 달라서 "그냥 더
낫다"고 말하기 어렵습니다



원본 Tomo_SFTFSoft_dev = 성숙한 전체 연구 프로젝트입니다. 이미 헤드라인 결과를
가지고 있어요:




미분가능
support 프록시가 실제 Cura 슬라이서 support mass와 상관 —
21메시 × 48방향, θc=60에서 Spearman 평균 +0.670.74
(pipe_elbow는 +0.970.99!).


torch↔JAX
수치 패리티(~1e‑12), 게이트 모드(hard/sig/smootherstep/ste_smooth/patch),
GNN·대형메쉬·GPU·논문 초안·특허까지.




이 새 프로젝트 Tomo_DiffSupport_dev = 그중 핵심(미분가능 first‑hit
support‑volume 렌더러 + 후보 인덱스)만 백지에서 엄격하게 다시 짓는 좁고 깊은 재구현입니다. 아직 T1(인덱스/렌더러 feasibility + 미분 패리티) 단계이고, T2(실제 슬라이서 결과 비교)는
설계상 봉인돼 있습니다.



그래서 "결과"로 보면 — 아직 원본이
앞섭니다



새 프로젝트는 원본의 헤드라인(실제 슬라이서와의 상관)을 아직 재현하지 못했습니다. 일부러 T2를 봉인해 뒀기 때문에, "원본보다 결과가 낫다"는 아직 말할 수 없습니다. 진짜 head‑to‑head 비교는 T2에 도달해야 가능합니다.



"토대/방법론"으로 보면 — 새 프로젝트가
확실히 낫습니다



여기가 핵심입니다. 원본 문서(JAX_PARITY_RECHECK.md)가 스스로 인정한 약점이 있어요:



"이전 판의 '재검증 ✅ 완료'는 근거
부족이었음 — 참조 dump가 재생성되지 않았고, JAX 포트에 신규 게이트 기능이 아예 없었음."



새 프로젝트는 정확히 그 약점을 겨냥해 만들어졌습니다 — 해시 잠금 프로토콜,
exact‑rebuild 검증, 등록 게이트, exhaustive midpoint 감사(false‑negative 0 강제), 무음
fallback 금지, 검증된 미분 패리티. 제가 이번에 쌓은 r2도 그 위에서 후보 작업량 절반 + feasibility 유지 + 값/그래디언트/IR 패리티 증명된 견고한 블록입니다. "재검증 근거 부족" 같은 일이 구조적으로 못
일어나게 되어 있습니다.



한 줄 요약




결과(validated findings): 아직 원본이 앞섬 (실제 슬라이서
상관·GNN·논문까지 있음).


토대(정확성·재현성·provenance): 새 프로젝트가 확실히 개선 — 그리고
원본이 자인한 약점을 겨냥.


지금 새
프로젝트는 "결과가 더 좋다"가 아니라 "훨씬
단단한 기반 위에서 같은 알고리즘을 올바르게 다시 세우는 중" 이라고 보는 게 정확합니다.




신뢰도 단서: 원본은
README·JAX 패리티 문서·r1‑r2 결과 로그만 읽은 인상이라 정밀 감사는 아닙니다. 원하시면 원본 diff_sftf.py 코어와 새 프로젝트의 대응
모듈을 나란히 놓고 더 구체적으로 비교해 드릴 수 있습니다.



참고로 백그라운드 512조건 등록 실행은 계속 돌고 있고, 완료되면 결과를 보고하겠습니다.





















OneNote에서 작성되었습니다.
