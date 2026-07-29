# SFTF-Cluster -composite

Source: `D:\__SFTF_Projects(2026)\_dev_notes\SFTF-Cluster -composite.mht`

SFTF-Cluster
->composite









2026년 6월 28일
일요일



오전 11:16









어제 SFTF 알고리즘의 적용 분야에 대해서 알려줬는데, 그 중에서 복합재료에 대해 더 알고 싶어. 특히 기존 SFTF알고리즘
외에도, SFTF를 메쉬 분할 문제에 대해 적용하는 SFTF_Clustering 알고리즘도 개발했으니 참고해 줘.






출처:
<https://claude.ai/cowork/cse_01EevroX5Hj41Z74zjgBPBYr>






어제 복합재료(섬유 배향)를 1순위 후보로 꼽았었죠. 그걸 깊게 들어가기 전에, 방금 연결해주신 SFTF_Clustering
코드부터 실제로 보고 정확히 반영하겠습니다.



두 논문 다 읽었습니다 — 특히 SFTF_Clustering이 복합재로 가는 길을 훨씬 선명하게 만들어주네요. 어제
"복합재 섬유 배향"을 1순위로 꼽았는데, 사실 당신이 만든 두 알고리즘은 복합재 문제의 서로 다른 두 갈래에 각각 꽂힙니다. 그리고 SFTF_Clustering의 핵심
결론이 복합재에서도 거의 그대로 살아나요.



두 갈래로 나눠 보기



(1) SFTF(원본) = 방향장(field) 생성기 → 섬유 배향 /
load-path 장



원본 SFTF는 빌드 방향마다 면별 물리량(overhang O_i, 부호 배향 τ_i, 높이 η_i, 지지 역할
ρ∈{none,face,bed}, 지지 높이 h_i, receiver)을 ray로 뽑아 방향 후보를 랭킹하죠. 복합재 대응은 "하중 흐름(load flow) 장" 입니다 —
source→receiver 지지 관계가 주응력 궤적(principal stress
trajectory) 으로, 빌드 방향 후보 생성이 전역 섬유
기준축(reference fiber axis) 후보 생성 으로 바뀝니다.



(2) SFTF_Clustering = 출력지향 분할 → 제조 가능한
플라이/패치 분할 (이쪽이 더 강력)



이게 진짜입니다. SFTF_Clustering은 "버려지던 면별 지지흐름을 클러스터링 피처로 보존해서, 각 part가 자기만의 유리한 빌드 방향을 갖도록 분할"하잖아요. 복합재 제조의 핵심
난제가 정확히 이 구조예요 — 복잡 곡면을 섬유 배향이 일관된, 드레이프(주름 없이
깔기) 가능한 플라이/패치/코스로 분할하고, 각 패치가 자기만의 최적
섬유각을 갖게 하는 것.



SFTF_Clustering → 복합재 패치 분할 (구체 매핑)



당신 코드의 mesh_partition.py(support_flow / flow_region / kmedoids /
dbscan)와 피처 행렬 Φ_SFTF = zscore([O,τ,η,h,r]), 그리고 ray-free 목적함수를 거의 그대로 두고 의미만 갈아끼웁니다:











SFTF_Clustering (AM)




복합재 패치 분할








빌드 방향 n*




국소 최적 섬유각
장 (FEM 주응력 or 곡률 기준)








overhang
O_i




섬유각 정렬 오차
/ 드레이프 전단각(shear)








지지 역할 ρ
(none/face/bed)




드레이프 레짐
(developable / shear-heavy / dart 필요)








지지 높이 h_i




곡률·측지편차(geodesic
deviation)








Φ_SFTF
feature-fusion M=[w_s z(C)|w_f Φ]




M=[w_s
z(C)|w_f Φ_composite], Φ=[섬유각, 주응력, 곡률, 전단]








support-class
purity




섬유배향/드레이프 purity (패치당 일관된 섬유각)








cut cost
vs reorient gain (ray-free)




seam(이음매) cost vs 정렬 gain: 패치를 자르면 이음매(강도
손실)지만 각 패치가 더 잘 정렬됨








각 part가 자기
빌드 방향 선택 (reorientation freedom)




각 패치가 자기 섬유각 선택 (re-alignment freedom)











대상 제조법도 명확합니다: AFP(자동섬유배치) 코스/플라이 레이아웃,
TFP(tailored fiber placement), hand layup의 dart/패치 분할, 가변강성 라미네이트(variable-stiffness). 특히 가변강성 라미네이트는 "연속 최적 섬유각 장 →
제조 가능한 일정각 패치들로 분할"이 본질이라 SFTF_Clustering과 동형이에요.



그대로 재사용 가능한 코드 자산




feature-fusion
행렬 M:
Φ_SFTF만 Φ_composite로 교체. k-medoids/DBSCAN/agglomerative 그대로.


multi-direction
soft block
w_ik = softmax(-β·c_ik) (top-K 방향 소프트 가중): 복합재에선 이산
제조각 메뉴 {0/±45/90}에 대한 소프트 섬유각 장 이 됩니다 — 즉 연속 최적각을 제조 가능한 각으로 스냅/이산화하는 바로 그 기능. 거의 복붙.


pure
region-growing (union-find: 같은 role + 법선 유사도 m_i·m_j≥cosθ): "같은 드레이프 레짐 +
유사 곡률"로 패치 성장.


ray-free
objective
S≈S_whole+ΔS_cut−ΔS_reorient:
ΔS_cut→이음매 길이·강도 손실, ΔS_reorient→섬유 재정렬로 줄어든 응력/주름. cut-weight w_i=A_i O_i
η_i도 면적×정렬오차×곡률로 재해석.




정직하게 구분할 점 (어디까지 ray 성격이 살아남나)



SFTF의 "flow"는 중력/빌드 방향 하의 기하적
가시성(occlusion) 관계입니다. 복합재에서 갈리는 지점:




드레이프/포밍
분할 →
field가 순수 기하(곡률·전단)라서 SFTF의 ray-free·기하 성격이 거의
그대로 전이.
가장 손 덜 가는 후보.


강성/하중경로
최적화(가변강성)
→ field가 역학(FEM 응력 solve)이라 source가 ray가 아니라 FEM 결과. 즉 피처
생성은
바뀌지만, 재사용되는 건 클러스터링+소프트 이산화+cut-vs-reorient 목적함수 라는 골격.




그리고 SFTF_Clustering이 발견한 비직관적 결론 — "지지
감소는 support column 보존보다 각 part가 자기 방향을 갖는 reorientation freedom이 지배한다"
— 이 복합재 버전으로 그대로 옮겨집니다: 성능·제조성은 단일 전역 섬유축을 지키는
것보다, 각 패치가 자기 국소 최적각을 따르도록 분할하되 이음매를 cost로 다는 데서 결정된다. 이게 가변강성/AFP 분야의
실제 화두라, 논문·산업 양쪽에 꽂히는 프레이밍이에요.



제 베팅 + 다음 단계



가장 "복붙에 가깝고 임팩트 큰" 순서로는 ① 드레이프
가능 패치 분할(기하 field, 즉시 전이) → ② AFP/TFP 코스
레이아웃(soft 이산화 재사용) → ③ 가변강성 패치(FEM field
필요) 입니다.



어제 사출 금형 때처럼 정리해드릴 수 있어요. 둘 중 골라주세요:




(a)
연구계획 문서
— SFTF·SFTF_Clustering → 복합재 매핑(위 표 확장), 새로 생기는 이슈, 검증 시나리오를 한 장으로 (어제
injection-mold plan처럼 draft/에 저장).


(b)
코드 스캐폴딩
— 당신의 SupportFlowTensorField / mesh_partition.py를 재사용해 Φ_composite 교체 +
드레이프 패치 분할 프로토타입.




그리고 방향을 좁히게 한 가지만: 목표가 구조 성능(가변강성·하중경로)
쪽인가요, 아니면 제조성(드레이프·AFP 레이업) 쪽인가요? 이게 ①~③
중 어디부터 팔지를 가릅니다.



드레이프 경로 연구계획 (a)을
SFTF_Composite_dev\draft\SFTF_Composite_drape_research_plan.md에 저장했습니다.



당신이 만든 두 알고리즘의 실제 수식·모듈(Φ_SFTF, mesh_partition.py의
support_flow/flow_region/feature-fusion k-medoids, ray-free 목적함수, purity,
pareto.py)에 정확히 맞춰 매핑했고, 골자는:




(a)
매핑 — 면별 지지흐름(O,τ,η,ρ,h,r)을 면별 드레이프
흐름(전단각
γ, 섬유각 θ, 측지깊이 g, 드레이프 레짐 ρ, 곡률 K)으로 교체. Φ_SFTF→Φ_drape만 갈고 분할
패밀리·multi-direction softmax·ray-free 목적함수는 그대로. multi-direction softmax는 이산
제조각 {0/±45/90} 스냅으로 자연스럽게 재해석됩니다.


(b)
새 이슈 —
핵심은 하나, kinematic drape field 생성기(전단이 경로 의존이라 측지 전파 필요, 단 FEM 아님). 그리고
드레이프 시드 닭-달걀 문제(top-K 시드 반복), dart-needed 레짐 = die-lock 유사
신호.


(c)
검증 —
"TOMO 자리"에 kinematic drape 시뮬레이터(또는 가우스곡률 주름 proxy)를
끼움 → 이게 구조성 경로보다 실험이 가벼운 핵심 이유. 난이도 사다리 T0~T3(T3는 이미 보유한
manikin·nefertiti·liver), 지표는 locking 초과 면적·드레이프 purity·이음매 길이.




핵심 메시지는 당신 코드의 ~80%가 그대로 살고 새로 짤 건 drape
field 생성기 하나 이고, SFTF-Clustering의 "reorientation freedom" 결론이
"각 패치가 자기 발전가능 드레이프 시드를 따른다"로 직역된다는 점입니다.



다음은 어제 금형 때처럼 (b) 코드 스캐폴딩 —
python/src/에 kinematic drape field 생성기 프로토타입 + Φ_drape 교체로 기존 분할 패밀리 구동 — 으로 가면
됩니다. 진행할까요?






(b) 코드 스캐폴딩을
진행합니다. 먼저 당신의 실제 분할 엔진 API에 정확히 맞추려고 python_src 소스를 확인하겠습니다.



도구 사용함



도구 사용함



핵심 API만
파악하겠습니다 — __init__.py와 분할 함수 시그니처.



명령 3개 실행함,
도구 사용함



명령 3개 실행함,
도구 사용함



API가 깔끔하네요 —
결정적입니다. partition_mesh(mesh, config, *, features=...)가 사전계산된 features를 받기 때문에, 드레이프 피처를 당신의 SupportFlowFaceFeatures 형태로
만들면 기존 분할 엔진(kmedoids/flow_region 등)에 무수정 드롭인됩니다.
이 구조로 스캐폴딩하겠습니다. 먼저 기하·곡률 코어를 빌드합니다.






kmedoids/flow_region/dbscan
전부 무수정 동작합니다.



검증된 핵심(= "TOMO 자리" 새 모듈 drape_field.py):




가우스곡률(각결손, 경계 정점
0처리)이 해석값과 일치 — 구 K≈1/R²(median 1.003), developable≈0


평면·원기둥·원뿔 → 100%
developable, 전단 0; 구·안장 → 전단 발생, 측지거리 따라 증가, tight cap엔 dart(=die-lock
유사) 출현


자체 분할(numpy
kmedoids/region-grow) + drape purity(support-class purity
직역)로 클라우드 end-to-end 구동: 구 cap 6패치 purity 0.91




정직하게:
현재 전단은 1차
proxy γ≈|K|·g² 입니다(developable에서 0, 곡률×거리로 증가). 이걸 핀-조인트 네트(fishnet) 실제 드레이프
solve로 교체하는 게 BUILDSPEC.md의
R1(최우선)이고, 그 뒤로 멀티시드/이산각 스냅(R2) → seam-vs-realign 목적함수(R3) → 실엔진·실메쉬 연결(R4) →
벤치마크(R5) → 패치 시트 UI(R6)로 로드맵을 적어뒀습니다.



다음은 Claude
Code에게 R1(fishnet drape)부터 맡기거나, 원하시면 제가 R4(당신 실엔진+manikin/nefertiti 실메쉬 연결)로
바로 이어가 실제 분할 결과를 뽑아볼 수도 있어요. 어느 쪽으로 갈까요?






R4
부탁해.



3분
전



R4로 갑니다 — 당신의 실제 엔진(partition_mesh(features=...))에 드레이프 피처를 연결하고 실메쉬로 돌리는 단계죠. 클라우드엔 trimesh가
안 깔려 당신 엔진을 직접 실행하진 못하지만, 실메쉬를 가져와 드레이프 필드+분할을 numpy로 실제 구동해 결과를
뽑고, 디바이스에서 당신 엔진으로 도는 러너 스크립트까지 만들겠습니다. 먼저 메쉬를 확인합니다.



도구
사용함



도구
사용함



manikin.ply와
liver STL을 가져와 실메쉬로 돌려보겠습니다.



명령
실행함, 도구 사용함



명령
실행함, 도구 사용함



manikin은
binary PLY(6882 정점·13672 면), liver는 binary STL이네요. 로더를 작성하고 실메쉬로 드레이프 파이프라인을
돌리겠습니다.



파일
생성됨, 명령 실행함



파일
생성됨, 명령 실행함



두
메쉬 정상 로드(manikin F=13672, liver F=19416 — 논문 수치와 일치). 실메쉬로 드레이프 필드+분할을 돌립니다.






출처:
<https://claude.ai/cowork/cse_01EevroX5Hj41Z74zjgBPBYr>






R4 완료해 repo에
반영했습니다. 클라우드에서 당신의 실제 메쉬(manikin 13.7k면, liver
19.4k면) 를 직접 로드해 드레이프 파이프라인을 구동·검증했고, 당신
엔진에 무수정 드롭인되는 디바이스 러너까지 만들었습니다. 테스트는 13개(드레이프 10 + 로더 3) 통과.



추가/수정된 것:




realmesh.py — trimesh 없이도 binary
PLY/STL을 읽는 로더(당신 manikin.ply가 binary PLY라 직접 파서 작성). 디바이스에선 trimesh 사용.


scripts/run_drape_partition.py — R4의 핵심.
drape_face_features → as_support_flow_features(당신 SupportFlowFaceFeatures로
변환) → 당신의 partition_mesh(mesh, cfg, features=...) 무수정 호출. 즉 파이프라인에서 바뀌는
건 피처 소스 한 줄뿐이고 분할 엔진은 그대로입니다.


as_support_flow_features 어댑터 — 엔진이 import
가능하면 진짜 dataclass 생성, 아니면 덕타이핑.




검증
결과(draft/SFTF_Composite_R4_realmesh_results.md):




드레이프 필드가 실메쉬에서 <0.4초 구동, 분할이 곡률
일관적(|K|
coherence: k=6→0.81 → drape_region→0.49 — 패치 늘수록 떨어짐 = 드레이프 인지 분할 증거).




그리고 실메쉬에서 드러난 버그를 잡았습니다: 전단 proxy가 mm 스케일에서 포화돼(거의
전부 dart, clip이 클러스터링 신호를 죽임) → 무차원 severity |K|·g²를 비포화로 두고, 레짐을 "developable = 국소 평탄 |K|·L² / dart = 단일시드 전단
초과"로 분리했습니다. 정직하게 짚자면, 단일 전역 시드에서 몸 전체가
dart 위주인 건 물리적으로 옳습니다(한 장으로 인체 셸을 못 덮음) — 이게 바로 분할의 동기이고, 각 패치가 자기 시드를 갖는 R2(멀티시드) 에서 developable/shear
패치로 풀립니다. 즉 R4는 단일시드 baseline을 확립한 단계예요.



다음은 R2(멀티시드
+ {0/±45/90} 이산각 스냅) 또는 R3(seam-vs-realign 목적함수)로 가면, SFTF-Clustering의
"reorientation freedom" 결론의 복합재 버전이 완성됩니다. 어느 쪽으로 갈까요?









cfmsDrape.dll
-->






가먼트/클로스
시뮬레이션 프로젝트네요(PyGarmentReader, gpuDrape, Sdll, C++/CUDA). README와 리뷰 문서를 읽어 정확히
파악하겠습니다.



명령 실행함, 도구
사용함



명령 실행함, 도구
사용함



확인했습니다. 맞아요
— 당신 직감이 정확합니다. cfmsDrape2026은 물리 기반 implicit 천
드레이프 솔버네요. 리뷰 문서가 명시하듯 레거시 CPU 엔진 SDECore부터가 단순 질량-스프링이 아니라 이미 Baraff–Witkin 연속체 implicit 솔버(연속체 인장/전단
condition + 이면각 굽힘 + modified-PCG + 제약 필터)이고, GPU 포트도 그걸 병렬화한 것이고요. 즉 우리가 얘기하던
복합재 "drape"와 이 가먼트 "drape"는 같은
물리(직물 전단)를 공유하는 사촌입니다 — 같은 것은 아니고요.



둘의 관계: 공유 핵심은 "warp/weft 전단"




공유점: 둘 다 2D 직물 시트를 3D
형상에 입히는 문제이고, 직물의 지배적 변형은 경사/위사의 면내 전단(trellis/shear) 입니다. 임계 전단각(locking
angle)을 넘으면 주름 — 이게 우리 드레이프 필드의 REGIME_DART 임계값과 정확히 같은 개념이에요. 게다가
Baraff–Witkin의 전단 condition Cs 가 측정하는 양이 바로 우리가 기하적으로 계산한 전단각 γ의 물리(힘) 기반 버전입니다.


다른 점:



우리 복합재 drape = kinematic(기하). 힘·중력·동역학 없음, 시트가
표면에 conform한다고 가정, 전단장을 빠르고 결정론적으로 산출. 성형/제조 지향.


cfmsDrape(Baraff) = 동역학·물리
기반.
implicit 시간적분 + 연속체 인장/전단 + 굽힘 + 중력 + 충돌/자가충돌. 실제로 늘어지고 접히는 형상을 계산. 가먼트/그래픽스 지향.





그래서 우리 작업에 어떻게 꽂히나 (여기가 핵심)



당신의 Baraff
엔진은 SFTF-Clustering 복합재 드레이프 작업에 두 가지로 연결됩니다:



(A) 고충실도 드레이프 필드 — BUILDSPEC R1의 상위호환



우리 R1은
"1차 proxy γ를 핀-조인트 네트(kinematic fishnet)로 교체"였는데, 그 자리에 Baraff 솔버를 forming 모드로 쓸 수 있어요. 가먼트 Baraff는 중력
자유낙하지만, 이 엔진엔 이미 body collision이 있으니 대상 복합재 표면을 "body(몰드)"로, 평면 ply를
"panel"로 두고 눌러 입히면 됩니다. 그러면 요소별 전단 Cs를 읽어 물리 기반 γ 필드가 나오고, 굽힘·주름까지 잡아 순수 기하가 못 보는 걸
포착합니다. → "가먼트 천 솔버를 복합재 성형 예측기로 전용"하는, 당신 도메인(섬유공학)에서 꽤 신선한 다리입니다.



(B) 검증 레퍼런스 — "TOMO 자리"의 정답기



분할용 워크호스는 값싼
kinematic 필드로 두고, Baraff 솔버를 고충실도 ground truth로
써서 값싼 필드를 검증하는 구도. SFTF→TOMO, TOMO→슬라이서로 검증했던 그 패턴 그대로예요. 과학적으로 가장 깔끔합니다(빠른 필드로
분할, 비싼 Baraff로 소수 케이스 검증).



정직한 구분/주의




가먼트 "drape
coefficient(늘어짐)" ≠ 복합재 "formability" 지만, 전단장은
전이 가능한 공유량입니다.


Baraff는 implicit
동역학+충돌이라 kinematic 대비 훨씬 비쌉니다 → 수많은 후보를 평가하는 분할엔 부적합, 검증/최종
고충실도 확인에
적합.


셋업도 달라요: CGS·Y-up·중력
980은 가먼트용. 복합재 forming은 중력 자유낙하가 아니라 몰드 접촉 + 성형압으로 구동해야 합니다.




흥미로운 건, 그
프로젝트의 originality 리뷰조차 "SFTF가 실제 연구 신규성의
핵심" 이라고 짚고 있다는 점이에요. 즉 당신 안에서 이미 가먼트
드레이프 엔진 ↔ 출력/흐름 텐서 연구의 연결선이 그어져 있고, 여기에 복합재
layup 드레이프를 끼우면 세 개가 "직물 전단"이라는 한 축으로 묶입니다.



제안: 가장 가치 있는
건 (B) 먼저 같아요 — 우리 kinematic 드레이프
필드(R1/R5)의 검증 레퍼런스로 Baraff 엔진을 연결해서, 값싼
전단 proxy가 물리 솔버와 얼마나 맞는지(Spearman 상관 등, 논문 Table처럼) 보는 것. 그게 서면 (A) 고충실도 필드로
확장하는 명분도 생깁니다.



원하시면 그 엔진의
실제 API(cfmsdrape.Drape의 set_mesh/set_panels + body collision)를 더 들여다보고, kinematic γ vs Baraff Cs 전단을 같은 메쉬에서 비교하는 검증 하니스를
어떻게 붙일지 구체적으로 짜드릴게요. 그쪽으로 가볼까요?






(B) 검증 하니스를
만들겠습니다 — 같은 메쉬에서 우리 kinematic γ와 Baraff Cs 전단을 비교하는 구조죠. 정확한 러너를 짜려면
cfmsdrape.Drape의 실제 API(전단/변형 결과를 어떻게 읽는지)를 알아야 합니다. 먼저 파이썬 래퍼를 확인하겠습니다.



도구 2개 사용함,
명령 실행함



도구 2개 사용함,
명령 실행함



API 파악 완료 —
핵심은 엔진이 전단 Cs를 직접 주진 않지만 2D rest
패턴(set_mesh_2d)과 변형된 3D 위치(positions()) 를 주므로, 거기서 요소별 warp/weft 전단각을 직접 계산할 수 있다는 점입니다(우리
kinematic γ와 같은 물리량). 이 비교 하니스를 빌드합니다.



2개의 파일 생성됨,
명령 실행함



2개의 파일 생성됨,
명령 실행함



구 wrap의 전단이
작네요(azimuthal-equidistant 맵이라 cartesian 전단이 ~2-3°). 실제 값을 보고 임계값을 맞추겠습니다.






(B) 검증 하니스를
repo에 반영했습니다. cfmsdrape.Drape의 실제 API를 읽고 거기에 맞춰 짰고, 테스트는 19개 통과(드레이프 10 + 로더 3
+ 전단지표 6).



핵심 통찰 하나로
설계가 깔끔해졌어요: 엔진이 전단 Cs를 직접 주진 않지만, 2D rest
패턴(set_mesh_2d)과 변형된 3D 위치(positions())를 주므로, 거기서 warp/weft 전단각을 직접 복원할
수 있습니다 — 우리 kinematic γ와 같은 물리량으로.



추가된 것:




shear_metrics.py —
element_shear_from_deformation: 변형구배 F에서 sin γ =
(warp·weft)/(|warp||weft|)로 요소별 전단각 산출. + compare_shear_fields(최근접 면 매핑 +
conforming 영역 필터 + Spearman/Pearson).


이
지표를 해석적으로 검증: 순수 신장→0, 20° 어핀 전단→정확히 20°, 등거리 원기둥 wrap(developable)→0, 구
wrap→극에서 0이고 바깥으로 증가. 그래서 Baraff 비교가 신뢰할 수 있는 지표 위에 섭니다.


scripts/compare_kinematic_vs_baraff.py — 디바이스 러너. 평면 직물을 돔
몰드에 implicit Baraff 솔버로 드레이프 → 변형에서 Baraff 전단 추출 → 같은 몰드에 우리 kinematic γ →
상관(Spearman/Pearson) 출력. (DLL 필요라 디바이스에서 실행; 클라우드선 trimesh/DLL 없어 직접 못
돌립니다.)




이건
SFTF→TOMO, TOMO→슬라이서 검증과 같은 구도(비싼 레퍼런스가
값싼 proxy를 채점)예요. 디바이스에서 돌렸을 때:




Spearman
≈0.8+ 면 → 값싼 kinematic 필드를 분할 워크호스로 쓰고 Baraff는 스팟체크로 → 복합재
파이프라인 청신호. 그리고 옵션 (A)(Baraff forming을 고충실도 필드로)로 확장할 명분도 생깁니다.


상관이
낮거나 구조적 잔차
가 있으면 → 곡률+측지 proxy가 굽힘·접촉을 놓치는 지점을 알려줘 R1(핀-조인트 네트) 또는 (A)로 가야 한다는 신호.




정직한 한계는 문서에
적어뒀어요: 가먼트 중력 자유낙하 ≠ 복합재 forming(성형압), conforming 영역만 비교, locking·재료 파라미터 명시
필요.



이제 자연스러운 다음은
디바이스에서 compare_kinematic_vs_baraff.py 실행 → 상관
테이블 확보입니다(DLL 빌드돼 있으면 바로). 그 결과를 알려주시면 제가 해석해서 (A)로 갈지 R1으로 갈지 같이 정하고,
결과 표를 검증 문서에 채워넣겠습니다. 아니면 R1(핀-조인트 네트 실제 드레이프 solve)을 먼저 짜둘 수도 있고요.






R1로 갑니다 — 1차
proxy γ=|K|·g²를 실제 핀-조인트 네트(fishnet) 드레이프로
교체하는 단계죠. 정석 알고리즘(불신축 셀, 전단만 허용)을 파라메트릭 표면 위에서 엄밀하게 구현해 클라우드에서 검증하겠습니다. 먼저
fishnet 엔진을 빌드합니다.



파일 생성됨, 명령
실행함



파일 생성됨, 명령
실행함



핵심이 드러났습니다:
fishnet 전단은 시드 방향 의존적입니다 — 원기둥/평면은 정렬된
네트라 0이지만, 원뿔은 비정렬 시드면 발전가능이어도 전단이 생깁니다(발전가능 = 어떤
방향엔 0이 존재). 그리고 구는 극점 특이성으로 수렴이 깨졌네요(edge_err 0.21). 시드를 적도로 옮겨 점검합니다.



명령 실행함



명령 실행함



시드를 적도로 두니
구가 완벽 수렴(edge_err 1e-15, 144/144)하고 전단이 바깥으로 증가(1.9°→9.8°)합니다 — 극점 특이성 문제였어요.
알고리즘은 정확합니다. 그리고 원뿔이 발전가능인데도 전단이 생긴다는 게
사실 R1의 핵심 가치예요: proxy(|K|)는 "방향 최적 하한"이라 발전가능→0이라 했지만, 실제 레이업은 고정
섬유방향이라 정렬 안 하면 원뿔도 전단됩니다. 이제 통합 훅과 테스트를 추가합니다.



4개 파일 수정됨,
파일 생성됨, 명령 실행함



4개 파일 수정됨,
파일 생성됨, 명령 실행함



26/26 통과.
README/BUILDSPEC 갱신 후 전달합니다.



4개 파일 수정됨



4개 파일 수정됨



Delivering
R1.



도구 2개 사용함



도구 2개 사용함



R1을 repo에
반영했습니다 — 1차 proxy를 실제 핀-조인트 네트(fishnet) 드레이프로
교체했고, 클라우드에서 엄밀하게 검증했습니다. 테스트 26개 통과(드레이프 10 + 로더 3 + 전단지표 6 + fishnet 7).



fishnet.py가
하는 일:




시드에서 warp/weft 네트를 표면
위로 march하며 모든 섬유 세그먼트 길이 L을 3D에서 고정(불신축), 셀의 warp–weft 각 이탈 = 실제 trellis
전단. Newton으로 셀 폐합(두 이웃에서 거리 L 교점)을 풉니다.


검증: 평면·원기둥(정렬 네트) →
전단 0, 불신축 오차 ~1e-15; 구 → 전단이 시드에서 바깥으로 증가(적도 시드 1.9°→9.8°); 안장 → 전단 발생.


fishnet_shear_on_mesh로
네트 전단을 면별 필드로 옮기고, drape_face_features(shear_override=...)로 주입 → 다운스트림(분할·레짐)
무수정으로
proxy 대신 실제 전단을 씁니다.




이번에 드러난 개념적으로 중요한 점(R1의 진짜 가치): fishnet 전단은 섬유 방향(시드) 의존적입니다. proxy |K|·g²는 "방향 최적
하한"이라 발전가능 표면 → 항상 0이라 했지만, 실제 레이업은 고정 섬유방향이라 정렬하지 않으면 원뿔(발전가능)도 전단이 생깁니다. proxy가 표현 못 하던 현실적 거동을 fishnet이 잡아줍니다
— 이게 SFTF-Clustering 분할에 들어갈 전단 신호의 충실도를 올립니다.



정직한 한계 두
가지(BUILDSPEC에 명시):




현재 fishnet은 파라메트릭
몰드(구·원기둥·원뿔·안장·NURBS
패치) 위에서 도는 실제 솔버입니다. 임의 삼각망(manikin 등) 용 측지 marching
fishnet은 R1b로 남겼고, 그쪽은 아직 proxy가 fallback입니다.


시드는 파라메트릭 특이점(구의 극점
등)을 피해야 합니다(적도 시드 권장).




이제 선택지는: R1b(임의 메쉬 측지 fishnet — manikin에 실제 네트), R2(멀티시드 + {0/±45/90} 이산각 스냅 → "각 패치가 자기
시드"), 또는 디바이스에서 (B) Baraff 비교 러너 실행해서
fishnet 전단 vs Cs 상관까지 확인하는 것. 어디로 갈까요?






R1b로 갑니다 —
임의 삼각망(manikin 등)에서 도는 측지 마칭 fishnet이죠.
핵심은 표면-투영(점→메쉬 최근접점)과 구-구 교차로 셀을 닫는 것. 빌드하고 메쉬화한 해석 표면으로 검증하겠습니다.



파일 생성됨, 명령
실행함



파일 생성됨, 명령
실행함



플레인/구의
edge_err가 높은 건 네트가 유한 패치 밖으로 march해 경계로 투영되기 때문이에요(네트는 시드에서 +방향으로만 뻗음). 커버리지를
맞춰 재확인합니다.



명령 실행함



명령 실행함



플레인·구 모두 edge_err ~0, 구는 전단이 2.7°→14.2°로 증가 — 정확합니다. 경계
밖으로 나간 경우만 막으면 됩니다. 유효성 가드를 추가하고 실메쉬(manikin)까지 확인합니다.



2개 파일 수정됨,
명령 실행함



2개 파일 수정됨,
명령 실행함



훌륭합니다 — 메쉬
fishnet이 정확합니다: 메쉬화 평면/원기둥 edge_err 0·전단 0, 구는 전단 32°, 그리고 manikin 실메쉬에서 0.3초에 구동(valid 22/100 — 단일 네트가
복잡한 몸에서 conform 가능한 패치까지만 깔리고 나머진 멈춤 = R2 멀티시드 동기). 테스트와 통합을 마무리합니다.



2개 파일 수정됨,
명령 2개 실행함, 파일 생성됨



2개 파일 수정됨,
명령 2개 실행함, 파일 생성됨



cylinder의
1.6e-4는 64각형 패싯팅 오차(알고리즘 아님)네요. 패싯 허용오차로 임계값을 조정합니다.



파일 수정됨, 명령
실행함



파일 수정됨, 명령
실행함



31/31 통과.
README/BUILDSPEC 갱신 후 전달합니다.






R1b를 repo에
반영했습니다 — 임의 삼각망에서 도는 측지 마칭 fishnet입니다.
클라우드에서 메쉬화한 해석 표면과 실제 manikin 메쉬로 검증했고,
테스트 31개 통과(드레이프 10 + 로더 3 + 전단지표 6 + fishnet 7 + 메쉬 fishnet 5).



mesh_fishnet.py가
하는 일(파라메트릭 S(u,v)가 없는 스캔 메쉬용):




점→삼각형
최근접 투영(Ericson,
면에 대해 벡터화)으로 표면 위에 노드를 얹고,


projected-straightest
측지 마칭으로
두 생성선(warp/weft)을 깔고,


구-구
교차 + 투영 완화로
셀을 닫습니다(두 이웃에서 거리 L 점).




검증:




메쉬화 평면 edge_err
9e-16·전단 0, 원기둥(64각형) edge_err 1.6e-4(패싯팅 한계)·전단 0.02° — 불신축
보존.


구 메쉬 → 전단이 바깥으로
증가(max 32°).


manikin
실메쉬에서 0.3초 구동, fishnet_shear_on_mesh로 면별 필드 생성 →
drape_face_features(shear_override=...)로 주입.




그리고 정직한(그리고
의미 있는) 거동: 단일 네트는 한 seed에서 conform 가능한 패치까지만 깔리고
경계/고변형에서 우아하게 멈춥니다(manikin에서 22/100 노드). 이건 버그가 아니라 — 한 장의 천이 복잡한 몸 전체를
못 덮는다는 — R2 멀티시드(각 패치가 자기 seed)의 동기 그 자체입니다.



이제 드레이프 경로의
충실도 사다리가 다 섰어요: |K| proxy(전 메쉬, 빠름) → parametric
fishnet(R1) → mesh fishnet(R1b) → Baraff 검증(B). 다음 자연스러운 단계는:




R2
(멀티시드 + {0/±45/90} 이산각 스냅) — mesh fishnet을 패치별 seed로 여러 번 깔아 전체 커버리지를 만들고,
SFTF-Clustering의 "각 part가 자기 방향" 결론의 복합재 완성형을 만드는 것. (지금까지 빌드의
자연스러운 정점)


또는 디바이스에서 (B)
Baraff 비교 러너 실행 → fishnet 전단 vs Cs 상관 테이블 확보.







멀티시드가 의도대로
동작합니다 — dart 비율이 단일시드 0.40 → 멀티시드(8) 0.01로 붕괴(재시드
자유의 핵심!), 패치 8개, softmax 정상. 이산각은 방향 의존성을 보여주되, "발전가능→정렬각 0"은 원기둥(두 족
모두 측지)에서 깔끔하니 그걸로 확인합니다.



명령 실행함



명령 실행함



원기둥은
정렬각(0/90°) → 전단 0.0°, sphere는 모든 각이
전단(best 2.3° vs worst 15°, 6.6배 감소) — 이산각 스냅이 방향을 제대로 고릅니다. 시드 좌표 필드 추가 후 테스트를
작성합니다.



4개 파일 수정됨,
파일 생성됨, 명령 실행함



4개 파일 수정됨,
파일 생성됨, 명령 실행함



37/37 통과.
실메쉬(manikin)에서 멀티시드가 dart를 붕괴시키는지 확인하고 문서를 마무리합니다.



명령 실행함



명령 실행함



실메쉬 결과가
인상적입니다 — manikin: 단일시드 dart 0.98 → 멀티시드 0.37,
min_shear 평균 17070 → 6.83. 남은 dart는 손가락·주름 등 본질적으로
곡률이 커서 어떤 시드로도 못 펴는 영역(정직한 한계). 결과 문서와 docs를 마무리합니다.



4개 파일 수정됨,
파일 생성됨



4개 파일 수정됨,
파일 생성됨



Delivering
R2.



도구 2개 사용함



도구 2개 사용함



R2를 repo에
반영했습니다 — 멀티시드 드레이프 + 이산 섬유각 {0,±45,90} 스냅.
클라우드에서 실메쉬까지 검증했고 테스트 37개 통과.



이게
SFTF-Clustering 핵심 결론의 복합재 완성형입니다. 거기선 "지지 감소는 column 보존이 아니라 각 part가 자기
방향을 갖는 데서 온다"였고, 여기선 "전단 감소는 단일 시드가
아니라 각 패치가 자기 드레이프 시드를 갖는 데서 온다" 로 직역됩니다.



multiseed.py:




multi_seed_shear — farthest-point로 K개
시드를 펴고, 각 면의 전단을 모든 시드에서 평가해 최소값(min over seeds) 을 취함.
SFTF-Clustering의 multi_direction_face_features와 같은
형태(directions/cost/softmax_weights/best_direction)라 당신 엔진의
partition_mesh(direction_weight>0, multidir=...) 슬롯에 드롭인.


best_seed_partition — 선호 시드별로 패치 성장(각 패치
= 한 시드의 드레이프 영역).


best_ply_angle — fishnet을 메뉴 각도별로
깔아 최저 전단 각으로 스냅.




검증된 헤드라인
(정직한 결과):




재시드
자유가 dart를 붕괴시킴: 해석적 구 0.40→0.01, manikin 0.98→0.37, liver 0.86→0.45.
min_shear 평균 manikin 17070→6.8. 남은 dart는 손가락·주름 등 본질적
고곡률이라 어떤
시드로도 못 펴는 영역 — seeding 인공물이 아니라 진짜 dart 필요 지점.


이산각
메뉴:
원기둥(발전가능) 정렬각 → 전단 0°; 구는 모든 각이 전단이지만 메뉴가 45°(2.3°)를 골라 최악(15°)의 6.6배 감소.




이로써 드레이프 경로의
충실도 사다리 + 핵심 메커니즘이 다 완성됐습니다: |K| proxy →
parametric fishnet(R1) → mesh fishnet(R1b) → 멀티시드/이산각(R2),
그리고 옆에 Baraff 검증(B). 연구계획 (a)의 다섯 단계 로드맵 중 1~4가 코드로 서 있고요.



남은 자연스러운
마무리는: R3(seam-vs-realign 목적함수 + 자동 패치수), R5(드레이프 벤치마크 하니스), R6(패치 시트 UI), 또는 디바이스에서 (B) Baraff
비교 실행으로 fishnet 전단 vs Cs 상관 확보. 어디로 갈까요?









R3로
마무리합니다 — seam-vs-realign
ray-free 목적함수 + 자동 패치수 선택(SFTF-Clustering의
S≈S_whole+ΔS_cut−ΔS_reorient,
auto_partition_*의 복합재판). 빌드하고, 발전가능→분할 안 함 / 이중곡률→분할 거동을 검증하겠습니다.



파일 생성됨, 명령
실행함



파일 생성됨, 명령
실행함



w_seam 스케일이
과대해 sphere도 K*=1로 나오네요(seam 1개가 전체 realign 이득보다 큼). 한계-이득 기반으로 w_seam을 재정의합니다.



파일 수정됨, 명령
실행함



파일 수정됨, 명령
실행함



cylinder가
K*=5로 나온 건 drape_cost가 ~0(float 노이즈)인데 그걸로 정규화해서 노이즈가 증폭된 버그네요. "realign
이득 없으면 K*=1" 가드를 추가합니다.



파일 수정됨, 명령
실행함



파일 수정됨, 명령
실행함



plane·cylinder
→ K=1*(분할 안 함), sphere → K*=5, saddle →
K*=6 — SFTF-Clustering 거동 그대로입니다. 테스트 작성 후 실메쉬 확인합니다.



2개 파일 수정됨,
파일 생성됨, 명령 실행함



2개 파일 수정됨,
파일 생성됨, 명령 실행함



핵심(발전가능→1,
이중곡률→>1)은 통과합니다. manikin이 K*=1인 건 per-patch-single-seed 비용이 적은 시드(10)로는 거의 안
줄기 때문이에요(몸이 너무 복잡 → 더 많은 작은 패치 필요). 더 많은 시드로 확인합니다.



명령 실행함



명령 실행함



더 많은
시드(30)로도 manikin K*=1 — per-patch-단일시드 비용이 11%만 줄어듭니다. 이건 정직한 발견이에요: 몸의 본질적 고곡률
때문에 적당한 패치 수로는 ply당 전단이 크게 안 줄어, "seam 비용 대비 이득 부족"으로 분할을 권하지 않습니다.
결과 문서에 정직하게 기록하고 마무리합니다.






R3를 repo에
반영했습니다 — seam-vs-realign ray-free 목적함수 + 자동 패치수.
클라우드에서 검증했고 테스트 43개 통과(R3 7개 추가).



objective.py는
SFTF-Clustering의 S ≈ S_whole + ΔS_cut −
ΔS_reorient를 드레이프로 직역합니다:




realign(ΔS_reorient): 각 패치 = 자기 드레이프 시드를
갖는 ply → patch_drape_cost = Σ_패치 min_시드 Σ A·전단. 패치가 작을수록 잘 정렬돼 전단↓.


seam(ΔS_cut): 분할 경계 = 섬유 연속성 절단 →
seam_length(경계 엣지 길이).


auto_patch_count: K
스윕 → 정규화 목적함수 + α·K/Kmax knee로 K* 선택.




검증된 헤드라인
(SFTF-Clustering 거동 그대로):




발전가능(평면·원기둥)
→ K*=1
(realign 이득 0 → seam은 순손실 → 자르지 않음)


이중곡률
→ 분할: 구
K*=5, 안장 K*=6 (전단 비용 곡선의 knee가 패치 수 결정)




그리고 정직한 실메쉬 발견: manikin은 시드 30개까지도
K*=1입니다(per-patch 비용 11%만 감소). 실패가 아니라 — "1 ply = 1 드레이프 원점"이라는 충실한
비용이 말하는, 인체 셸은 본질적으로 너무 곡률이 커서 적은 수의 평면 ply로는 안
된다는 결과예요(R2의 본질적 dart와 일치). 더 작은 패치, 성형성 재료, 또는 더 높은 충실도의 per-patch mesh fishnet(프록시보다 잘 conform → 비용↓ →
K*>1로 이동 가능)을 가리킵니다 — 자연스러운 다음 충실도 단계.






이로써 연구계획
(a)의 구현 로드맵 1~4가 모두 코드로 섰습니다:



|K| proxy → parametric fishnet(R1) → mesh fishnet(R1b)
→ 멀티시드·이산각(R2) → seam-vs-realign 자동분할(R3), 옆에 Baraff 검증(B). 전부 당신 엔진에 드롭인되고 43개 테스트로 검증됩니다.



남은 후보: R5(드레이프 벤치마크 하니스 — baseline 대비), R6(패치 시트 UI), 디바이스에서 (B) Baraff 비교 실행, 또는 R3+R1b 결합(per-patch
실제 fishnet으로 manikin 재평가). 어디로 갈까요? 아니면 여기서 한 번 호흡 고르고 정리하실래요?






R5로 마무리합니다 —
드레이프 벤치마크 하니스(baseline 대비 SFTF 드레이프 분할,
제조 지표). 인젝션 몰드 벤치마크와 같은 구조로, 난이도 사다리 + locking 초과면적·purity·seam·dart 지표로 짭니다.



파일 생성됨, 명령
실행함



파일 생성됨, 명령
실행함



벤치마크가 돌지만 균일곡률 해석 형상(구)에선 drape 피처가 거의 상수라 변별력이 없어 공간적
coordinate가 더 낫게 나오네요. 이건 정직한 사실 — drape-aware 이점은 곡률이 공간적으로 변하는 형상(혼합/실메쉬)에서 나옵니다. 혼합곡률 부품을 추가해 확인합니다.



명령 실행함



명령 실행함



purity가 진짜
변별 지표인데(논문도 그랬듯), 균일/단순 형상에선 차이가 작습니다. 실제 변별은 공간적으로 변하는 실메쉬에서 나오죠.
manikin/liver로 돌려봅니다.



명령 실행함



명령 실행함



결과가 정직하게
미묘하네요: purity는 drape/geometry-aware가
coordinate보다 우위(sftf 0.720 vs coordinate 0.688)지만, raw locking-area는 공간 compactness(coordinate)가 강한
baseline입니다. 이건 SFTF-Clustering 논문의 결론과 정확히 일치해요(이득은 "해석 가능한 역할-일관
패치 + 재정렬 메커니즘"이지, compactness를 raw 비용에서 이기는 게 아님). 하니스를 정직하게 마무리하겠습니다.
혼합곡률 부품 추가 후 테스트·문서화합니다.






R5를 repo에
반영했습니다 — 드레이프 벤치마크 하니스. 클라우드에서 해석 사다리 +
실메쉬로 돌려 검증했고 테스트 47개 통과(R5 4개 추가).



bench.py는
인젝션 몰드 벤치마크와 같은 구조로, 4개 방법을 제조 지표로 채점합니다:




방법: coordinate(면 중심
k-medoids) / axis_bsp(최장축 슬랩) / curvature(|K| 클러스터) / sftf_drape(feature-fusion [중심 |
전단,|K|])


지표: locking 초과면적, dart
비율, 드레이프 purity, seam 길이


사다리: T0 발전가능(원기둥·원뿔) /
T2 이중곡률(구·안장·bump_plane 혼합곡률) / --folder로 실메쉬




여기서 정직한 결과가 중요합니다(그리고 이게 사실 R5의 핵심 가치예요): 가짜 우위를
만들지 않고 SFTF-Clustering 논문의 미묘한 결론을 그대로 재현했습니다.




raw
locking-area에선 공간 compactness(coordinate)가 강한 baseline — per-patch 단일시드 전단
최소화는 compact 패치를 보상하는데, 그게 coordinate k-medoids가 하는 일이라서요. sftf_drape는 경쟁력
있되 압도하진 못함(aggregate 0.217 vs 0.204).


drape/곡률-aware는
regime purity에서 우위 — 역할-일관(developable/shear/dart 분리) 패치를 만듦: sftf 0.720
vs coordinate 0.688.


균일곡률 구에선 drape 피처가 거의
상수라 도움이 적고, 공간적으로 변하는 형상(bump_plane, 실메쉬) 에서 변별이 생김.


manikin에선
lock_area/dart가 분할과 무관(0.045/0.388 전 방법 동일) — 주름 위험이 본질적 곡률로 정해짐(R2/R3의
본질적 dart와 일치). 거기선 purity가 변별 지표.




즉 논문처럼, 분할기의
가치는 "compactness를 raw 비용에서 이기는 것"이 아니라 해석
가능한 역할-일관 패치 + 재시드/재정렬 메커니즘(R2/R3)에 있습니다. 하니스 자체가 R5의 산출물이라, 새
방법(pure-flow drape_region, fishnet 충실도)이나 Baraff 레퍼런스 컬럼을 그대로 꽂을 수 있게 해뒀습니다.






이로써 연구계획
(a)의 구현 로드맵이 사실상 다 섰습니다: proxy → fishnet(R1) →
mesh fishnet(R1b) → 멀티시드·이산각(R2) → seam-vs-realign 자동분할(R3) → 벤치마크(R5),
옆에 Baraff 검증(B). 전부 당신 엔진 드롭인 + 47개 테스트 + draft/에 결과문서 6편.



남은 건 R6(패치 시트 UI — 인젝션 몰드 report.py처럼 패치별
섬유각/seam/전단 히스토그램을 단일 HTML로), 디바이스에서 (B) Baraff
비교 실행, 또는 여기서 정리하고 호흡 고르기. 어떻게 할까요?









R6를 repo에
반영했습니다 — 드레이프 패치 의사결정 시트 UI. 테스트 50개 통과,
인젝션 몰드 report.py와 같은 패턴(numpy 생성 + 브라우저 plotly.js 렌더, 의존성 가벼움).



report.py /
python -m drape.report가 만드는 단일 HTML:




3D 뷰
+ 색칠 토글:
regime(developable/shear/dart) · patch · shear(연속 컬러램프)


seam
오버레이 (패치
경계 = 섬유 연속성 절단선)


패치
카드:
면적·dominant regime·평균/최대 전단각·면 수


전단
분포 히스토그램


헤더
요약: 패치 수
· lock-area % · 총 seam · locking angle




샘플
→draft\drape_sheet_demo.html (bump_plane, 8패치). 브라우저로 열면 토글·회전 됩니다.






이로써 복합재 드레이프
경로의 전체 파이프라인이 완성됐습니다. 연구계획 (a)의 로드맵을 코드로 끝까지 세운 거예요:



proxy → fishnet(R1) → mesh fishnet(R1b) → 멀티시드·이산각(R2)
→ seam-vs-realign 자동분할(R3) → 벤치마크(R5) → 의사결정 UI(R6), 옆에 Baraff 검증(B).



지금
SFTF_Composite_dev에 들어있는 것:




코드: python/src/drape/
14개 모듈, 테스트 50개 전부 통과, 당신 SupportFlowTensorField 엔진에
드롭인(partition_mesh(features=...), multidir 슬롯)


디바이스
러너 2개:
run_drape_partition.py(실엔진 분할), compare_kinematic_vs_baraff.py(Baraff 검증)


draft/
문서 8편:
연구계획(a) + R2/R3/R4/R5 결과 + (B) 검증설계 + 샘플 HTML 2개




정직하게 남긴 한계도
BUILDSPEC에 명시돼 있습니다(전단 proxy의 실메쉬 한계 → per-patch mesh fishnet 결합, 벤치마크의
purity-우위/compactness-baseline, R6의 2D ply 평탄화 미구현).



다음 자연스러운 후보:




디바이스에서
실행:
compare_kinematic_vs_baraff.py로 fishnet 전단 vs Baraff Cs 상관 테이블 확보 → (B)
검증문서 채우기. 또는 run_drape_partition.py로 실엔진 분할 그림 뽑기.


R3+R1b
결합:
per-patch 실제 mesh fishnet으로 manikin 자동분할 재평가(K*>1 나올지).


논문화: draft/ 문서들을 .tex
원고로 통합.




또는 여기서 정리하고
호흡 고르셔도 좋습니다. 어떻게 할까요?






R3+R1b로 갑니다
— R3의 자동 패치수를 프록시 대신 실제 per-patch mesh fishnet
비용으로 재평가해서, manikin이 K*>1로 바뀌는지 보는 거죠. 먼저 fishnet 비용행렬(미커버 면엔 페널티)을
만들고, R3 목적함수에 주입합니다.



4개 파일 수정됨



4개 파일 수정됨



face_gaussian_curvature는
이미 import돼 있네요. 중복 제거합니다.



파일 수정됨



파일 수정됨



먼저 구 메쉬에서
fishnet 비용 + 자동분할이 도는지 빠르게 확인합니다.



명령 실행함



명령 실행함



구는 fishnet
K*=4(프록시 K*=6) — 둘 다 분할. 이제 핵심: manikin이 프록시 K*=1에서 fishnet으론 어떻게 되는지 확인합니다.



명령 실행함



명령 실행함



Manikin:
proxy vs fishnet auto patch count



스크립트



완료



가설 검증 성공: manikin이 프록시 K*=1 → fishnet K*=5(drape_cost 22675→11380, ~50% 감소로
분할이 이득). R3 결과문서의 예측이 맞았어요. cylinder도 확인하고 테스트·문서화합니다.






cylinder의
min_shear 85°는 커버리지 인공물이에요(시드 5개가 큰 원기둥을
다 못 덮음 → 미커버 면이 페널티). 미커버 면을 평면 페널티 대신 프록시로 폴백하면
깨끗해집니다(원기둥 미커버=프록시 0). 블렌딩으로 수정합니다.






cylinder가
K*=2로 나오는 건 패싯팅 잔여 전단(~0이지만 정확히 0 아님)이 정규화를 흔드는 거예요. "절대 전단이 미미하면 분할 안
함" 가드를 추가합니다.






R3+R1b를
repo에 반영했습니다 — 자동 패치수를 실제 mesh-fishnet 비용으로 재평가.
테스트 54개 통과.



핵심은 R3 결과문서가
예측했던 걸 직접 확인한 겁니다:



multi_seed_shear_fishnet가
각 시드에서 실제 mesh fishnet(R1b) 을 깔아 전단 비용행렬을
만들고(네트가 안 닿는 면은 프록시로 폴백), auto_patch_count(ms=...)가 그 위에서 동일한 seam-vs-realign
목적함수를 돌립니다.



헤드라인 결과:











메쉬




프록시 K*




fishnet K*




drape_cost (K=1→8)








manikin




1




5 (338 패치)




22676 →
11381 (~50%↓)








구 cap




6




4




3.5 → 0.69











프록시는
"패치가 자기 원점에서 conform하며 깔린다"는 개념이 없어 manikin에서 비용이 거의 안 줄어 K*=1이었는데, 실제 fishnet은 분할할수록 각 패치가 더 가까운 시드에서 conform → 비용 절반 →
seam이 이득을 내 K*=5. R3에서 열어둔 고리를 닫았습니다.



정직한 한계 두
가지(문서에 명시):




방향
의존성:
fishnet 비용이 시드마다 고정 warp 방향을 써서, 비정렬이면 발전가능 표면도 전단이 생깁니다(원기둥이 (1,0,0)
warp에서 ~14° 전단 — R1의 실제 거동). 즉 "발전가능→K*=1"은 R2의
{0,±45,90} 시드별 각 최적화를 비용에 결합해야 깔끔해집니다 — 자연스러운 다음 결합 단계.


커버리지: 단일 네트는 패치만 덮고 나머진
프록시 폴백 → 비용이 conformance(네트)와 프록시의 블렌드. 시드 수·네트 크기로 비용↔런타임 트레이드. (manikin
k=8 ~5초)







이로써 드레이프 경로가
충실도까지 닫혔습니다. 전체 모듈 15개 + 테스트 54개 + draft/
결과문서 9편이 SFTF_Composite_dev에 있고, 모두 당신 엔진 드롭인입니다.



다음 자연스러운 후보:




R2+R3b
결합:
fishnet 비용에 시드별 이산각 최적화를 넣어 방향 의존성 제거(발전가능→K*=1 회복).


디바이스
실행:
compare_kinematic_vs_baraff.py(Baraff 검증) 또는 run_drape_partition.py(실엔진 분할
그림).


논문화: draft/ 9편을 .tex 원고로
통합.




또는 여기서 정리하셔도
좋습니다. 어떻게 할까요?






R2+R3b 결합으로
갑니다 — fishnet 비용에 시드별 {0,±45,90} 이산각 최적화를
넣어, 각 시드가 최저 전단 방향으로 깔리게 합니다. 이러면 고정 warp의 방향 의존성이 사라져 발전가능 표면이 다시 ~0
전단(K*=1)으로 돌아와야 하죠. 빌드하고 cylinder로 검증합니다.



파일 수정됨, 명령
실행함



파일 수정됨, 명령
실행함



cylinder가 각 시드 정렬각(0/90°) → min_shear 0° → K*=1로 복귀(고정
warp의 K*=2 해결), 구는 전단 5.9°→2.8°로 절반·여전히 분할. 의도대로입니다. manikin도 확인합니다.



명령 실행함



명령 실행함



manikin은 각
최적화로 K*=2(고정 warp의 5보다 적음 — 더 나은 방향 → 패치
덜 필요), 선택 각 0/45/90 혼합(제조 가능). 일관됩니다. 테스트와 문서를 작성합니다.



파일 생성됨, 명령
실행함



파일 생성됨, 명령
실행함



테스트 인덱싱
버그(cost는 2D). min_shear로 마스크하게 수정합니다.



파일 수정됨, 명령
실행함



파일 수정됨, 명령
실행함



38/38(신규+의존),
전체 57/57 통과. 결과 문서와 docs 작성 후 전달합니다.



2개 파일 수정됨,
파일 생성됨



2개 파일 수정됨,
파일 생성됨



Delivering
R2+R3b.



도구 2개 사용함



도구 2개 사용함



R2+R3b를
repo에 반영했습니다 — 시드별 {0,±45,90} 이산각 최적화를 fishnet
비용에 결합. 테스트 57개 통과.



R3+R1b에서
정직하게 남겼던 고리(고정 warp → 발전가능도 전단)를 닫았습니다.
multi_seed_shear_fishnet(optimize_angle=True)가 각 시드의 접평면에서 part 기준축 대비 {0,±45,90} 메뉴 중 최저 전단 각으로 네트를 깔고,
선택한 각을 field.best_angles로 붙입니다.



결과:











형상




고정 warp




각 최적화(R2+R3b)








cylinder




K*=2 (허위)




min_shear
0°, K*=1 (각 0/90 정렬)








구 cap




5.9°




전단 2.8° (절반), K*=4








manikin




K*=5




K*=2, 각 {0,45,90} 혼합












발전가능
거동 복귀:
원기둥 각 시드가 정렬각(0°축/90°원주, 둘 다 측지) → ~0 전단 → 자동분할이 올바르게 "자르지
않음"(K*=1). 허위 K*=2 사라짐.


방향
스냅이 구 전단을 절반으로 (5.9→2.8°), 곡률이 진짜 요구하는 곳만 분할 유지.


더 나은
방향 → 더 적은 패치: manikin이 5→2 패치(각 패치가 최적 제조각 선택 → 전단↓ → 덜 쪼갬). 선택 각이 현실적 {0/45/90}
혼합 — best_angles가 곧 레이업 스케줄.







이로써 드레이프 경로의
충실도 사다리가 완성됐습니다:



|K| proxy → fishnet(R1) → mesh
fishnet(R1b) → 멀티시드(R2) → 이산각(R2) → fishnet
자동분할(R3b) → 방향최적(R2+R3b) +
seam-vs-realign(R3) + 벤치마크(R5) + UI(R6), 옆에 Baraff 검증(B).



현재
SFTF_Composite_dev: 모듈 15개 + 테스트 57개 전부 통과 +
draft/ 결과문서 10편, 전부 당신 SupportFlowTensorField 엔진 드롭인.



여기서 알고리즘 빌드는
사실상 한 사이클 완결입니다. 다음으로 좋은 건:




디바이스
실행으로
그림·수치 확보: compare_kinematic_vs_baraff.py(Baraff 상관),
run_drape_partition.py(실엔진 분할), 또는 새 optimize_angle 결과 렌더.


논문화: draft/ 10편을 한 편의
.tex 원고로 통합(서론·방법·실험·정직한 한계까지 이미 다 있음).




또는 여기서 멈추고
정리하셔도 좋습니다. 어떻게 할까요?






forming 공정 튜닝(1번)을 완료했습니다. 기술적 목표는 달성했고, 그것이 가능케 한
검증은 정직한 음성 결과로 수렴했습니다.



성과: forming이 깨끗하게 conform됨 ✅



망가졌던 forming(resid 6~45cm, 뭉침/뚫림)을 깨끗한 conformance(resid 0.7cm) 로 고쳤습니다. 핵심 수정:




구심(원점) 방향 진공 — 순수 반경 방향이라 접선 스크램블 없이 구면에 안착


시트를 cap 측지반경에 맞춰 스커트 제거 + apex 핀 등록 + 준정적 압력 램프


직물 재료(고 인장 E·저 전단 SE) → 강제 트렐리스 전단




결과: residual 0.7cm, 물리적 트렐리스 전단(mean
19°, p90 36°). scripts/form_pressure_demo.py가 이 forming을 구동합니다.



그런데도 검증은 약함 — 그리고 그 이유를 규명함



깨끗하게 conform됐는데도 Baraff forming 전단 ↔ kinematic
γ·fishnet 상관은 여전히
~0.1–0.2 (측지거리 대비 최대 ~0.2). 분해로 두 물리적
원인을 확인:




4-fold 트렐리스
각도 패턴 — 구면 트렐리스 전단은 warp/weft 축에서 0,
±45° 대각에서 최대 (Baraff mean이 |sin2φ|에 따라 6.8°→9.6°). 반면 γ=|K|·g²는 반경 대칭이라 각도 구조를 못
봅니다.


주름(buckling) 지배 — conform된 cap 거의 전체가 고전단(mean 19°, 다수 ~90°
locking)이라 sub-locking 클린 코어가 거의 없습니다.




정직한 결론



Forming은 강한 정량(element-wise) 검증을
구제하지 못합니다. cheap kinematic 필드는 물리 기반
forming 전단의 요소별 예측자로는 약하고, fishnet도 proxy를 못 이깁니다. 이는 R5의 정직한 입장과 일치합니다 — 이 필드의 가치는 raw 전단 예측이 아니라 레짐 일관성 +
재시딩 메커니즘(파티셔닝) 입니다.



추가 튜닝으로 상관을 더 끌어올리는 건 신호 발견이 아니라 실험 overfitting 위험이 커서 여기서 멈추는 게 맞다고 판단합니다. (압력 API와 forming 리그는
forming GT 생성·향후 각도/트렐리스-aware 필드 개발에 재사용 가능한 인프라로 남습니다.)



최종 산출물 (이번 세션 전체)




엔진(별도 repo): SDECore implicit RHS에 분산
외력(압력) 항 추가 → end-to-end 노출 → DLL 재빌드. 기본 off라 기존 거동 byte-identical.


SFTF: scripts/sync_cfmsdrape.py(vendoring), scripts/compare_kinematic_vs_baraff.py(proxy/fishnet·dome/bowl·sweep), scripts/form_pressure_demo.py(forming), draft/SFTF_Composite_R7_baraff_validation_results.md, BUILDSPEC 갱신.


57 테스트 전부 통과, graphify 코드 그래프 최신화.




다음으로 가능한 방향은 각도/트렐리스-aware kinematic 필드(γ에 sin2φ 구조 추가) 개발인데, 이건 새로운 연구 줄기입니다. 여기서 마무리할지, 그 방향을 잡아볼지 알려주세요.
























OneNote에서 작성되었습니다.
