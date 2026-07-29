# Physical AI-의복 조작 로봇의 시뮬레이션 인프라

Source: `D:\__SFTF_Projects(2026)\_dev_notes\Physical AI-의복 조작 로봇의 시뮬레이션 인프라.mht`

Physical AI-의복 조작 로봇의 시뮬레이션 인프라









2026년 7월 11일
토요일



오후 5:50










조사 완료했습니다(에이전트 106개, 약 372만 토큰). 보고서는 GarmentRobotSim_LANDSCAPE_2026-07-11.md에 저장했고, 핵심은 이렇습니다:


판정:
세 공백이 모두 문서화되어 있고, 선생님 자산과 1:1로 대응됩니다.



물리 충실도 공백 ↔ 드레이프 엔진 — 제 추측이 아니라 문헌에 명시된 불만입니다.
2024 서베이가 "로봇 시뮬레이터는 물리적 사실성을 희생하고 시각적 그럴듯함을 선호한다"고 직격했고, RA-L
2024 실증 연구는 MuJoCo/Flex/SOFA/Bullet 전부 실제 천 궤적 재현에 실패함을 보였으며,
2026년 2월 시스템 리뷰도 "더 사실적인 의복 시뮬레이터가 여전히 필요하다"고 요구합니다. 2026년 4월
최신 환경(LeHome)조차 의복은 여전히 PBD로 돌립니다.


에셋 파이프라인 공백 ↔
GarmentCode CAD — 주요 벤치마크(GarmentLab NeurIPS 2024, DexGarmentLab NeurIPS
2025)의 태스크 35개를 전수 확인했는데, 전부 정적 ClothesNet 메시를 "주어진 에셋"으로 쓸
뿐 패턴·봉제정보 조건부 태스크 생성은 어디에도 없습니다.


미분가능성 공백 ↔ JAX
전환 — DiffCloth/DiffClothAI 같은 미분가능 천 시뮬은 있지만 의복 특화 벤치마크와 결합된 적이 없습니다.



권장
경로는 예상대로 "데이터 팩토리/벤치마크"입니다. 순수 시뮬레이터 논문은 RGBench(2025)가 이미 실측
물성 기반 고충실도를 겨냥하고 있어 정면 경쟁이 됩니다. 수요 근거도 확보됐습니다 — LeHome이 시뮬 데이터 공동학습으로 실로봇 성공률을
~15%→~50%로 올렸음을 실증했습니다(소규모·자기보고라 medium 신뢰).


정직하게
말씀드릴 것 세 가지: ① 어제 여쭤보신 Isaac/GR00T 로드맵의 변형체 계획은 이번 조사에서 검증된 정보가 안
잡혔습니다 — 산업 수요 근거는 아직 미확인 상태로 보고서의 "추가 확인" 목록에 올렸습니다. ② 전략
리스크 1순위는 ETH IGL(GarmentCode 원저자)입니다 — GarmentCodeData가 이미 Warp/XPBD 시뮬
파이프라인을 갖고 있어서, 원저자들이 "패턴 생성+시뮬+로봇"으로 확장하면 가장 가까운 경쟁자가 됩니다. 이건 별도 확인이
필요합니다. ③ 논문을 쓴다면 정면으로 다뤄야 할 반론이 둘 있습니다 — 변형체 접촉의 손실 불연속 때문에 "그래디언트가 언제
유용한가"를 분석해야 하고(실무는 CMA-ES를 더 씀), fling 같은 동적 태스크에 필요한 공기역학은 Baraff-Witkin
계열 준정적 엔진의 기본기가 아니라서 커버 범위를 한정해야 합니다.


이로써
두 방향(뉴럴 서로게이트, 의복 조작 시뮬) 조사가 다 끝났습니다. 둘 다 공백은 실재하는데, 서로게이트 쪽은 "빨리 치고 나가는
단독 논문", 시뮬 인프라 쪽은 "자산이 쌓이는 중기 프로젝트" 성격입니다. 원격 PC 작업 시작하실 때 이
보고서도 git으로 가져가시면 됩니다.




출처:
<https://claude.ai/epitaxy/local_5262a6d1-e96d-4ac9-9954-c6fb3f7bbdd9>




의복 조작 로봇
시뮬레이션 인프라 연구 지형 — 포지셔닝 보고서


2026-07-11, 딥리서치(멀티에이전트 교차검증) 결과 정리. 검증: 주장 다수 3-0
통과, 2건 기각(§6), 조사 커버리지 공백은 §5에 명시. 우리 자산: 검증된 드레이프 엔진(C++/GLSL, JAX 전환 중) +
GarmentCode 네이티브 의복 CAD + GarmentCodeData_v2.


0. 한 줄 결론


우리 세 자산이 겨냥할
공백 세 개가 각각 독립적으로 문헌에 문서화되어 있다 — ① 물리 충실도(주류 환경 전부 실측 검증 없는 PBD/FEM),
② 에셋 파이프라인(전부 정적 메시 의존, 패턴·봉제 조건부 태스크 생성 전무), ③ 미분가능성(미분가능 천 시뮬은 있으나 의복 특화
벤치마크와 미결합). 권장 경로는 순수 시뮬레이터 논문이 아니라 "패턴 파라미터 → 물성 → 태스크" 조건부
커리큘럼을 내세운 데이터 팩토리/벤치마크.


1. 지형 지도


벤치마크/환경 (3층
구조)









환경




연도/학회




물리




에셋




태스크




한계








SoftGym




2020
(CoRL)




NVIDIA
Flex (PyFleX)




절차적 사각 천
등




개기/펼치기 등




2019-24
시뮬 연구의 절반 이상 점유했으나 NVIDIA 라이선스로 로봇 모델(URDF) 로드 불가 — picker 추상화 위
학습








GarmentLab




NeurIPS
2024




Isaac
Sim/PhysX5, FEM+PBD 병용




ClothesNet
11카테고리 + ShapeNet 9000+




5그룹 20태스크
(개기·세탁·패킹·걸기·드레싱)




패턴/봉제 생성기
없음, 실측 검증 없음








DexGarmentLab




NeurIPS
2025




Isaac
4.5: 대형=PBD, 소형=FEM




ClothesNet
2,500+ (8카테고리, 정적 메시)




fold/fling/hang/wear/store
15개




미분 불가,
봉제·패턴 조건 태스크 없음, 논문 스스로 "PBD·FEM 모두 실제 패브릭 재현에 한계" 인정








LeHome




2026.4
(arXiv 2604.22363)




다중 엔진:
의복=PBD, 부피체=FEM, 화염/기체=Flow




—




가정 태스크
(Fold Garment 포함)




2026년 최신
환경조차 의복은 PBD — 통합·미분가능 천 솔버 아님








ICRA 2024
Cloth Competition




IJRR 2025




(실세계)




실물 34종 의복




펼치기 679회
실로봇 시도




11팀 중 시뮬
사용 2팀뿐 — 시뮬 인프라가 실전 수준에서 불신받는 방증









미분가능 천 시뮬
(의복 벤치마크와 미결합)









시스템




출처




내용




의복 벤치마크?








DiffCloth




ACM TOG
2022 (MIT)




Projective
Dynamics + 건마찰 접촉, 빠른 그래디언트. 시스템 식별·드레싱 궤적 최적화(시뮬 내)·real-to-sim 물성 식별에 실사용




✗








DiffClothAI




IROS 2023
(NUS)




PD+IPC(비관통), 천↔관절
강체 미분가능 양방향 커플링 — 천 상태→로봇 제어로 그래디언트 역전파. SoftMAC·TieBot이 채택




✗








DaXBench




ICLR 2023




미분가능 물리
벤치마크 — 천은 로프/액체와 함께 3분의 1일 뿐




✗ (범용)









2. 문서화된 공백 3개 (우리 자산과 1:1 대응)


물리
충실도 ← 드레이프 엔진


Longhini
et al. 2024 서베이: "로봇 시뮬레이터는 물리적 사실성을 희생하고 빠르고 시각적으로 그럴듯한 거동을 선호한다" —
직조 구조·실 밀도·습도 미모델링, yarn-level 시뮬은 로보틱스 파이프라인에 미통합 (2026-07 기준 여전히 유효 확인).


Blanco-Mulero
et al. RA-L 2024: MuJoCo/Flex/SOFA/Bullet 모두 실제 천 궤적 재현 실패를 실증.


2026.2
Frontiers 시스템 리뷰(41편): "더 사실적·포괄적인 의복 시뮬레이터가 여전히 필요" 명시.


에셋/태스크
파이프라인 ← GarmentCode 네이티브 CAD


주요
환경 전부 정적 ClothesNet 메시에 의존. 패턴·봉제정보 조건부 태스크 생성(파라메트릭 의복 커리큘럼)은 조사된 어떤
환경에도 없음 (GarmentLab 20태스크·DexGarmentLab 15태스크 전수 확인).


미분가능성 ←
JAX 전환


"미분가능
+ 의복 특화 대규모 벤치마크" 조합은 공백 (§1 표).


수요 근거: LeHome 실증 — sim+real 공동학습이 실로봇 성공률
~15%→~50% (단 3태스크·자기보고, medium 신뢰). 데이터 팩토리 가치 제안을 직접 뒷받침.


3. 포지셔닝 판정: 세 경로 비교


순수
시뮬레이터 논문: ✗ 비추천 — RGBench(arXiv 2511.06434, 2025)가 이미 실측 패브릭 파라미터 기반 고충실도 시뮬을
겨냥 중(직접 검증은 안 됐으나 반드시 인용·차별화 필요). 정면 경쟁 + 검증 부담 최대.


벤치마크
논문: △ — GarmentLab/DexGarmentLab(NeurIPS 2연속)과 태스크 구성으로 경쟁해야 함. 로봇 통합(우리 약점)이
심사 기준.


데이터
팩토리/벤치마크 하이브리드: ✓ 추천 — "GarmentCode 패턴 파라미터로 의복·물성·태스크를 조건부
생성하고, 검증된 드레이프 물리로 시뮬하며, JAX로 미분가능한" 3중 조합. 어떤 단일 경쟁자도 셋을 다 갖지 못했고, 각 공백이
제3자 문헌으로 문서화되어 있어 신규성 서사가 안전.


4. 논문에서 정면으로 다뤄야 할 반론 (검증됨)


"그래디언트가
언제 유용한가": 변형체 접촉의 손실 불연속 때문에 그래디언트 기반 시스템 식별이 자주 실패하고, 실무는 BO/CMA-ES 등
gradient-free를 흔히 씀 (Longhini 서베이 + DiffCloth 자체 문서화). JAX 미분가능성을 팔려면 이 함정 분석을
기여로 포함할 것.


공기역학:
Frontiers 리뷰가 동적 조작(fling)에 공기-천 상호작용을 이상적 요건으로 명시. Baraff-Witkin 계열 준정적 드레이프의
기본 강점이 아니므로, 동적 태스크 커버 범위를 명확히 한정하거나 보강 계획을 서술할 것.


5. 미조사/추가 확인 필요 (이번 조사에서 검증 클레임 없음)


미완료GarmentCodeData의
자체 Warp/XPBD 시뮬 파이프라인 — 우리 포지셔닝의 최근접 경쟁/보완 지점. ETH IGL(원저자)이 "패턴
생성+시뮬+로봇"으로 확장 중인지 확인 필수 (전략 리스크 1순위).


미완료RGBench의
검증 방법·태스크 범위, 우리 엔진 검증 수준과의 차별점.


미완료NVIDIA
Isaac Lab/GR00T 로드맵의 변형체 고도화 계획 — 미검증. 휴머노이드 데모(Figure, 1X 등)의 시뮬 사용 여부도
미확인. 산업 수요 근거는 아직 없음.


미완료에셋
비교(CLOTH3D, DeepFashion3D), 기반 엔진 직접 비교(MuJoCo deformable, Genesis, Style3D),
봉제 자동화 시뮬 수요 — 커버리지 공백.


미완료충실도↑
→ 전이 성능↑의 정량 실증 (Blanco-Mulero 이후) — 데이터 팩토리 논문의 핵심 전제.


6. 인용 금지 (검증에서 기각된 주장)


"DexGarmentLab이
PBD의 비현실적 sagging을 명시적으로 시인했다" (0-3 기각 — 한계 인정은 일반적 수준의 문장).


"ICRA
대회 실전 성능이 FlingBot(0.8)·UnFoldIR(0.85) 등 시뮬 훈련 선행 수치보다 크게 낮았다" (1-2 기각 —
직접 비교 불가).


7. 핵심 소스



GarmentLab: https://arxiv.org/abs/2411.01200 · https://garmentlab.github.io


DexGarmentLab: 
https://arxiv.org/html/2505.11032v3


LeHome: https://arxiv.org/pdf/2604.22363


SoftGym: https://arxiv.org/abs/2011.07215


2026 Frontiers 시스템
리뷰: https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1752914/full


Longhini et al.
2024 서베이: https://arxiv.org/pdf/2407.01361


Blanco-Mulero et
al. RA-L 2024: https://arxiv.org/abs/2310.09543


DiffCloth: https://arxiv.org/abs/2106.05306


DiffClothAI: https://ieeexplore.ieee.org/document/10341573


DaXBench: https://arxiv.org/abs/2210.13066


ICRA 2024 Cloth
Competition: https://arxiv.org/html/2508.16749v1


RGBench (미검증, 차별화
대상): arXiv 2511.06434





출처:
<https://claude.ai/epitaxy/local_5262a6d1-e96d-4ac9-9954-c6fb3f7bbdd9>



















OneNote에서 작성되었습니다.
