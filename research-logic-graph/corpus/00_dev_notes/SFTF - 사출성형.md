# SFTF - 사출성형

Source: `D:\__SFTF_Projects(2026)\_dev_notes\SFTF - 사출성형.mht`

SFTF - 사출성형









2026년 6월 27일
토요일



오후 8:28










논문 잘 읽었어요.
이제 SFTF의 정체가 명확해졌네요. 앞서 제가 추측했던 "응력장 추종"이 아니라, 핵심은 방향 의존 비대칭 flow tensor + ground-node 통합 + 값싼
warm-start 후 국소 검증(AVE) 이 세 가지 재사용 가능한 엔진이에요. 이걸 기준으로 다시 짚어드릴게요.


SFTF를 "탈AM"으로 추상화하면


논문에서 진짜 옮겨갈
수 있는 건 "서포트 배향"이라는 응용이 아니라 이 알고리즘 골격입니다:



비대칭
flow tensor: 표면 요소(source)에서 ray를 쏘아 누가 누구를 "받아주는가(receiver)"를 비대칭
텐서로 인코딩 → 방향 의존 가시성/차폐 관계가 있는 모든 문제에 일반화됨


Ground-node
Rayleigh 통합: 특수 경계(빌드 플레이트)를 가상 receiver로 흡수해 스칼라 패치를 텐서 수축항으로 통일 → 바닥/평면/무한원/환경 같은 특수 수용체가 있는 문제에
대응


Warm-start
+ AVE:
비싼 검증기(TOMO/슬라이서) 대신 값싼 랭킹으로 후보 basin만 골라 국소 검증, 어려운 케이스만 자동 확대 → 저차원(특히
S² 구면) 위의 비싼 블랙박스 목적함수면 무엇이든



즉 적용 대상의 공통
조건은: (저차원 방향/배향 공간) × (표면 요소 간 방향 의존 상호작용) ×
(평가 비용이 큰 목적함수).


전이 강도순 적용 후보


1순위 — 거의 동형(isomorphic). 사출·주조 발형(파팅) 방향 / 언더컷 최소화


이게 제 가장 강한
추천입니다. 대응이 거의 1:1이에요:









AM (SFTF)




금형 발형








overhang
face




언더컷 face
(발형 방향으로 못 빠지는 면)








build
plate (ground node)




파팅 평면








support
volume vssv_{ss} vss​




언더컷 부피 /
side-action(슬라이드·리프터) 수








build
direction 탐색




draw
direction 탐색 (S²)









언더컷 판정이 곧
ray-cast 가시성이라 overhang coefficient와 ray 캐스팅을 그대로 씁니다. 산업 수요(금형 설계 자동화)가 크고,
draft 해석이 AM 서포트보다 오히려 정의가 깔끔해서 구현 난도도 낮아요. 논문·산업
양쪽 다 임팩트가 가장 좋은 후보.


2순위 — 같은 ray-cast 가시성 커널



다축
CNC 셋업 배향 / 공구 접근성(accessibility): 셋업 횟수·언더컷 최소화. "receiver = 공구가 도달 가능한 방향"으로
바꾸면 그대로 적용.


3D
검사·스캐닝 뷰포인트 계획(next-best-view): 표면 커버리지 = 가시성. 값싼 후보 시점 생성 → 커버리지 국소 검증 → 안 보이는 포켓만
AVE로 확대. AVE 구조가 특히 잘 맞음.


복사
열전달 view factor / 태양광 패널 틸트·자기그림자: 논문의 face-to-face 영향 wijw_{ij} wij​가 사실상 view factor의
일반화예요. 패널 간 self-shadowing 차폐를 flow tensor로 인코딩 가능.



3순위 — 메타 프레임워크(warm-start 부분만 재사용)


저차원 배향/각도
위에서 FEM·CFD 같은 비싼 평가가 걸리는 문제 전반 — 받음각 사전선별, 빌드플레이트 네스팅 배향, 로봇 그래스프/픽스처 방향 등.
여기선 비대칭 텐서는 못 쓰고 "값싼 랭킹 + 적응 검증" 골격만 가져갑니다.




제 베팅은 금형 발형 방향(1순위) 이고, 그다음이 뷰포인트 계획이에요. 둘 다 SFTF의 고유
기여(비대칭 텐서 + ground node + AVE)를 거의 손대지 않고 살릴 수 있거든요.


원하시면 이 중
하나를 골라서 (a) SFTF 수식이 새 문제로 어떻게 매핑되는지 구체적 변환, (b) 필요한 수정 사항, (c) 논문화/검증 시나리오까지
한 장으로 정리해드릴게요. 어떤 걸로 파고들까요? 그리고 목표가 논문 확장인지 산업 적용인지도 알려주시면 거기에 맞춰 잡을게요.




에
도움이 되는 연구를 하고 싶어. 일단 "금형 발형 방향" 에 대해 (a) 부터 부탁해


12분
전


논문 수식을 실제로 보고 나니 매핑이 깔끔하게 떨어집니다. 핵심은 SFTF가 이미 가진 두 축 — (내부
가시성 = ray로 receiver를 찾는다) 와 (ground node = 특수 평면으로의 직접 해소) — 이
금형 발형 문제의 언더컷 판정과 파팅면으로의 직접 이형(離型) 에 거의 1:1로 대응한다는 점이에요.
논문 본문에서 "예측력의 대부분은 build-plate penalty와 internal visibility에서 나온다"고
한 그 두 항이, 금형에서 그대로 가장 중요한 항이 됩니다.


문제 재정의: 발형 방향 = S² 위의 SFTF 탐색


부품(고정 메시)을 주고, 발형 축 d ∈ S²를 고른다. 2판 금형이면 +d(캐비티
측)과 −d(코어 측) 두 반쪽으로 면이
갈리고, 언더컷 = 자기 반쪽 방향으로 빠지려는데 다른 면에 가려져(occlusion) 못 빠지는 면 =
슬라이드/리프터(side action)를 강제하는 면. 목표는 언더컷(→ side action 수·부피)을 최소화하는 d 탐색. 이건 AM의 "서포트 부피 최소 배향 = S²
탐색"과 같은 저차원·고비용 문제라 SFTF 골격이 그대로 들어갑니다.


핵심 대응표 (component-by-component)









SFTF (AM)




금형 발형








build
direction d (한쪽, 중력)




draw
axis d, 단 ±d 양쪽 패스 (두 반쪽)








critical
angle θc




draft
angle α (이형 구배, 1–3°)








overhang
coeff oᵢ(d)




draft-deficiency
/ 이형 대상 가중치 gᵢ(d)








ray
along −d로 receiver 탐색




ray
along ±d로 occlusion(언더컷) 탐색








face-to-face
support (receiver j 존재)




내부
언더컷: 면 i가 면 j에
가려 못 빠짐 → side action 필요








height h_ij, 감쇠 w_ij




언더컷
깊이 = 슬라이드가 빠져나와야 하는 이동량








no
receiver → build plate (ground node)




ray가 부품
밖으로 탈출 → 파팅면/오픈으로 직접 이형








support
volume v_ss (비싼 TOMO)




언더컷 부피 /
side-action 수 (비싼 moldability CAE)








AVE 하드케이스
확대




경쟁
basin·경계 언더컷 많은 난해 부품에 동일 적용









수식 단위로 다시 쓰기


논문의 통합 Rayleigh 비용


R(d)
= Σ_{(i,j)∈S} oᵢ w_ij (nᵢ·d)(nⱼ·d) + Σ_{i∈G} oᵢ


를 금형 버전으로 옮기면 — 양쪽 패스 ±d를 합치고, 면 가중치를 이형 면적 기반으로 바꾸고, ground 항의 의미를 뒤집습니다.


(1) 이형 대상 가중치 (overhang coeff 대체). +d 패스에서 캐비티 측 면(nᵢ·d > 0)에 대해


gᵢ⁺(d) = Aᵢ · max(0, nᵢ·d) (투영 이형 면적), 추가로 draft 부족분 max(0, sinα − nᵢ·d)를 벌점으로 더할 수 있음. → 너의 oᵢ 정의에서 임계각을 draft
angle로, 부호를 "위로 빠지는 면"으로 바꾸면 코드 한 줄 수준 교체.


(2) Ray casting = 언더컷 판정 (internal visibility 그대로). cᵢ에서 +d로 ray 발사.



부품 밖으로 탈출
→ 클린 이형 (ground 항으로).


다른
면 j에 먼저 충돌 → 면 i는 j 뒤에
갇힘 = 내부 언더컷. 이동량 h_ij(슬라이드 행정), 영향 w_ij는
깊이에 대한 함수.


AM의
receiver 유효조건(nⱼ·d>0 등)은 금형에선 "차폐 face가 실제로 이형 경로를
막는가"로 치환.



(3) 비대칭 flow tensor. 양쪽 패스 각각


F⁺(d) = Σ_{(i,j)∈S⁺} gᵢ⁺ w_ij (nᵢ ⊗ nⱼ), F⁻(d)도 −d로 동일, F(d)=F⁺+F⁻.


이게 "어느 면이 어느 면에 갇히는가"라는 방향 의존 entrapment 관계를 비대칭
텐서로 인코딩 — SFTF의 원래 의도와 정확히 같은 구조.


(4) Ground node = 파팅면 직접 이형, 단 부호 1회 반전. 여기가 유일하게
"지적으로 다른" 부분이에요. AM에선 build-plate 도달이 비용(penalty
B) 이지만,
금형에선 파팅면으로의 클린 이형이 좋은 결과(reward) 입니다. 수학은 동일 — 가상 receiver 법선 d, 증강 텐서의 Rayleigh 수축 dᵀ(d⊗d)d = (d·d)² = 1 → 각 클린-이형 면이
정확히 gᵢ만큼 기여 — 부호만 반대.
그래서 목적함수를 "언더컷 최소화"로 두면:


U(d)
= Σ_{entrapped, ±} gᵢ w_ij (nᵢ·d)(nⱼ·d) − λ · Σ_{clean release} gᵢ


의 형태로, ground 항이 reward(음수)로 들어갑니다. 통합 Rayleigh 항등식 U + release = total이 그대로 성립해서, 논문의
ground-node 유도(스칼라 패치 → 텐서 수축 통일)가 부호만 바뀐 채 보존돼요.


(5) 그대로 재사용 — 거의 안 건드림. 512 Fibonacci-sphere → 콘 재샘플 → 각도
NMS top-K basin → 비싼 검증기는 ±10° 윈도우에서만 → AVE 하드케이스 확대. 이 파이프라인 전체가
그대로입니다. 교체되는 건 면 단위 커널(oᵢ→gᵢ, receiver 유효조건, 양쪽 패스)과 검증기뿐.


비싼 검증기(TOMO) 자리에 들어갈 것


금형의 "정확한 ground truth" = exact moldability/undercut
평가기. voxel 기반 global accessibility / visibility map(가우스 맵·shadow) 방식의 자체 구현이나,
Moldflow류 상용 CAE의 언더컷·side-action 판정을 백엔드로 둡니다. SFTF는 그 비싼 평가를 수 ms 사전선별로
줄여주는 warm-start 역할. 산업적 가치가 직접적인 지점이 여기예요 — 견적 단계에서 발형 방향·side action 유무를
빠르게 스크리닝해서 금형비/DFM 피드백을 조기에 주는 것. impact factor보다 현장에 꽂히는 게 바로 이 부분입니다.




요약하면, 너의 두 핵심 기여(비대칭 entrapment 텐서 + ground-node Rayleigh
통합)는 거의 손대지 않고 살아남고, 진짜 설계 결정은 단 두 개 — (i) ±d 양쪽 패스 처리, (ii)
ground 항을 penalty→reward로 부호 반전 — 뿐입니다.


원하면 이어서 (b) 필요한 수정 사항(양쪽 패스 동시 최적화, 파팅 라인 일관성, draft 검사 vs
언더컷 검사 분리, 다중 side-action 방향 등 실제 구현에서 새로 생기는 이슈)과 (c) 산업 검증 시나리오(어떤
부품셋·어떤 baseline·어떤 지표로 "현장에 도움됨"을 보일지)로 넘어갈게요. (b)부터 갈까요?




출처:
<https://claude.ai/cowork/cse_01EevroX5Hj41Z74zjgBPBYr>




좋아.
(b) 부탁해


4분
전


(a)에서 매핑은 깔끔했지만, (b)는 솔직히 말해 금형이 AM보다 본질적으로 어려운 지점들을 드러내는
단계예요. 같은 골격을 쓰되, AM엔 없던 제약이 새로 생깁니다. 변경 강도순으로 세 묶음으로 정리할게요.


Tier A — 알고리즘 골격을 바꿔야 하는 것 (필수)


A1. 탐색 공간이 S²가 아니라 RP² (사영공간).


2판 금형에서 d와 −d는 같은 발형 축 입니다(캐비티/코어 역할만
swap). 그래서 antipodal 식별이 필요해요 — 512 Fibonacci 샘플의 절반만 유효, NMS도 antipodal 병합으로
바꿔야 함. 코드 변경은 작지만 개념적으로 중요하고, 덤으로 후보 풀이 2배 줄어 그만큼 빨라집니다. (3판·핫러너 등 예외는 별도 처리.)


A2. 언더컷은 "서포트 붙이면 끝"이 아니라 "feasible side-action
방향이 존재하는가"라는 중첩 문제.


이게 AM과의 가장 큰 차이예요. AM에선 모든 overhang이 서포트로 항상 해소되고 비용은 연속적(부피)입니다. 금형에선 언더컷 면마다
슬라이드/리프터가 부품과 충돌하지 않는 이형 방향을 가져야 하고, 그게 없으면 die-lock(이형 불가) —
부품 재설계나 분할 코어가 필요한 별개 사건입니다. 그래서:



언더컷을 스칼라 벌점으로 끝내면
안 되고, entrapment 텐서가 알려주는 차폐 방향을 side-action 후보 방향의 seed로 쓰는 2차 방향
탐색이 붙습니다.


진짜 비용은 언더컷
부피가
아니라 side-action 개수입니다. 작은 언더컷 여러 개가 한 방향으로 한 슬라이드에 묶이면 싸고, 제각각 다른
방향이면 비쌈. → 언더컷 면을 호환 이형 방향으로 클러스터링(구면 위 NMS와 같은 종류)하는 단계가 새로 필요.



여기가 금형 버전의 진짜 연구·구현 코어이자, 산업적으로 돈이 갈리는 지점입니다.


A3. Draft를 언더컷과 분리된 별도의 하드
채널로.


AM의 overhang은 임계각 넘으면 서포트로 회복 가능한 연속 비용이지만, 금형에선 nᵢ·d ≈ 0인 거의 수직 벽은 언더컷이
아니어도 스커핑·이형 손상·이젝션 불량을 냅니다. 즉 실패 모드가 두 개예요:



언더컷 채널: occlusion
/ die-lock → ray casting에서.


Draft
채널: nᵢ·d가 너무 작음 → 순수 국소(법선만), 사실상 (a)에서 베이스라인으로
쓰던 대칭 텐서가 여기서 제 역할을
찾음.



그리고 둘은 trade-off 합니다 — 언더컷을 줄이는 방향이 저-draft 벽을 양산할 수 있음. 다행히
논문의 rank-normalized scoring이 차원 다른 항들을 scale-robust하게 묶는 바로 그 도구라, 이 다채널
목적함수에 그대로 맞아요. (오히려 AM보다 rank-norm의 명분이 더 분명해짐.)


A4. 검증기(TOMO 자리)가 스칼라가 아니라 구조화된 출력이어야
함.


AM 검증기는 v_ss 하나면 됐지만, moldability 검증기는 (i) 언더컷 클러스터, (ii) side-action
수, (iii) die-lock 플래그를 내야 합니다. 그래서 논문의 "ratio" 단일 지표가 다중 지표(언더컷
부피 비 + side-action 수 일치 + die-lock 검출)로 바뀌고, AVE의 confidence 신호도 재정의해야 해요
— 예: nᵢ·d≈0 경계 밴드 면적이 크거나,
작은 d 변화에 side-action 수가
민감하면 escalate.


Tier B — 점수 벡터에 새 항 추가 (중간)


B1. 파팅 라인 일관성/복잡도 항.


A1~A3의 면별 분류는 국소 라벨이지만, 실제 파팅은 두 반쪽이 만나는 연속·닫힌
경계(파팅 라인) 가 필요합니다. 국소 sign 분류는 누더기·지그재그 경계를 만들 수 있어, 깔끔한 분할엔 graph-cut류
정규화가 필요. SFTF가 d를 랭킹하는 건 그대로 두되, 점수
벡터에 파팅 라인 복잡도 proxy(예: nᵢ·d≈0 밴드의 면적·산포)를 한 피처로 추가하면 "복잡 파팅을 강요하는 방향"을 미리 깎을
수 있습니다.


B2. w_ij 감쇠 함수의 재형성.


AM에서 height는 서포트 재료량(연속)이지만, 금형에서 언더컷 깊이는 슬라이드
행정·금형 크기에
들어가는 2차 요인이고 1차 비용은 "슬라이드가 필요한가" 라는 거의 계단형입니다. 랭킹용 w_ij는 부드럽게 두되, 검증기는 이산
side-action 수로 평가하는 식의 이원화를 권합니다.


Tier C — 산업 채택을 위한 제약·강건성 (도입 성패를 가름)


C1. S² 탐색이 자유롭지 않고 제약·가중됨.


현장 발형 방향은 보통 묶여 있어요 — Class-A(외관)면엔 파팅 라인·게이트 자국 금지, 이젝션은 코어 측,
기능 축 정렬 등. 그래서 자유 탐색이 아니라 금지/선호 축 마스크 + 지정 면 통과 벌점을 얹은 제약 탐색이 됩니다.
Fibonacci 샘플에 마스크·가중을 거는 식으로 추가는 쉬움.


C2. CAD 메시 강건성.


Stanford 메시와 달리 금형 부품은 sliver 삼각형, non-manifold 엣지, 미세 필렛(둥근 엣지
→ nᵢ·d가 연속적으로 변하는 경계 밴드)이 흔해 ray
casting이 더 취약합니다. 가능하면 draft는 원본 B-rep에서, ray는 epsilon·first-hit fallback 강화.
(논문의 결정론적 source 샘플링이 출발점은 되지만 더 다듬어야 함.)


C3. 단일 최적해가 아니라 다중 후보 의사결정 출력으로.


이건 문제가 아니라 기회예요. 엔지니어는 "축 A = 슬라이드 0개지만 파팅 지저분 / 축 B =
슬라이드 1개지만 Class-A 깨끗" 같은 2~3개 전략 비교를 원합니다. SFTF의 top-K basin + 항별 피처
분해가 그대로 DFM 의사결정 자료가 됩니다. 단일 optimum보다 이 다후보 제시를 전면에 내세우는 게 산업적으로 더 먹혀요.




핵심만 다시 추리면: 그대로 가는 건 파이프라인(샘플→콘 재샘플→NMS→국소검증→AVE)과
rank-norm scoring이고, 진짜 새로 만들어야 하는 건 딱 두 덩어리 — (A2) side-action
feasibility/클러스터링 + die-lock, 그리고 (A4) 구조화된 moldability 검증기 — 입니다. 나머지(RP² 축소,
draft 분리 채널, 제약 탐색, 다후보 출력)는 기존 틀에 항·마스크를 더하는 수준이에요.


이어서 (c) 산업 검증 시나리오로 가면 좋을 것 같아요 — 어떤 부품셋으로(예: 단순 draft 부품
→ 명백한 1-슬라이드 부품 → die-lock 부품의 난이도 사다리), 어떤 baseline 대비(PCA·주축·엔지니어 수작업 발형),
어떤 지표로(side-action 수 정확도, die-lock 재현율, 풀스윕 대비 검증 예산 %) "현장에 도움됨"을
증명할지까지 짜드릴게요. (c) 갈까요?




출처:
<https://claude.ai/cowork/cse_01EevroX5Hj41Z74zjgBPBYr>




(c)는
"impact factor가 아니라 현장"이라는 목표에 맞춰, 표를
예쁘게 채우는 검증이 아니라 "이게 견적·금형비를 실제로 줄이는가"를 증명하는 검증으로 설계할게요. 논문의
A–E 그룹·budget curve·LOMO 같은 엄밀성은 그대로 빌려오되, 지표를 산업 언어로 갈아끼웁니다.


1. 부품 난이도 사다리 (A–E 대체)


AM의
"shape difficulty × mesh scale" 대신, 금형
난이도 = 언더컷/side-action 복잡도로 축을 다시 잡습니다.









Tier




성격




정답이 자명한가




검증 목적








T0




draft만 있는
단순 부품(박스+보스, 컵)




구성상 자명




위생 검사(절대
틀리면 안 됨)








T1




side-action
1개 명백(사이드 홀, 스냅훅, 측면 보스)




거의 자명




단일
언더컷·이형방향 시드 정확도








T2




경쟁 발형
방향·다중 슬라이드(커넥터 하우징, 브래킷)




모호




basin 경쟁·side-action 수 핵심








T3




die-lock
/ 재설계 없이는 불가(캡티브 언더컷)




함정




die-lock recall(가장 비싼 실패)









부품 출처:
Thingi10K에서 사출 적합 부품 필터 + DFM 교재 표준 예제 + (가능하면) 실제
양산 부품 — 실제 채택된 발형 방향과 실제 슬라이드 수를 아는 골드 데이터. T3는 일부러 함정 부품을 넣어야 합니다(논문의
Happy 50k 하드케이스 역할).


2. 정답(ground truth) 정의 — 세 겹


순수 자체 검증은
순환논리에 빠지니 독립적 GT를 둡니다:



Exact moldability 검증기(TOMO 자리): voxel/visibility accessibility로 언더컷 클러스터 +
side-action 수 + die-lock 플래그 산출. SFTF가 warm-start하는 그 비싼 백엔드.


전문가 주석: 실제 채택된 발형 축 + 실제 슬라이드
수(진짜 골드, 구하기 어렵지만 가장 설득력 큼).


상용 CAE 교차검증: NX Mold Wizard /
Moldflow류의 draw analysis와 대조(1·2를 못 구할 때 보강).



3. Baseline — 이겨야 할 대상


논문 구도를 그대로
차용:



PCA 주축, 대칭
support/fabric 텐서 고유벡터(너의 기존 baseline)


"바운딩박스
6면" 휴리스틱(주니어가 먼저 시도하는 6방향) — 현장 현실 baseline


budget-matched
uniform/random 국소 윈도우(논문 Table 3 그대로)


엔지니어
수작업(시간·정확도
비교 대상)


풀스윕 + exact 검증기 =
oracle(상한, 그리고 우리가 비용을 줄여주는 그 대상)



4. 지표 — 산업 언어로 재정의


논문의 단일 v_ss
ratio 대신 다중·현장 지표:



(1순위)
side-action 수 일치율: 국소검증 후 top-K basin이 최소-슬라이드 발형을 회복하는가. exact-match와
±1 슬라이드 모두 보고. → 슬라이드 1개 = 금형비·사이클타임 직결이라 이게 곧 돈.


(2순위)
die-lock recall: 진짜 die-lock 부품을 플래그하는 비율. 견적
단계에서 놓친 die-lock이 가장 비싼 사고라, recall이 헤드라인 지표. (precision보다 recall 우선.)


검증
예산 %:
풀스윕 대비 평가 비율(논문 지표) → 절감 시간/비용으로 환산.


첫
양호 후보까지 wall-clock (ms): 견적 속도 피치.


draft
결손 면적:
2차 품질.


전문가
선택과의 top-1 일치(κ).


툴링
비용 proxy:
(SFTF 선택 vs oracle)의 슬라이드 수 차 × 슬라이드당 통상 단가 → "달러로 얼마 손해 안
보는가".



5. 프로토콜 — 논문 엄밀성 재사용



튜닝 가중치는 LOMO/nested
CV(너가
이미 calibration 과적합으로 학습한 그 교훈 — in-sample 1.94→LOMO 2.37 사례를 여기서도 명시).


budget-matched
대조군(uniform/random)으로
"이득이 예산 크기가 아니라 윈도우 배치에서 온다"를 동일하게
증명.


AVE
평가:
escalation 전/후 최악 side-action 오차와 그 예산 비용(논문 Table 5의 12.44→1.62 구도).


T3(die-lock)는
분리 보고 —
평균에 섞지 않기(Happy 50k 교훈).


큰 coarse-grid 셋으로 타이밍·확장성
감사(A–E
3° audit 대응) — C++ 구현 speedup 재현.



6. 산업적 "so what" — 표 너머의 증명


여기가 impact
factor와 갈리는 지점입니다. 표만으로는 현장이 안 움직여요.



견적-단계
데모: 부품
투입 → <1s에 top-3 발형 전략을 슬라이드 수 + Class-A 충돌 +
die-lock 플래그와 함께 제시. (b)의 다후보 의사결정 출력이 그대로 데모가 됨.


시간-동작
비교:
"엔지니어 단독" vs "엔지니어+도구"가 방어
가능한 발형 결정에
도달하는 시간.


가장
강력한 한 방 — 회고적 파일럿: 협력 금형사/사내 툴링팀의 과거 N개 잡에 도구를 돌려서 (i) 추천 발형이
실제 채택과 일치했는가, (ii) 실제로 발생했던 비싼 설계변경(ECO)을 견적 시점에 잡아낼 수 있었는가를 본다. 이게 되면 논문 한 편보다
도입 한 건이 옵니다.



7. 정직성 — 결과를 좋게만 보이게 하는 함정



GT
순환:
검증기가 SFTF 가정과 같으면 무의미 → 전문가/CAE 같은 독립 GT 필수.


부품
선택 편향:
쉬운 부품만 넣으면 다 맞음 → T2·T3(모호·die-lock)를 반드시 포함.


메시
품질 교란:
CAD 슬리버/필렛이 ray를 흔듦 → 메시 품질을 공변량으로 기록.


범위
한정: 발형
방향은 비용의 일부(게이트·냉각·휨은 별개) → 주장을 "발형/언더컷 사전선별"로 좁게 못 박기.





요약하면 검증의 북극성은 두 지표 — side-action
수 일치율(=돈)과 die-lock recall(=견적
사고 방지) — 이고, 나머지 예산%·속도·CV는 논문 틀을 그대로 빌려옵니다. 그리고 진짜 설득은 표가 아니라 과거 잡 회고 파일럿에서 나와요.


이제
(a)+(b)+(c)가 한 줄기로 모였으니, 원하면 이걸 한 장짜리
연구기획서(.docx 또는 .md) 로 정리해드릴게요 — 문제정의·매핑·신규 구현 이슈·검증계획·산업 파일럿까지. 아니면 바로
다음 실무 단계로, exact moldability 검증기(=TOMO 자리)부터
프로토타입으로 짜보는 것도 가능하고요. 어느 쪽으로 갈까요?




좋아.
수고했어. 고마워.


지금


천만에요, 도움이 됐다니 기쁩니다. 짧게 정리만 남겨둘게요 — 나중에 이어갈 때 참고하시라고요.


지금 repo에는 연구계획(draft/SFTF_InjMold_research_plan.md) → exact 검증기 → 금형판 SFTF
warm-start+AVE → 검증 하니스·벤치마크 → 견적용 의사결정 시트까지, 21개 테스트와 함께 python/src/moldability/에 들어가 있습니다. 다음에 이어갈
때는 BUILDSPEC.md의 R1~R12를 Claude Code에 맡기면
되고, 그중 R8(가중치 LOMO 보정)·R7(실부품 GT)·**R1(side-action 최소 set-cover)**이 산업
가치에 가장 직접적입니다.


연구 잘 풀리길 바랄게요. 또 필요하면 언제든 불러주세요!




출처:
<https://claude.ai/cowork/cse_01EevroX5Hj41Z74zjgBPBYr>




성능 최적화 완료 ✅


R2가 도입한 반구 pull 검색으로 ray 캐스팅 호출이 급증해 전체 suite가
11분으로 늘어난 문제를, 결과를 비트
단위로 동일하게 유지하면서 해결했습니다.


변경 사항 — geometry.py


ray_is_occluded와 ray_first_hit의 origin마다
도는 Python 루프를 제거하고, origin에 대해서도 벡터화했습니다. 메모리 폭증을 막기 위해 origin을 _ORIGIN_CHUNK(2048) 단위 청크로 처리 — 큰
메시에서도 (chunk
× M × 3)
임시 배열로 RAM을 제한합니다. Möller–Trumbore 수식·임계값·ignore_index 자기교차 제외 로직은 그대로라 출력이 동일합니다.


검증



결과 불변 확인: 6개 부품의
SA/die-lock/lifter 값이 최적화 전과 정확히 일치 (tilted_tube의 lifter@20° 포함)


전체 25개 테스트 통과: 174초 (2분 54초) — 최적화 전 11분 대비 약 3.7배 단축, R2
이전 R1 기준(5분)보다도 빠름


벤치마크
숫자는 결과가 동일하므로 리포트 수정 불필요



참고



이
최적화는 numpy 레퍼런스 경로를 빠르게 만든 것이고, BUILDSPEC
R5(>1e5 면 메시용 trimesh/embree 백엔드)는 여전히 별개로 남아 있습니다.
청크 방식이라 현재 프로토타입 규모(≤수백 면)에서는 단일 벡터화 패스로 처리됩니다.


체인지로그에
perf 항목 기록 완료.





지금까지 이번 세션에서 완료한 것: R1(side-action
최소 set-cover) → R2(lifter 인식 die-lock 강화) → 성능 최적화(ray caster 벡터화). 전체 25개 테스트 그린.


다음은 R3(draft를 별도 채널로
점수화) 또는 R8(SFTF 가중치 LOMO 보정)이 후보입니다. 계속할까요?






R4 완료 ✅


파팅 라인 복잡도 proxy를 추가했습니다 — SFTF 점수가 나중에 복잡한 파팅을 벌점화할
수 있도록.


변경 사항


코어 — verify.py



parting_band_area: |n·d| ≤ sinα 밴드(파팅 라인/면이 지나는
근수직 면)의 총 면적


parting_band_spread: 그 밴드의
draw 축 방향 면적 가중 산포 ÷ bbox 대각선 (무차원). 평면 파팅 → 낮음, 계단형 파팅 → 높음


summary()에 노출 → CLI 자동 출력



부품/테스트 — parts.py, test_moldability.py



stepped_block(undrafted_box와 동일한 bbox의 2단 블록
— 정규화 동일조건에서 파팅 구조만 차이)




테스트:
계단형 밴드 spread가 단일 평면 밴드보다 엄격히 큼



노출 — report.py payload에 두 필드 추가


문서 — BUILDSPEC R4 [DONE]+체인지로그+카운트(27),
README(27)


검증값 (draw +z)









부품




band_area




spread








drafted_box
(5° 구배)




0.00




0.000








undrafted_box
(평면 파팅)




16.0




0.096








stepped_block
(계단 파팅)




12.0




0.144









새 필드는 랭킹 키와 무관한 부가 피처라 벤치마크
리포트 변동 없음(stepped_block/undrafted_box는 builtin() 밖이라 벤치에도 미포함).




이번 세션 누적: R1(set-cover) → R2(lifter die-lock) → perf(벡터화 11→3분) → R3(draft 채널) → R4(파팅 복잡도). 전체 27개 테스트 그린.


다음 후보:



R8 — SFTF 점수 가중치 LOMO 보정 (★SFTF
정확도, sftf.py)


R9 — cone-refined 2단 샘플링 (좁은
basin 포착)


R7 — 실제 Thingi10K 데이터셋



어느 것을 진행할까요?




R8 완료 ✅


SFTF 점수 가중치를 검증기 대비 rank-tuning으로 보정하고 LOMO
교차검증으로 과적합(optimism)을 정량화하는 모듈을 추가했습니다
— 논문의 1.94→2.37 optimism 체크의 금형판.


변경 사항


신규 모듈 — calibrate.py



label_part: 공유 축 풀(Fibonacci 반구
+ X/Y/Z 시드)을 검증기로 1회 라벨링 → 축당 SFTF 피처 + side-action 비용 캐시


_score: propose와 동일한 rank01 스코어링 재사용 → 보정된 가중치가 배포 경로에 그대로 전이


fit_weights: 캐시 위 좌표하강으로 평균
best-of-K 최소화


lomo: 부품 하나씩 hold-out →
나머지로 fit → held-out 평가. moldable
부품만 집계, die-lock은 별도 recall


CALIBRATED_WEIGHTS: LOMO
검증된 결과(P 1→2). propose(mesh,
weights=...)로 사용



테스트 — test_calibrate.py: 프로토콜 무결성 6개 (누수 없음, in-sample≤default, optimism
방향, die-lock recall=1.0, held-out에서 자명 가능 부품 복원). 빠른 subset(콘 제외, 48축)으로 3초.


리포트 — draft/SFTF_InjMold_calibration_report.md (python -m
moldability.calibrate로 생성)


문서 — sftf.py
docstring/주석이 calibrate.py를 참조, BUILDSPEC R8 [DONE]+체인지로그+카운트(33), README(33)


핵심 결과 (해석 사다리)









추정기




평균 best-of-3








DEFAULT_WEIGHTS




1.000








보정
in-sample




0.250








보정 LOMO held-out




0.250









baseline 대비: bbox6 0.50 / pca 0.00 / SFTF(LOMO) 0.25 — die-lock recall 1.0.


정직한 발견: 보정이 best-of-K를 1.0→0.25로 4배 개선하고 SFTF가 bbox6를 이기지만, 이 셋에선 PCA(0.0)에 짐 — 길쭉한 튜브라 PCA 주축=이형축이기 때문(기존 벤치 서술과 일치). SFTF의 진짜
우위는 주축≠이형축인 **실제 부품(R7)**에서 드러납니다. 또한 best-of-K는 윈도우 없는 raw 풀
기준이라 배포 warm-start(윈도우+AVE)의 보수적 하한임을 리포트에 명시했습니다.




이번 세션 누적: R1→R2→perf→R3→R4→R8.
전체 33개 테스트 그린.


R8의 결과가 가리키듯, 다음으로 가장 가치 있는 건 R7(실제 Thingi10K T0–T3 데이터셋 — PCA 대 SFTF를 진짜로 변별)입니다. 또는 R9(cone-refined 2단 샘플링 — rect_tube 같은 좁은 basin을 raw 랭킹에서도 포착)이 R8에서 드러난
rect_tube=1.0 문제를 직접 겨냥합니다. 어느 쪽으로 갈까요




R7 완료 ✅ (하네스 — 오프라인)


R7의 목표는 실제 Thingi10K 부품이지만 이 환경엔 인터넷이 없습니다. 실제-메시 파이프라인을 오프라인에서 끝까지 완성해, 사용자가 실제 STL을 폴더에 떨구면 동일 경로가 즉시 동작하도록 했습니다.


변경 사항


실제-메시 I/O — io.py



write_binary_stl: trimesh 없이 바이너리 STL
쓰기 (CCW 법선)



큐레이션 데이터셋 — datasets.py



curated(): 해석 사다리 + R1–R4 피처
부품을 묶은 티어드 T0–T3 셋 (GT 기록)


export_folder(): 부품을 .stl로 출력 → load_folder로 왕복



테스트 — test_realmesh.py 3개:



큐레이션 사다리 구조/GT 검증




STL 왕복 충실도: 면 수 + side-action/die-lock/lifter 판정
보존 (tilted_tube의 lifter 포함)


LOMO 감사가 STL에서 적재한 메시 위에서 end-to-end
동작 (die-lock recall 1.0)



문서 — BUILDSPEC R7 갱신, 체인지로그, 카운트(36), README


정직한 발견 (왜 실제 부품이 필요한가)


해석 부품으로 PCA를 이기는 구성을 실증 탐침했으나 실패했습니다 — **PCA는 회전
등변(rotation-equivariant)**이라 해석 부품의 이형축은 항상 질량 주축에 묶입니다:



rect_tube_rotated →
PCA가 8°로 복원, tilted_tube → 15°로 복원 (둘 다 PCA가 찾아냄)


l_bracket/sheared_step → 모든 축 die-lock



즉 이형축이 질량 주축과 무관한 부품은 실제 기능형
지오메트리에서만 나오며, 이것이 바로 R7이 실제 데이터를 요구하는 이유입니다. 이 점을 BUILDSPEC R7에 명시했고, 하네스는 그
드롭인을 완전히 지원합니다.




이번 세션 누적 (전체 36 테스트 그린)


R1(side-action 최소 set-cover) → R2(lifter die-lock
강화) → perf(ray caster 벡터화, 11→3분) → R3(draft 채널) → R4(파팅 복잡도) → R8(SFTF 가중치 LOMO
보정) → R7(실제-메시 하네스).


남은 로드맵 후보:



R9 — cone-refined
2단 샘플링: R8에서 드러난 rect_tube=1.0(좁은 basin을 raw 랭킹이 놓침) 문제를 직접 겨냥


R5 — 대형 메시용 embree 백엔드 (>1e5
면)


R6 — 제약 조건부 발형 탐색 (Class-A 금지축
마스크)


R10/R11/R12 — stratified 샘플링 / AVE 신뢰도 /
의사결정 시트 UI 강화





Cone refinement이 명확히 효과적입니다:



coarse만: X에 최근접 10.5°, P==0(이형 가능) 후보는 X
근처에 없음(999)


refined: X에 최근접 5.9°, 그 후보가 P==0 — coarse가 놓친 좁은 이형 basin을 시드
없이 포착



R9 테스트를 추가합니다.






Added 4 lines


Bash Re-run sftf tests


IN


cd
"d:/__SFTF_Projects(2026)/SFTF_InjMold_dev" &&
PYTHONPATH=python/src uv run pytest python/src/moldability/tests/test_sftf.py
-q -p no:cacheprovider --no-header 2>&1 | grep -v RuntimeWarning | tail
-5


OUT




....... 
[100%]

7 passed in 11.00s




7개
통과 (R9 포함). 총 37개. 전체 suite로 회귀 확인(특히 warm_start/bench가 refine 기본값에 영향받는지)하고,
동시에 문서를 갱신합니다.


Bash Run full suite after R9


IN


cd
"d:/__SFTF_Projects(2026)/SFTF_InjMold_dev" &&
PYTHONPATH=python/src uv run pytest python/src/moldability -q -p
no:cacheprovider --no-header > "$TEMP/full8.txt" 2>&1;
echo "rc=$?" >> "$TEMP/full8.txt"


OUT




Command
running in background with ID: b9zs1yblw. Output is being written to:
C:\Users\USER\AppData\Local\Temp\claude\d----SFTF-Projects-2026--SFTF-InjMold-dev\2ac08520-1735-4f41-af13-23b307d6cf3d\tasks\b9zs1yblw.output.
You will be notified when it completes. To check interim output, use Read on
that file path.




전체 37개 테스트 통과 (176초, 2:55) — 회귀
없음(warm_start/bench 포함).


R9 완료 ✅


propose()의 단일 Fibonacci 패스를 논문의 2단계
cone-refined 샘플링으로 교체했습니다.


변경 사항 — sftf.py



_score_candidates:
coarse/refined 패스가 동일 기준으로 랭크하도록 스코어링 분리


_cone_directions: 중심 축 주변 cone_deg 캡에 결정적 Fibonacci
나선으로 n개 방향 생성 (RNG 없음 → 재현 가능)


propose 2단계: coarse
Fibonacci로 basin 윤곽 잡기 → 상위 refine_centers basin 주변 tight cone 재샘플 → 통합 재스코어 → NMS. refine_centers=0이면 기존 단일 패스.



검증 (rect_tube, 시드 없음)













X축 최근접 후보




X 근처 P==0(이형 가능)








coarse만




10.5°




없음








refined




5.9°




있음 (5.9°)









좁은 홀-축 basin을 cone refinement가 시드
없이 포착 —
R8에서 드러난 rect_tube 좁은 basin 문제를 정확히
겨냥. 배포 경로(warm_start→propose)가 더 나은 시드를 받습니다.


테스트



신규 test_cone_refine_catches_narrow_hole_basin: refined가 coarse보다 X에 가까워지고(≤8°), P==0 후보가 cone 안에
존재함을 핀


기존 test_propose_surfaces_hole_basin의 과도하게 엄격한 P==0 단언을 <0.1로 완화(주석으로 이유 명시) — refine로 basin이 채워져 NMS가 점수 기준 대표
1개를 고르므로. 정확한 P==0 보장은 신규 R9 테스트가 담당.



문서 — BUILDSPEC R9 [DONE]+체인지로그+카운트(37),
README




이번 세션 누적 (전체 37 테스트 그린)


R1→R2→perf→R3→R4→R8→R7→R9. 로드맵 R1–R4·R7·R8·R9 + 성능 최적화 완료.


남은 항목:



R5 — 대형 메시용 trimesh/embree 백엔드
(>1e5 면)


R6 — 제약 조건부 발형 탐색 (Class-A 금지/선호
축 마스크)


R10 — stratified source 샘플링 (대형 메시
텐서 추정 비편향)


R11 — AVE 신뢰도 신호 재정의
(warmstart.py)


R12 — 의사결정 시트 UI 강화 (Flask 업로드 /
메시 다운샘플 / pull 화살표)



다음으로 무엇을 할까요?






R5를 진행합니다 — ray_is_occluded 뒤에 대형 메시(>~1e5
면)용 trimesh/embree 경로를 자동 선택으로 추가하고, numpy를 감사 가능한 레퍼런스로 유지합니다. (이 환경엔 trimesh
미설치라 trimesh 경로는 미설치 시 numpy로 우아하게 폴백하도록 구현하고, 일치 테스트는 trimesh 있을 때만 실행되게
합니다.)


먼저 현재 벡터화된 ray_is_occluded 본문을 확인합니다






R5 완료 ✅


ray_is_occluded 시그니처를 바꾸지 않고 뒤에서 대형
메시(>~1e5 면)용 trimesh/embree 경로를 자동 디스패치하도록 했습니다. numpy는 감사 가능한 레퍼런스로 유지.


변경 사항 — geometry.py



_occluded_numpy: 기존 벡터화
Möller–Trumbore (감사 레퍼런스)


_occluded_trimesh: trimesh.ray.intersects_first 기반. verifier의 사용 방식(법선 오프셋 origin,
t_max=inf, ignore_index 자기면 제외)에 충실 — t_min만큼 ray 방향 밀어 self-surface
제거, first-hit이 originating 면이면 차폐로 세지 않음. 유한 t_max는
NotImplementedError→numpy 폴백


choose_ray_backend: RAY_BACKEND_FACE_THRESHOLD(1e5) 이상 그리고 trimesh 임포트 가능 시에만 trimesh, 아니면 numpy


set_ray_backend: 테스트/벤치용 강제 선택; benchmark_backends: 두 경로
타이밍 + 일치율




fast path의 모든 예외는 catch → numpy 폴백 (정확성
절대 깨지지 않음)



테스트 — test_backend.py 5개



소형 메시 → numpy 자동 선택


임계값
낮추면 trimesh 가용 시 trimesh 선택




강제 trimesh
+ 경로 고장 → numpy 폴백 결과가 레퍼런스와 일치 (오프라인
결정적)




백엔드 인자 검증




pytest.importorskip("trimesh") — trimesh 설치 시 두 백엔드의 moldability 판정 일치 (오프라인
자동 스킵)



제약 (정직)


이 환경엔 trimesh 미설치라 embree 경로 자체는 실행 불가 —
디스패치·폴백·임계값 로직은 오프라인에서 검증되고, embree 일치/벤치마크는 trimesh 설치 환경에서 #5 + benchmark_backends로 검증됩니다. uv add trimesh 후 대형 Thingi10K 부품에 benchmark_backends를 돌리면 됩니다.


문서 — BUILDSPEC R5 [DONE]+체인지로그+카운트(42),
README




이번 세션 누적 (41 pass + 1
trimesh-gated skip)


R1→R2→perf→R3→R4→R8→R7→R9→R5.


남은 항목: R6(제약 조건부 발형 탐색 —
금지/선호 축 마스크), R10(stratified source 샘플링), R11(AVE 신뢰도 신호 재정의), R12(의사결정 시트 UI 강화 — Flask
업로드/메시 다운샘플/pull 화살표).


다음으로 무엇을 할까요?




전체 45 passed, 1 skipped (180초, 2:59)
— 회귀 없음.


R6 완료 ✅


exhaustive에 선택적 발형 제약을 추가했습니다 (산업 채택용, plan
C1).


변경 사항 — sweep.py



DrawConstraints 데이터클래스:



forbidden_axes/forbidden_deg: RP²(antipodal) 하드
제외 — 금지 축 근처는 best 후보에서 배제


preferred_axes/preferred_deg/preferred_bonus: 선호 축 근처에 소프트 보너스


classA_faces/classA_penalty: 태깅된 Class-A 면이 파팅
밴드(|n·d| ≤ sinα)에 걸리면 면적 가중 벌점



exhaustive(..., constraints=): 랭크 키를 (n_side_actions,
constraint_cost, undercut_area)로 확장. side-action
수가 여전히 1순위, 제약은 동점 타이브레이커. SweepRecord.forbidden/.constraint_cost로 노출




제약 미지정 시 기존 동작 동일 (soft cost가 모든
축에서 0 → 키 순서 불변)



검증



금지: rect_tube에서 X(유일 0-SA 축) 금지 →
best가 X에서 벗어나 SA=1로 강제


선호: 볼록 부품(모든 0-SA)에서 Y 선호 → best가 Y 정렬


Class-A: z-법선 면 태깅 → X-draw(밴드에 걸림)
cost=1.0 vs Z-draw cost=0.0



테스트 — test_constraints.py 4개
(금지/선호/Class-A/기본불변)


문서 — BUILDSPEC R6 [DONE]+체인지로그+카운트(46),
README




이번 세션 누적 (45 pass + 1
trimesh-gated skip)


R1→R2→perf→R3→R4→R8→R7→R9→R5→R6.


로드맵 Tier A(R1–R4)·R5·R6·R7·R8·R9 + 성능 최적화 완료. 남은
항목:



R10 —
stratified source 샘플링 (sftf._sample_sources 비편향, 대형 메시)


R11 — AVE 신뢰도 신호 재정의 (warmstart.py
— 윈도우 경계/섭동 민감도/파팅 밴드)


R12 — 의사결정 시트 UI 강화 (Flask STL 업로드
/ 메시 다운샘플 / pull 화살표)



다음으로 무엇을 할까요?



























OneNote에서 작성되었습니다.
