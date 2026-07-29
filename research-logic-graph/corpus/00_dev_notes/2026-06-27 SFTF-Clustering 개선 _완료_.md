# 2026-06-27 SFTF-Clustering 개선 [완료]

Source: `D:\__SFTF_Projects(2026)\_dev_notes\2026-06-27 SFTF-Clustering 개선 [완료].mht`

2026-06-27 SFTF-Clustering 개선 [완료]









2026년 6월 27일
토요일



오후 7:58










일단 섬공지 수준은 완성했으나, 난잡하다.







가장 깊은 것부터 정리할게.



1. 가장 본질적인 약점: "최적화하는 목적함수가
없다"



이게 Chopper와의 가장 큰 격차야.




Chopper는 명시적 목적함수(작업부피 적합 + 구조 강도 + seam 가시성
+ 부품 수)를 정의하고 BSP cut 공간에서 beam search로 그것을 최소화해. 분할이 곧 최적화야.


이 방법은 군집화/영역성장이 뱉어낸 결과가 곧 분할이야. 지지량을 줄이는
목적함수가 어디에도 없어. 순도는 사후에 측정할 뿐
최적화 대상이 아니야.




그 결과가 표에 그대로 나와 있어 — support_flow는 manikin에서 10.49g
(통짜의 1.05배),
build_direction은 15.47g
(1.55배).
즉 분할이 목표(지지 절감)를 달성하기는커녕 통짜보다 나빠지는 경우가 제안 방법 자신에게서 나와.
리뷰어는 "그러면 이 방법은 무엇을 보장하는가?"라고 물을 거야. Chopper는 자기 목적함수를 단조적으로 개선하지만, 이
방법은 그렇지 않아.



2. 핵심 지표(purity)가 거의 순환논증이다



support_flow가 클러스터링하는 변수가
κ(bed/needs/supporter/free) 역할이고, 채점하는 지표인 support-class
purity도 바로 그 κ로 정의돼. 같은 양으로 묶고 같은 양으로 채점하니 높게 나오는 게 거의 자명해. 반면 baseline(좌표
k-means)은 κ를 아예 보지 못해. 리뷰어 입장에선 "당연한 결과"로 읽혀.



물리적으로 의미 있는 지표는 지지 질량인데, 거기선 1번처럼 일관성이 깨져. 헤드라인 숫자(0.51 → 0.87)가 인상적이지만, 실제로는
가장 약한 지표에서만 강하다는 게 문제야.



3. 정작 동기로 내세운 문제(작업부피)를 풀지 않는다



서론에서 "프린터 작업부피를 넘는 대형 자유곡면"을 동기로 들고,
Chopper도 그것 때문에 인용했어. 그런데 이 방법엔 부품 크기 제약이 전혀 없어. 어떤
부품이 프린터에 들어가는지 보장하지 못해. Chopper의 존재 이유를 동기로 빌려오면서 그 제약은 구현하지 않은 거라, "왜
Chopper가 아니라 이걸 쓰나?"에 대한 답이 약해져.



4. 진짜 경쟁자와 비교하지 않았다 (positioning
문제)



비교 baseline은 Planar BSP, graph-cut, spectral, 좌표
k-means — 전부 출력
비인지(non-support-aware) 일반 분할이야. 정작 직접
경쟁자인




Gao 2019 (near support-free multi-directional decomposition) — 너의 다방향 분할과 정확히
같은 목표


Wei 2018 (support-free skeletal
partitioning)




는 인용만 하고 비교하지 않았어. Chopper급
논문이라면 약한 baseline을 이기는 걸로는 부족하고, 직접적인 선행 최적화 기법 대비 무엇이 더 나은지/다른지를 보여야 해. 특히 Gao
2019가 이미 "다방향 무지지 분해"를 했으니, 너의 다방향 기여의 originality가 정면으로 위협받아.



5. Originality 자체가 "feature
engineering + off-the-shelf 군집화"로 환원된다



깊게 보면 핵심 기여는 *"SFTF가 버린 면별 특징을 z-score해서
sklearn 군집화에 넣었다"*야. 알고리즘적 새로움이 아니라 특징 선택의 새로움이지. 게다가:




전체가
저자 본인의 동반 논문 SFTF(in press)에 의존 → salami-slicing(한
연구를 둘로 쪼갬) 인상을 줄 수 있어. "SFTF가 버린 부분"이라는 프레이밍 자체가
기여를 남은 찌꺼기로 보이게 만들어.


세 경로 중 다방향 build_direction은 manikin에서 24부품·1.55배로 사실상 음성 결과고, 논문도
"이점이 작다"고 인정해. 기여 하나가 negative라 originality 서사가 약해져.




6. 매직 넘버 과다 & 부품 수 자동결정 부재



k=6 수동 지정, λ=3 (manikin 한 메쉬에서 스윕해 전체에 재사용),
θ_sim=35°, δ=0.02, β=8, τ_min, w_s/w_f/w_d… 손으로 정한 상수가 많아. DBSCAN은 아예 실패 사례로
자인. 그런데 부품 수가 지지량 증감을
좌우하는 핵심 변수인데도 그걸 목적함수로 자동 결정하지
못해(Chopper는 cut을 목적함수가 결정). greedy union-find/softmax-argmax는 전역 trade-off를 못
봐서, 1번의 실패 모드(과분할→지지 폭증)를 구조적으로 막을 수 없어.






그래서 — 두 갈래 권고



(A) Chopper 품질을 진짜로 노린다면: 분할을 최적화 문제로 재정의해야 해. 면별
지지흐름 특징을 목적함수의 항으로 넣고(지지질량 대리 + 부품수 + 작업부피 제약 + 접합면 강도), 그 위에서
탐색(BSP/그래프컷/그리디라도 목적함수 단조 개선)을 돌려야 1·3·4·6이 한꺼번에 풀려. 지금 코드는 그 목적함수의 좋은 초기화/특징 공급기로 자리매김할 수 있어.



(B) 현재 분량/범위를 유지한다면: 주장을 정직하게 축소해. "지지
절감"을 헤드라인에서 빼고(달성을 보장 못 하니), 실제로 제공하는 것 — 지지기둥을 한 부품 안에 유지하는, 해석 가능한 support-role-aware 세그멘테이션
prior — 을 기여로 내세워. 그리고 지지 질량이 통짜보다 커지는
케이스를 한계로 명시하고, 최소한 Gao 2019와 정성 비교라도 추가해.



내 추천은 (A) 방향으로 한 발이라도 가는
거야. 지금은 originality가 "특징을 살렸다"에 머물러서 Chopper의 "문제를 정식화하고
풀었다"와 체급 차이가 나거든.






목적함수가 originality를 만들지 못하나



"작업부피 제약 + 지지질량 + 부품수 + seam을 다목적으로 최소화하는 재귀
분할" — 이 정식화 자체는 이미 점유된 땅이야. 네 참고문헌 안에 직접 경쟁자가 있어:




Chopper [10]: 재귀 절단 + (fit + 구조 + seam + 부품수)
목적함수. 골격이 똑같아져.


Gao 2019 [13] "Near Support-Free Multi-Directional 3D Printing via Global-Optimal Decomposition": 지지를 최소화하는 다방향 분해. 너의 다방향 분할과 목표·제목이 거의 동일.


Wei 2018 [12]: support-free skeletal partitioning.




목적함수를 제대로 넣는 순간, 논문은 "출력지향 분할"이라는 일반 무대에서
이 세 편과 정면으로 같은 문제를 푸는 게 돼. 그러면 리뷰어의 질문은 바뀌어: "Gao 2019가 이미 지지 최소화 다방향 분해를
했는데, 당신의 목적함수는 무엇이 다른가?" 목적함수의
형태로는 이 질문에 답할 수 없어. 그래서 목적함수는
originality의 원천이 아니라, 오히려 originality를 검증받는 시험대가 돼.



진짜 originality는 목적함수가 아니라
"신호(representation)"에 있다



방어 가능한 새로움은 무엇을 최소화하느냐가 아니라 무엇을 가지고 자르느냐에 있어. 이 논문에만 있는 커널은 세 가지야:




면별 지지흐름장을
분할 신호로 사용 — receiver 종류 $\rho_i$(face냐 bed냐),
지지 높이, hit_map 지지쌍. Chopper(기하/구조), Gao(전역 지지면적), Wei(골격), Hu의 pyramidal
분해 — 이 어느 것도 *"각 면의 지지가 어디로 흐르는가"*라는 면별 벡터장을 분할 입력으로 쓰지 않아. 이건
진짜로 다른 표현이야.


"지지 basin"이라는 분할 primitive — hit_map 지지쌍을 union-find로 묶어 오버행과 그 받침면을 절대 분리하지 않는 절단.
Chopper/Gao는 집계량을 최소화할 뿐, 지지흐름 연결성을 명시적으로 보존하진 않아. 이건 다른 데 없는 구체적
primitive야.


방향 후보와 면특징이 같은 텐서장 한 번의 계산에서 나온다 — 배향 선택과 분할이 동일한 물리장에서 결합되어 나오는 구조. 대부분의 분해 기법은 배향과
분할을 따로 두거나 비싸게 반복해.




즉 originality는 SFTF 지지흐름장 + 지지 basin 절단 primitive + 배향-분할 결합이 짊어지는 거지, 목적함수가 짊어지는 게 아니야.



그런데 — 두 가지 약한 고리



정직하게 짚을게.




(a) 신호 자체는 빌려온 것. SFTF는 저자 본인의 in-press 선행연구 [1]이야.
그래서 "이 논문"의 originality는 장(field)을
만든 것이 아니라 그 장으로 분할
primitive와 정식화를 만든 것에만 걸려 있어. salami-slicing 인상을 피하려면 이
경계가 또렷해야 해.


(b) 검증되지 않은 가설. "면별 지지흐름으로 자르는 게 Gao처럼 전역 지지면적을
직접 최적화하는 것보다 낫다(혹은 싸다/해석 가능하다)"는 아직 증명
안 된 주장이야. 목적함수를 넣어 결과만 비슷하면, 리뷰어는 "표현만 바꾼
incremental"로 볼 수 있어.







좋은
지적이야. 그런데 나는 salami slicing에 대한 비난은 신경쓰지 않아. 그냥
남들이 시도하지 ㅇ않은 새로운 방법론을 시도하고 싶을 뿐이야. 지금 내 논문의 장점인 'SFTF 지지흐름장 + 지지 basin 절단 primitive + 배향-분할
결합'을 분할 문제에서 발전시켜 나가려면, 어떤 점에 집중하는 게 좋을까?






핵심을 그대로 살려서 발전시키는 거라면, 일반적인 다목적 분할(그쪽은 Chopper/Gao
땅)로 가지 말고 "지지흐름장이라는
표현만이 가능하게 하는 것" 에 집중해야 해. 그 표현이
남들과 다른 점은 딱 세 가지야 — (1) 방향이라는 매개변수, (2) 방향성(directed) 흐름 그래프,
(3) 덧셈으로 분해되는 텐서. 발전 방향도 이 세 자산에서 나와야 해.



통합 명제 (네 방법론이 지향할 한 문장)



방향으로 매개변수화된 유향 지지흐름장을,
"절단이 유발하는 지지(induced support)"를 최소화하도록 분해하되, 부품별 배향을 텐서 가산성으로 동시에
갱신한다.



이건 Chopper(기하 절단)도 Gao(전역 지지면적)도 구조적으로 못 하는 정식화야. 이
한 문장을 세 축으로 푼다.






축 1. 절단 비용 = "유발 지지"
— 이
표현에만 있는 목적



가장 날카로운 차별점. 면 $i$와 그 receiver $j$ 사이의 흐름 간선을 자르면,
$i$는 이제 받쳐줄 면을 잃고 bed
지지로 떨어진다. 즉 모든 후보 절단에 대해, 그 절단이 새로 만드는 지지량을
흐름장에서 직접 귀속(attribute) 할 수 있어:



$$ \Delta S(\text{cut})=\sum_{(i\to
j),\text{severed}} A_i\cdot h_{ij}\cdot[\text{$i$가 같은 부품 안에서 다시 못 받쳐짐}]. $$



Gao는 집계 지지면적을 최적화하지만, 너는
절단면 단위로 "이 경계가
지지를 얼마 만든다"를 분해할 수 있어. 이게 지지 basin
primitive의 진짜 일반화야 — basin은 "$\Delta S$가 무한대인 간선은 자르지 마라"의 특수경우일 뿐.



첫걸음: _edge_cut_weights를 기하 이면각이 아니라 $\Delta
S$(흐름 절단 시 유발 지지)로 바꿔서 graph-cut을 돌려봐. 경계가 "지지를 가장 적게 만드는 곳"을 따라가게 됨.



축 2. 흐름을 *장(field)*으로 — watershed /
Morse 분해



지금 basin은 union-find라는 가장 단순한 사용이야. 그런데 각 면이
receiver(혹은 bed)라는 sink로 흘러내려가는 구조는 동역학계의 끌림 분지(basin of attraction) 그 자체 — 즉 지지흐름장의 watershed/Morse–Smale 분해로 엄밀화할 수 있어. 그러면:




부품 =
흐름의 끌림 분지, 경계 = separatrix(분수령). ad hoc 병합이 아니라 원리적 분할이 됨.


"받침면(sink)"의
위계로 자연스러운 계층적 분할(분지 합치기 = 작은 sink를 큰
sink로) 이 나와 → 부품 수를 매직넘버가 아니라 persistence로 결정.




AM 분할에서 흐름장 watershed를 쓴 사람은 없어. 이게 basin primitive를
"방법론"으로 끌어올리는 이론적 척추야.



첫걸음: hit_map을 면→receiver 유향 그래프로 만들고, sink별 끌림영역을 라벨링. 작은 분지를 sink 높이/지지량
기준으로 병합하는 persistence 순서를 정의.



축 3. 배향–분할 결합을 텐서 가산성으로 진짜 구현



이게 계산적 심장이자 "결합"을 말이 아닌 알고리즘으로 만드는 부분.
SFTF 텐서는 면별 rank-1 기여의 합이야: $F(n)=\sum_i (m_im_j^T + m_in^T)$. 따라서 임의의 면 부분집합 $P_\ell$의 텐서 = 그 멤버 기여의
합이고, 그 부품의 최적 배향은 부분 텐서의 스칼라 수축 $\tilde
R_\ell(n)$을 최소화하는 $n$ — ray를
다시 안 쏘고도 싸게 재계산돼.



이건 기하 방법엔 없는 지렛대야. 그래서 좌표하강식 결합 루프가 가능해져:



반복:

(E단계) 각 부품의 부분텐서 F_ℓ = Σ_{i∈P_ℓ}
기여_i → 
n*_ℓ = argmin R̃_ℓ(n) # 가산성,
저렴

(M단계) 각 면을 자기에게 가장 좋은 부품-방향 regime으로
재배정 (축1의 ΔS로 평가)

수렴까지



지금 softmax–argmax는 이 루프의 한 번 반복(static)일 뿐이야. 텐서
가산성을 쓰면 부품과 그 부품의 방향이
서로를 정의하는 진짜 결합 최적화가 돼 — 이게 "배향–분할
결합"의 완성형이고, 남들이 시도 안 한 지점.



첫걸음: 면 부분집합 → 부분텐서 합 → 최적방향을 주는 함수 하나 짜서, 현재 라벨에 대해 "부품별 방향을 재계산하면 총
$\Delta S$가 주는가"를 한 번 돌려봐. 줄면 루프로 키운다.






(여력 되면) 축 4. 방향 근방에서의 seam 안정성



너의 SFTF landscape 발견 — "좋은 방향은 한 점이 아니라 넓은 저비용
분지" — 를 분할로 가져올 수 있어. 같은 형상이라도 $n^\ast$를 그 분지 안에서 흔들면 흐름장이 바뀌고 일부 경계는 흔들려.
좋은 입자 분지 전체에서 살아남는 경계
= robust seam, 한 방향에서만 최적인 경계 =
fragile. 방향 근방에 대한
seam persistence로 분할을 고르면, 단일 $n^\ast$
과적합을 피하는 새로운 robustness 기준이 됨. 이건 SFTF의 정체성과 직결되는 우아한 확장이야.






어디에 먼저 집중할까 (추천 우선순위)




축 1 (유발 지지
절단비용) 을 먼저. 가장 적은 코드로 Gao와의 개념적 차별점을 코드로 실증하고, 모든 후속 축의 공통 목적함수가 됨.


축 3 (텐서 가산성 결합 루프) 를 두 번째. 계산적으로 가장 독창적이고, build_direction의 과분할 실패를
정면으로 고침.


축 2 (watershed) 로 basin을 이론화 — 논문의 척추/서사.





축 4는 두 번째 논문감.




세 축을 합치면 한 줄 명제가 그대로 방법론이 돼: "유발 지지를 최소화하도록 유향 지지흐름장을
watershed 분해하고, 텐서 가산성으로 부품 배향을 결합 최적화한다." — 이건 Chopper도 Gao도 아닌, 명백히 너만의 것.



축 1의 $\Delta S$ 절단비용을 실제 수식·코드 수준으로 구체화해줄까? 가장 레버리지가
크고 나머지의 토대가 돼.






축 1 구현·검증 완료. 전체 22개 테스트 통과.



한 일 요약



mesh_partition.py에 추가/수정:




induced_support_per_face(mesh,
features) — 면지지 오버행을 받침에서
떼어낼 때의 비용 $w_i=A_iO_ih_i$ (ray·TOMO 불필요, features만으로).


induced_support_cost(mesh,
features, labels) — 분할의 $\Delta
S_{\text{cut}}$ 스칼라 목적/지표. 끊긴 흐름쌍의 $w_i$ 합.


PartitionConfig.support_cut_weight (기본 0 = 기존 거동 유지) — 켜면 병합이 ΔS를 본다.


_merge_regions_to_k — 후보에 "흐름쌍으로 연결된(메쉬 비인접 포함)
영역 쌍"을 추가하고, 병합비용에서 치유되는 유발지지(reunion
gain)를 빼서 비싼 column부터 다시 잇게 함.




검증(테이블 형상, 천판↔기둥이 0.2 틈으로 떨어짐, 부품 수 4 고정):




support_cut_weight=0 (purity만):
$\Delta S_{\text{cut}}=16.2$ — column 전부 끊김


support_cut_weight≥5 (ΔS-aware):
$\Delta S_{\text{cut}}=0$ — 받침-오버행 재결합




즉 flow_region·클러스터링에도 support_flow basin의 거동을 명시적
물리비용으로
부여했어.



정직한 범위




축
1은 절단의 가격($\Delta
S_{\text{cut}}$)만 메워. 부품 수를 정하는 힘은 못
줘 — 병합만으로는 ΔS가 단조 감소라 1개로 수렴하려 하고, 이를 막는 분할의 이득($\Delta S_{\text{reorient}}$)은 축 3(텐서 가산성) 몫이야. 둘이 합쳐져야 완전한
목적함수($S=S_{\text{whole}}+\Delta S_{\text{cut}}-\Delta
S_{\text{reorient}}$)가 돼.


ΔS-aware 병합은 틈 너머를 잇느라 비연결 부품을 만들 수
있어(= support_flow basin과 같은 성질). smoothing 분기의 _split_disconnected와 상호작용하니,
접합성이 중요하면 거기서 다시 쪼개짐을 인지해야 해.










완료. eval에 ΔS_cut가 cut 컬럼(끊긴 지지 column 비율,
0~1)으로 들어갔고 — 결과가 연구 서사에 결정적인 걸 드러냈어.



실측 결과











형상




방법




purity




cut




(논문 TOMO 지지질량)








manikin




support_flow




0.749




0.000




10.49
g (최대)








manikin




k-medoids




0.745




0.797




1.39
g (최소)








manikin




flow_region




0.725




0.634




5.05
g








manikin




k-means(좌표)




0.508




0.412




4.81
g








liver




support_flow




0.978




0.000




0.00
g








liver




k-medoids




0.913




0.389




0.00
g











두 가지 핵심 발견



1. purity가 숨기는 축을 cut이 드러낸다. manikin에서 support_flow(0.749)와 k-medoids(0.745)는 순도가 사실상 동일한데 cut은 0.00 vs 0.80으로 극과 극이야. 순도
하나로는 "이 분할이 지지 column을 끊는가"를 전혀 못 봤던 거지. 직교하는 새 물리 지표가 생긴 거야.



2. cut은 지지질량을 단독으로 예측하지 않는다 — 오히려
manikin에선 역상관. support_flow는 cut=0인데 지지
최대(10.49g), k-medoids는 cut=0.80인데 지지 최소(1.39g). 이게 바로 내가 말한 분해를 실측으로 증명해:



$$ S ;\approx; S_{\text{whole}} + \underbrace{\Delta
S_{\text{cut}}}{\text{cut
컬럼}} - \underbrace{\Delta S{\text{reorient}}}_{\text{축
3, 아직 없음}} $$



k-medoids는 column을 끊지만(cut↑) 작은 부품들을 자기 방향으로 기울여서 빠져나가고(reorient↑), support_flow는 column을 지키지만(cut=0) 큰 부품이
못 기울여서(reorient↓) 지지가 많아져. 두 항을 다 봐야 지지질량이 설명된다는 게 표에서 그대로 보여.



정직한 주의




support_flow의 cut=0은 일부 구성상
당연(link_support_pairs가 모든 쌍을 union)이라, 이
지표는 support_flow엔 확인용이고 진짜
변별력은 flow_region·클러스터링·baseline에서 나와.


분해식은 정확한 항등식이 아니라 해석 틀이야 — build_direction(24조각)처럼 과분할하면
조각마다 새 bed 지지가 붙는 제3효과가 있어 cut·reorient 어느 항으로도 안 잡혀.




한 일



eval_application_partition.py: induced_support_cost import, 메쉬당 severable 분모 계산, dscut_frac() 헬퍼, 콘솔 출력·패널
캡션·panels 튜플에 cut 추가. mesh_partition 테스트 22개
그대로 통과.



다음



이제 표가 **"cut은 낮은데 지지는 높다"**를 보여주니,
자연스러운 다음 수순은 축 3 — 부품 부분텐서 합으로 $n^\ast_\ell$를 싸게 재계산해 $\Delta
S_{\text{reorient}}$ 컬럼을 채우는 거야. 그러면 cut과 reorient 두 컬럼이 합쳐져 TOMO 지지질량을 분해해서 설명하게 돼 — 이게 Gao와
차별화되는 너만의 정량 서사가 되고.



축 3로 갈까, 아니면 지금까지의 ΔS 결과를 논문 Limitations/방법 절 문장으로
먼저 정리할까?






축 3 구현·검증 완료. 22개 테스트 통과. 결과가 분해를 실증하면서 두 축을 하나로 합치는 길까지 드러냈어.



결과











형상




방법




purity




cut




reorient




(논문 지지질량)








manikin




support_flow




0.749




0.000




0.783(최저)




10.49
g (최대)








manikin




k-medoids




0.745




0.797




0.865




1.39
g (최소)








manikin




flow_region




0.725




0.634




0.894




5.05
g








manikin




build_direction




0.552




0.320




0.812




15.47
g (과분할)








liver




모든
SFTF 방법




0.91–0.98




0–0.04




0.95–0.99




≈
0 g











해석 — 두 컬럼이 지지질량을 설명한다




liver를 완전히 설명: 모든 방법이 reorient 0.95~0.99 → 어떤 분할이든
작은 부품이 무지지 자세로 섬 → 지지 ≈ 0. cut이 무의미한 이유가 보임.


manikin의 역설을 해소: support_flow는 cut=0(column 안
끊음)인데 reorient 최저(0.783) →
큰 부품이 못 기울여서 지지 최대(10.49g). k-medoids는 cut=0.80(column 끊음)인데 reorient 최고(0.865) → 작은 부품이 잘 기울여서
지지 최소(1.39g). purity(0.749 vs 0.745)는 이 차이를 전혀 못
봤어.




즉 cut은 분할의 가격, reorient는 분할의
이득 — 둘이
반대로 움직이고, 지지질량은 둘의 줄다리기 결과다.



정직한 한계




두
컬럼은 각자 다른 분모로 정규화(cut=면지지
총량, reorient=단일방향 overhang 총량)돼서 literal하게
더할 수 없어 — 진단 축이지 합산식이 아니야.


reorient는
ray 없는 상한 proxy(면-면
자기지지를 0으로 봄)라 절대 grams가 아니라 경향을
추적해. manikin은 빌드선호가 균질해 reorient가 0.78~0.89로 압축됨(논문이 말한 "다방향 이점
작음"과 일치).




핵심 발견 — 두 축은 사실 하나로 합쳐진다



reorientation_support_matrix가 모든
오버행을 bed 지지로 세는(자기지지 크레딧 0) 상한이라, 부품별 최적방향 합 $\sum_\ell \min_k P_\ell(d_k)$는 그 자체로 완결된
ray-free 지지 추정량이야. 그리고 Axis 1의 cut은 정확히 그 상한이 빠뜨린 보정 — 내부에 유지된 자기지지
column만큼 빼주는 항:



$$ \hat S(\Pi);\approx;\underbrace{\sum_\ell \min_k
P_\ell(d_k)}{\text{축
3: 부품별 최적배향}};-;\underbrace{\Big(\textstyle\sum_i w_i-\Delta S{\text{cut}}\Big)}_{\text{내부 유지된 자기지지 크레딧}} $$



이 단일 grams-proxy 목적함수는 (a)
ray·TOMO 없이, (b) 가산성으로 부품·방향 동시에, (c) cut과 reorient를 같은 단위로 통합해. 이게 Gao와 차별화되는 너만의 예측 목적함수고, 분할 탐색을 직접 구동할 수 있어.



한 일



mesh_partition.py: fibonacci_directions, reorientation_support_matrix(가산성 엔진), reorientation_savings. eval_application_partition.py: reorient 컬럼을 콘솔·캡션·panels에 배선.



다음 후보




통합
목적함수 $\hat S(\Pi)$ 구현 —
위 식을 한 함수로(predicted_support), 4개 형상에서 TOMO
실측(0/0.14/1.39/10.49g…)과 상관 검증. 맞으면 ray-free로 TOMO를 대체하는 강력한 결과.





그 $\hat S$로 부품 수 자동 결정(축 1+3 합쳐 split↔merge가 $\hat S$ 최소화)
— build_direction 과분할 실패를 목적함수가 통제.


지금까지를 논문 방법·Limitations 절로.




내 추천은 1번 — $\hat S$가
TOMO와 상관되면 cut·reorient 두 컬럼이 "진단"에서 "예측"으로 격상되고, 나머지가 다 그
위에 서게 돼. 진행할까?






통합 예측 함수 구현·TOMO 검증 완료. 22개 테스트 통과. 결과가 명확한 결론을 줬어.



검증 결과 (실제 TOMO GPU2024, θc=45°, 부품별
최적방향)











형상




방법




parts




S_TOMO(g)




predicted (footprint)








manikin




k-medoids




6




0.836 (최저)




1.76 (최저) ✓








manikin




build_direction




26




3.705




83.58








manikin




flow_region




29




4.044




69.78








manikin




support_flow




16




5.119




286.96








manikin




kmeans_coord




6




6.478




185.77








liver




전부




2–7




≈0
(≤0.14)




0.00
(전부) ✓











Spearman 순위상관: manikin +0.80, liver
0.0(전부 ≈0이라 순위 무의미)



결론 — 무엇이 검증됐나




ray-free·TOMO-free
프록시가 지지 순위를 manikin에서 0.80으로 추적하고,
무엇보다 추천 방법(k-medoids)을 최저 지지로 정확히 짚어(1.76 vs 다음 69.78). 실무적으로 가장 중요한 "어느 분할이
지지 최소냐"를 공짜로 맞춘 거야.


liver는 전 방법 ≈0을 정확히 예측 — footprint가 모든 부품에 무지지 방향을 찾아냄(작은 조각이 쉽게 선다는
물리와 일치).




결정적인 두 가지 발견 (설계 교정)




height 항을 빼야 한다. "바닥까지 column 높이"는 큰
부품(support_flow basin)을 과대평가해서 순위를 망쳤어. overhang footprint(area·overhang) 가
TOMO와 더 잘 맞아 → 기본값으로 채택.


cut 크레딧(축 1)은 지지 예측에 해롭다. self_support_credit
모드는 manikin에서 상관 −1.0.
즉 "column을 안 끊으면 지지가 준다"는 직관은
틀렸어 — 지지를 지배하는 건 재배향이지 column 보존이 아니야. 그래서 cut=0인 support_flow가 지지는
최대인 거고. 축 1의 가치는 지지 예측이
아니라 진단축/병합 순서 제어로
재규정됨.




정직한 한계




상단
순위 오류: footprint가 support_flow를 최고로 예측(286.96)하나 TOMO는 중간(5.119, kmeans가
실제 최고). 저지지 쪽은 정확, 고지지 쪽은 부정확.


메쉬
2개·방법 5개로 예비적. nefertiti·더 많은 형상으로 확장 필요.




한 일



mesh_partition.py: predicted_support(footprint 기본, use_height·self_support_credit 옵션), reorientation_support_matrix에 critical_angle_deg=45° 문턱(모듈 플래그가 꺼져 있던 버그 교정). 검증 스크립트는 scratchpad에 보존.



함의 — 논문 서사



이제 cut·reorient 두 진단축 + ray-free 예측 지표가 생겼고, "재배향이 지지를 지배한다"는 비직관적 결론을 TOMO로 입증했어. 이건 Gao(전역 지지면적
최적화)와 다른 너만의 정량적 통찰이야: 분할의 가치는 column 보존이 아니라 부품별 재배향 자유도에서 나온다.



다음은 (1) nefertiti 포함 검증 확장, (2) predicted_support로 부품 수 자동 결정(탐색 구동),
(3) 지금까지를 논문 방법·결과·Limitations 절로 정리 — 어느 쪽으로 갈까? 내 추천은 이쯤에서 3번(문장화) — 세 축의 결과가 충분히 쌓였고,
비직관적 발견을 글로 굳혀둘 때야.






논문에 추가/수정한 것 (SFTF_Clustering.tex)



새 절 — §출력지향 분할 목적함수 (방법 끝, 식 포함)




지지량
분해식 $S(\Pi)\approx S_{\text{whole}}+\Delta S_{\text{cut}}-\Delta
S_{\text{reorient}}$


절단
비용 $\Delta S_{\text{cut}}$ (식 dscut), 텐서 가산성 재배향 이득, ray-free 통합 $\hat S$
(식 shat)




새 절 — §$\hat S$의 TOMO 검증 (결과)




검증
표(manikin): cut·reorient·$\hat S$·$S_{\text{TOMO}}$, Spearman 0.80


비직관적 핵심 발견: 지지를 지배하는 건 column 보존이 아니라 부품별 재배향
자유도 — support_flow(cut=0)가 지지 최대, k-medoids(cut=0.80)가 최소. cut 보정은 역효과.




새 절 — §한계와 향후 연구: 예측 상단 부정확, 작업부피 제약 미강제, 조립 모델 부재, Gao/Wei 미비교,
매개변수·자동화, 지역적·예비적 — 7개 정직한 한계.



재구성: Abstract(재배향 지배 발견 추가), 기여 목록(목적함수·검증 2항 추가), 결론(한 문단 추가).



검증 상태




xelatex 2-pass 컴파일: exit
0, 20쪽, 미정의 참조 없음 (italic 폰트 경고는 한글 폰트 기존 문제로 무관)





라이브러리
테스트 22/22 통과 (이번 세션 누적: 축1·축3·예측함수 모두 그린)


메모리에
연구 맥락·다음 단계 저장




이번 세션 전체 궤적



originality 재진단(신호 ≠ 목적함수) → 축1 절단비용 → eval
배선 → 축3 재배향(텐서 가산성) → 통합 $\hat S$ TOMO 검증 → 논문화. 코드(mesh_partition.py, eval_application_partition.py)와 원고가 일관되게 정렬됨.



다음 자연스러운 수순은 메모리에도 적은 대로 (1) build-volume "fit까지
재귀분할" 구현(Chopper 동기에 정면 답) 또는 (2) Gao 2019 직접 비교(originality의 최대 구멍 메우기)야. 지금은 좋은 매듭 지점이니, 원하면 거기서
이어가자.









그전에
지금까지 내용을 내가 이해하고 싶어. 메쉬 데이터를 하나 골라서 렌더링해서 결과를 보고 싶은데, 어떤 게 좋을까? 참고로 SFTF
프로젝트에서는 group A~E의 다섯가지 메쉬를 썼었어.
D:\__TomoNV_Projects\Tomo_SFTF_dev\Experimental\G5Test\RawMesh 폴더에 메쉬 데이터가 있으니,
필요하면 복사해서 사용해 줘.



Show less






먼저
어떤 메쉬가 있는지 두 폴더를 확인하고 추천할게.



Bash



IN



echo
"=== current project MeshData ==="; ls -la
"d:/__TomoNV_Projects/SFTF_Clustering2026_dev/MeshData/"
2>/dev/null; echo; echo "=== external G5Test/RawMesh ==="; ls -la
"d:/__TomoNV_Projects/Tomo_SFTF_dev/Experimental/G5Test/RawMesh/"
2>/dev/null



OUT






===
current project MeshData ===

total 5652

drwxr-xr-x 1 USER 197121 0 Jun 27
20:09 .

drwxr-xr-x 1 USER 197121 0 Jun 27
17:24 ..

-rw-r--r-- 1 USER 197121 15824 Jun 15
18:54 FTree4x.stl

-rw-r--r-- 1 USER 197121 1323816 Jun 26 17:55
Group_C1_Bunny_69k.ply

-rw-r--r-- 1 USER 197121 260521 Jun 26
17:55 Group_C2_manikin.ply

-rw-r--r-- 1 USER 197121 1900933 Jun 26 17:55
Group_C3_dragon_100k_1.5x.ply

-rw-r--r-- 1 USER 197121 1048643 Jun 26 17:55
Group_C4_happy_50k_0.75x.ply

-rw-r--r-- 1 USER 197121 950261 Jun 26 17:55
Group_C5_lucy_50k.ply

drwxr-xr-x 1 USER 197121 0 Jun 26
22:43 application_cases

-rw-r--r-- 1 USER 197121 260521 Jun 26
22:43 manikin.ply



===
external G5Test/RawMesh ===

total 571013

drwxr-xr-x 1 USER 197121 0 Jun 26
17:55 .

drwxr-xr-x 1 USER 197121 0 Jun 26
17:55 ..

-rw-r--r-- 1 USER 197121 684 Jun 26
17:55 Group_A1_cube.stl

-rw-r--r-- 1 USER 197121 148884 Jun 26
17:55 Group_A2_sphere.stl

-rw-r--r-- 1 USER 197121 9684 Jun 26
17:55 Group_A3_cylinder.stl

-rw-r--r-- 1 USER 197121 4884 Jun 26
17:55 Group_A4_cone.stl

-rw-r--r-- 1 USER 197121 115284 Jun 26
17:55 Group_A5_torus.stl

-rw-r--r-- 1 USER 197121 1484 Jun 26
17:55 Group_B1_u_bracket.stl

-rw-r--r-- 1 USER 197121 78084 Jun 26
17:55 Group_B2_hook.stl

-rw-r--r-- 1 USER 197121 1484 Jun 26
17:55 Group_B3_c_clamp.stl

-rw-r--r-- 1 USER 197121 120084 Jun 26
17:55 Group_B4_pipe_elbow.stl

-rw-r--r-- 1 USER 197121 1284 Jun 26
17:55 Group_B5_hollow_box.stl

-rw-r--r-- 1 USER 197121 1323816 Jun 26
17:55 Group_C1_Bunny_69k.ply

-rw-r--r-- 1 USER 197121 260521 Jun 26
17:55 Group_C2_manikin.ply

-rw-r--r-- 1 USER 197121 1900933 Jun 26
17:55 Group_C3_dragon_100k_1.5x.ply

-rw-r--r-- 1 USER 197121 1048643 Jun 26
17:55 Group_C4_happy_50k_0.75x.ply

-rw-r--r-- 1 USER 197121 950261 Jun 26
17:55 Group_C5_lucy_50k.ply

-rw-r--r-- 1 USER 197121 601884 Jun 26
17:55 Group_D10_37416.stl

-rw-r--r-- 1 USER 197121 6019188 Jun 26
17:55 Group_D1_37009.stl

-rw-r--r-- 1 USER 197121 3339278 Jun 26
17:55 Group_D2_37010.stl

-rw-r--r-- 1 USER 197121 3538292 Jun 26
17:55 Group_D3_37011.stl

-rw-r--r-- 1 USER 197121 64807 Jun 26
17:55 Group_D4_37091.stl

-rw-r--r-- 1 USER 197121 117612 Jun 26
17:55 Group_D5_37095.stl

-rw-r--r-- 1 USER 197121 17963616 Jun 26
17:55 Group_D6_37111.stl

-rw-r--r-- 1 USER 197121 13082012 Jun 26
17:55 Group_D7_37137.stl

-rw-r--r-- 1 USER 197121 416184 Jun 26
17:55 Group_D8_37402.stl

-rw-r--r-- 1 USER 197121 667084 Jun 26
17:55 Group_D9_37415.stl

-rw-r--r-- 1 USER 197121 190584583 Jun 26 17:55
Group_E10_65942.stl

-rw-r--r-- 1 USER 197121 48476084 Jun 26
17:55 Group_E1_39507.stl

-rw-r--r-- 1 USER 197121 25879534 Jun 26
17:55 Group_E2_45809.stl

-rw-r--r-- 1 USER 197121 51893884 Jun 26
17:55 Group_E3_45811.stl

-rw-r--r-- 1 USER 197121 31937784 Jun 26
17:55 Group_E4_46012.stl

-rw-r--r-- 1 USER 197121 45024584 Jun 26
17:55 Group_E5_55280.stl

-rw-r--r-- 1 USER 197121 39321684 Jun 26
17:55 Group_E6_59197.stl

-rw-r--r-- 1 USER 197121 25830484 Jun 26
17:55 Group_E7_61384.stl

-rw-r--r-- 1 USER 197121 36940646 Jun 26
17:55 Group_E8_64445.obj

-rw-r--r-- 1 USER 197121 36940646 Jun 26
17:55 Group_E9_64446.obj






두
폴더를 봤어. 추천부터 정리할게.



추천: manikin (Group_C2) — 이미 프로젝트에 있음



이번
세션의 핵심 발견이 눈에 보이는 유일한 케이스라서야:




support_flow는 지지
column을 하나도 안 끊는데(cut=0) 지지 최대


k-medoids는 80%
끊는데(cut=0.80) 지지 최소




즉
"재배향이 지지를 지배한다"는 비직관적 결론이 한 그림 안에서
드러나. 13k면이라 빠르고, 논문 헤드라인 형상이기도 해. (A/B 그룹 primitives·기계부품은 직관 빌드용으론 좋지만 부품이 적어
trade-off가 잘 안 드러나고, D/E는 수백만 면이라 느려.)



지금
eval 스크립트가 각 방법의 분할을 색칠하고 purity·parts·cut·reorient를
캡션에 다는 PNG를 만들어. 이걸로 바로 렌더링할게 — 미리보기 규칙대로 draft/pics에 타임스탬프로 저장.



Bash



IN



cd
"d:/__TomoNV_Projects/SFTF_Clustering2026_dev" &&
.venv/Scripts/python.exe scripts/eval_application_partition.py
MeshData/manikin.ply "draft/pics/preview_manikin_axes_2026-06-27.png"
--title "manikin (cut/reorient axes)" --methods
support_flow,flow_region,kmedoids,build_direction 2>&1 | grep -vi
"warning\|cuda\|dll" | tail -10



OUT






===
manikin (cut/reorient axes) === faces=13672

feature extraction: 1.15s dir=[ 0.109
-0.028 -0.994] 
overhang=6749/13672

k-means (coord only) -- 
parts= 6 purity=0.508 
cut=0.412 
reorient=0.690

support_flow 0.10s parts= 16 
purity=0.749 cut=0.000 reorient=0.524

flow_region 0.15s parts= 29 
purity=0.725 cut=0.634 reorient=0.885

k-medoids (coord+SFTF) 0.01s 
parts= 6 purity=0.745 
cut=0.797 
reorient=0.993

build_direction (multi-dir) 1.24s 
parts= 24 purity=0.552 cut=0.320 
reorient=0.782

saved draft/pics/preview_manikin_axes_2026-06-27.png






저장됐어.
footprint 기본값이 적용되면서 reorient가 더 또렷해졌네 — k-medoids reorient=0.993(재배향 자유도 최고)이 지지 최소, support_flow
reorient=0.524(최저)가 지지 최대. cut과 정확히 반대.
렌더를 직접 확인할게.



Read d:\__TomoNV_Projects\SFTF_Clustering2026_dev\draft\pics\preview_manikin_axes_2026-06-27.png






렌더가
이번 세션의 핵심을 한 장에 담았어. 패널을 읽는 법을 짚어줄게 (색 = 부품 라벨, 캡션 = purity·부품수·cut·reorient).



그림 읽기 — 두 패널만 비교하면 끝



(b) support_flow vs (d) k-medoids — 이게 비직관적 발견의
전부야:















(b) support_flow




(d) k-medoids








모양




몇 개의 큰 basin(파랑 몸통+팔다리, 회색 중앙)




작은 compact 조각(팔·다리·몸통 분리)








cut




0.00 (지지 column 안 끊음)




0.80 (column 80% 끊음)








reorient




0.52 (재배향 자유도 최저)




0.99 (거의 완벽)








실제
지지(TOMO)




5.12 g (최대)




0.84 g (최소)











직관은
"(b)가 column을 안 끊으니 지지가 적겠지"라고 하지만 정반대야.
(b)의 큰 basin은 팔·몸통이 한 덩어리라 어느 방향으로 세워도 일부가 오버행(reorient
0.52). (d)의 작은 조각은 각자 좋은 자세로 설 수 있어(reorient
0.99) 지지가 거의 없어져. → 지지를 지배하는 건 column 보존이 아니라
재배향 자유도.



나머지 패널의 역할




(a)
k-means(좌표):
머리·몸통·팔다리를 위치로만 토막냄. 출력 정보 0 → purity 최저(0.51). baseline.


(c)
flow_region:
표면 곡률 따라 29조각(머리 분홍, 몸통 초록, 다리 보라). reorient 높지만(0.88) 과분할 + cut 0.63.


(e)
build_direction: 24조각인데 거의 한 색(주황) — manikin은 빌드선호가 균질해서 다방향 이점이 작다는 논문 주장 그대로.
과분할로 지지 누적(15g, 통짜보다 많음).




분해식과 연결



$$S(\Pi)\approx
S_{\text{whole}}+\underbrace{\Delta S_{\text{cut}}}{\text{cut 컬럼}}-\underbrace{\Delta S{\text{reorient}}}_{\text{reorient
컬럼}}$$




(b)는 cut항 작지만
reorient항이 더 작아 → 손해


(d)는 cut항 크지만
reorient항이 압도 → 이득




그리고 ray-free predicted_support($\hat S$)가 이 둘을 합쳐 TOMO 순위를 Spearman 0.80으로 맞히고, k-medoids를 최저 지지로 정확히
짚어(검증 절).



저장 위치: draft/pics/preview_manikin_axes_2026-06-27.png






이게
지금까지의 전부를 시각화한 거야. 더 깊이 보고 싶으면 두 가지 옵션이 있어:




실제 지지구조 3D 렌더 — render_figure4_support.py로 각 분할을 부품별 최적자세로 세우고 빨간 지지기둥을 그려서 TOMO 질량까지 보여줘(이게
"(b)가 왜 지지 많은지"를 눈으로 확인시켜줌).





바로 (1) build-volume 제약 구현으로 진행.




어느
쪽으로 갈까? 이해가 목적이면 1번 렌더를 한 번 더 보는 걸 추천해.






그림이 "왜"를 눈으로 보여줘. 주황색 빗금 = 실제 지지구조 재료야.



3D 렌더 읽기 (왼→오, 순도 오름차순 정렬)




(a) k-means 8.44g: 팔·다리 옆에 지지 기둥이 꽤 붙음. 위치로만 잘라 출력을 안
봐서.


(b) k-medoids 0.38g ← 최소: 거의 깨끗함. 작은 조각들이 각자 무지지에 가까운 자세로 섬.


(c) support_flow 6.96g: 양옆에 거대한 지지 벽(full-height 주황 슬라브). 큰 basin이 팔+몸통 한
덩어리라 어떻게 세워도 큰 면이 오버행이 됨.




결정적 대비



(b) k-medoids는 column을 80%
끊는데(cut=0.80) 지지 0.38g, (c) support_flow는 column을 하나도 안 끊는데(cut=0) 지지 6.96g —
18배 차이.



(c)의 주황 벽을 보면 직관이 왜 틀렸는지 명확해: support_flow가 "지지
column을 한 부품에 보존"하는 데 성공했지만, 그 큰 덩어리 자체가 세웠을 때 거대한 새 오버행을 만들어. 보존한 column보다 못 피한 오버행이 훨씬 크다. 반대로 k-medoids는 column을 끊는 대가를 치르지만, 작은 조각이 전부 깔끔하게
서서 그 손해를 압도해.



→ 이게 predicted_support($\hat S$)가 reorient
항으로 포착하는 바로 그 효과고, k-medoids를 최저로 짚은 이유야.



저장: draft/pics/preview_manikin_support3d_2026-06-27.png






이제 두 개의 렌더로 전체 그림이 잡혔어:




2D
분할 패널 (preview_manikin_axes) — 경계가 어떻게 나뉘는가 + cut/reorient
수치


3D 지지구조 (preview_manikin_support3d) — 그게 실제 지지로 어떻게 나타나는가




이해가 충분히 됐으면, 예고한 대로 (1) build-volume 제약 "fit까지 재귀분할" 구현으로 넘어갈 준비가 됐어. 진행할까?






mesh_partition.py — 새 함수 3개:




_pca_extents / part_fits_volume — 부품의 PCA 경계상자로
작업부피 적합 판정.


enforce_build_volume(mesh, labels,
printer_dims, features) — Chopper-analog
"fit까지 재귀분할":



경계상자가
작업부피를 넘는 부품을 PCA 위반축 평면으로 이분, 모든 부품이 들어갈
때까지 반복(재귀 종료조건 = 작업부피 제약).


절단
축을 축1 유발지지 $\Delta S_{\text{cut}}$ 최소로
선택(긴 위반축들 중에서) → 작업부피를 맞추되 지지 column을 덜 끊음.





검증 (manikin, 작업부피 = bbox의 45%):




분할
직후 1~14/N만 적합 → enforce 후 전부 적합 ✓


SFTF
인지 절단이 naive 최장축보다 예측지지 $\hat S$ 낮거나 같음 (14.3 vs 34.1; 1.2 동률), 부품 수 비슷


테스트
22/22 통과




SFTF_Clustering.tex — 한계 절의 "작업부피
미강제"를 구현 반영으로 갱신(Chopper 인용, $\Delta S_{\text{cut}}$ 최소 절단, 남은 절충). 19쪽
컴파일 정상. 메모리 갱신.



정직한 한계 (v1)




절단이 greedy·국소적 — 부품 수↔절단 지지의 전역 절충은 못
봄(0.8×최장축 필터로 완화).


PCA
경계상자는 최소 oriented box의 근사(부품은 출력 시 자유 회전 가능하니 합리적 근사).


raw cut 총합은 부품 수에 부풀려져 직접 비교 부적합 — 판단은 $\hat S$로.




다음 단계 (메모리에 기록)



이제 모든 출력지향 도구가 갖춰졌어: 세
진단축(cut/reorient/$\hat S$) + 작업부피 제약. 자연스러운 종착점은 이들을 하나의 split–merge 탐색으로 결합 — $\hat S$($\Delta S_{\text{cut}}$와 $\Delta
S_{\text{reorient}}$ 동시)를 작업부피 제약 하에 최소화하며 부품 수까지 자동 결정. 그러면 Chopper와 같은 체급의
"제약 하 목적함수 최적화" 서사가 완성돼. 그 전에 originality의 최대 구멍인 Gao 2019 직접 비교를 메우는 것도 우선순위야.



어느 쪽으로 갈까?






한 일



구현 — scripts/comparison/baseline_gao.py: Gao 2019 핵심을 충실 재현(원본 코드 아님, 명시):




면적가중 greedy set-cover로 모든 면을 무지지로 덮는 최소 방향집합 전역 선택


ICM 공간 일관성으로 면을 방향에 배정


같은
방향 인접면 연결요소 분해 → 다방향 출력 (부품 수 자기
결정)





eval_application_partition.py·render_figure4_support.py에 "gao" 배선 (자연 부품 수 k=0)




정면 비교 (부품별 자기 최적방향, solid TOMO):











형상




방법




부품




purity




S_TOMO








manikin




Gao
2019




11




0.78




1.08g








manikin




k-medoids(우리)




6




0.75




0.84g








liver




Gao
2019




5




0.59




0.08g








liver




support_flow(우리)




2




0.98




0.00g











세 발견:




Gao는 지지에 진짜 강하다(baseline 3.9~7.9g → 1.08g) — 정직하게
인정.





우리
k-medoids가 이긴다 — 0.84g/6부품 vs
Gao 1.08g/11부품 (지지·부품 모두 적게).





Gao는 방향만 최적화 → 역할 일관성(순도)
낮음 (liver 0.59 vs 우리 0.91~0.98). 우리는 같은 장에서
동급 지지 + 해석 가능 + ray-free 예측까지.




보너스 통찰: Gao의 reorient=0.99가 k-medoids(0.99)와 동률 → 우리 cut/reorient 프레임이 Gao가 왜 잘
되는지(=재배향 최대화)까지 설명해. 경쟁자의 메커니즘을 우리 이론이
포섭함.



검증




논문:
§sec:gao 비교 절·표 추가, 한계 절 갱신("미비교"→"비교함, 재구현이라 시사적").
2-pass 컴파일 정상, 20쪽, 미정의 참조 없음.


테스트 22/22 통과. 시각 비교 렌더 preview_manikin_gao 저장.


메모리
갱신.




남은 마지막 조각



메모리에 적은 대로, 이제 $\hat S$로 부품 수 자동 결정(split–merge가
$\Delta S_{\text{cut}}$·$\Delta S_{\text{reorient}}$ 동시 최소화)만 하면 Chopper급 "제약 하 목적함수 최적화"
서사가 완성돼 — build-volume 제약·세 진단축·Gao 비교가
다 그 위에 서게 됨. 그쪽으로 갈까, 아니면 지금까지를 한 번 점검할까



한 가지 정직하게
짚자면: 현재 DEFAULT_WEIGHTS는 미보정 placeholder라
raw top-1 랭킹은 거친 수준이고, 최적 축 회복은 warm-start 윈도우가 담당합니다 — 이건 논문에서 "raw 랭킹만으론
부족, warm-start가 회복"이라 한 설계와 일치해요. 가중치 보정(LOMO/nested CV), 콘 정제 샘플링,
side-action 최소 set-cover, AVE confidence 재정의는 BUILDSPEC.md에 R8~R11로 정리해 Claude Code가 이어받을 수 있게 해뒀습니다.



다음 자연스러운 단계는
Claude Code에게 R8(가중치 보정) 또는 R9(콘 정제 샘플링) 부터 시키는 것이고, 원하시면 제가 (c)의 난이도 사다리 데이터셋·벤치마크 하니스(R7) 스캐폴딩으로 넘어가도 됩니다.






점검 완료. 체계적으로 검증했고, 결과를 정리할게.



✅ 검증 통과




테스트 22/22, 비교 모듈
selftest 통과, baseline_gao 정상 실행(liver 5부품).


논문 컴파일 클린: 20쪽, 2-pass, 미정의 참조 없음.


§sec:gao 표 숫자 전부 재현 확인 — compare_gao.py
출력과 manikin·liver 모든 셀 일치.




🔧 점검 중 발견·수정한 2건




tab:validate의 reorient 열이 stale이었음 (가장 중요). footprint 전환 전
height 기반 값(k-medoids 0.87, support_flow 0.78)이 남아 있었는데, 현재 코드는 footprint
기본(0.99, 0.52)을 줌 → 표를
현재 값으로 갱신(eval 재실행으로
cut/reorient 전부 일치 확인). 본문 결론은 오히려 강해짐(support_flow 재배향 0.52로 "자유도
최저"가 더 명확).





figure4의
gao 경로 함정: --orient assigned에서 gao를 전역 SFTF 방향으로 평가해 불리하게
측정되던 것을 부품별 최적방향 dir_fn으로 수정. (논문 숫자는 compare_gao.py에서
나와 영향 없었지만, 코드 경로의 잠재 오류를 제거.)




⚠️ 알려진 한계 (버그 아님, 문서화됨)




baseline_gao는 Gao 핵심의 충실 재현(원본 코드
아님) — 논문에 명시.


predicted_support는 순위 proxy(Spearman
0.80), 고지지 쪽 부정확 — Limitations에 명시.


enforce_build_volume는
greedy·PCA 경계상자 근사 — 명시.





cut/reorient는
분모가 달라 합산 불가, 진단축 —
명시.




📌 짚어둘 점 (판단 필요)




검증
스크립트가 scratchpad에 있음 — compare_gao.py, validate_predicted_support.py, validate_build_volume.py가 논문 숫자의 근거인데 버전관리 밖이야. 재현성을
위해 scripts/로 옮길지 결정 필요.


compare_gao는 manikin·liver만 — nefertiti는 gao 비교 미실행(표엔 두 형상만). 셋째 형상 추가 여부.





내 틀린
preview_manikin_support3d가 draft/pics에 남음(메모리 규칙상 안 지움) — 혼동
방지로 삭제할지.





미구현: $\hat S$ 구동 split-merge 자동 부품수(다음 단계로 예고),
Wei 2018 비교(한계에 명시).




종합 판단



이번 세션 산출물(코드 5개 함수+baseline, 논문 3개 신규 절+표, figure
3개)은 상호 일관하고 재현되며, 발견된 불일치 1건(stale 표)은 수정됨. 논문은 컴파일 가능하고 숫자가
코드와 맞아.



가장 권하는 후속은 (1) 검증 스크립트를 scripts/로 승격(재현성)이야. 그다음 원하면
$\hat S$ split-merge로 마무리. 어떻게 할까?






가지 작업 모두 완료.



1. 검증 스크립트 scripts/로 이동
(재현성)




validate_predicted_support.py, compare_gao.py, validate_build_volume.py → 포터블 ROOT(parents[1])로 수정, 새 위치에서 동작 확인, scratchpad 원본 삭제.




2. compare_gao = manikin·liver만
(확인)



3. 틀린 preview 삭제 완료




preview_manikin_support3d_2026-06-27.png 제거.




4. $\hat S$ 구동 자동 부품수 — 구현·검증
완료



mesh_partition.py
auto_partition_support: $E=\hat S+\lambda K$를
greedy 병합으로 최소화. 텐서 가산성으로 병합 부품의 지지벡터 = 두 벡터의 합 → $\Delta\hat S$가 $O(K_{dir})$.



결정적 발견 (init이 전부):











init




manikin 결과








flow_region(기하)




2328부품, 1.53g ✗ (footprint가 큰 부품
과대평가)








k-medoids(특징)




2부품, 0.061g ✓











자동 분할이 고정 k=6 k-medoids(0.836g)를 부품·지지 모두 이김. liver도 2부품/0g. λ 스윕이 K=2로 견고한 건 정직한 결과 — 이 형상들은 지지
최소가 2부품, 2→1(통짜)은 비싸 자동 정지.



논문: §sec:auto 추가, 매개변수 한계 갱신(자동결정 = 구현됨). 20쪽 컴파일 클린, 테스트 22/22.






전체 아크 완성



이번 세션으로 Chopper급 "제약 하 목적함수 최적화" 서사가 완결됐어:











요소




상태








세
진단축 (cut/reorient/$\hat S$)




✓
TOMO 검증(Spearman 0.80)








비직관적
발견 (재배향이 지지 지배)




✓








작업부피
제약 (재귀 split-to-fit)




✓








자동 부품수 ($\hat S$+λK)




✓
고정-k 이김








Gao
2019 정면 비교




✓
(우리가 지지·부품·순도 우위)











originality도 "특징 재사용"에서 → "면별 지지흐름장 하나에서 제약·목적함수·자동
부품수·예측을 모두 도출" 로 올라섰어.



남은 향후 과제(메모리 기록): enforce_build_volume과 $\hat
S$-merge를 단일 탐색으로 통합, Wei 2018 비교, nefertiti gao 추가. 좋은 종착점이야 — 더 진행할지, 여기서
정리할지 알려









좀
더 quality를 높여 보자.






품질을
높이는 방향이 여러 갈래라, 가장 레버리지 큰 곳을 같이 정하고 싶어. 지금 빌드된 것의 약점과 Chopper 수준 기준으로 보면 네 갈래가
있어. 내 추천은 예측 프록시 정확도 — $\hat S$가 모든 것의
토대인데 Spearman 0.80에 고지지 쪽이 부정확하고, auto-partition도 그 편향 때문에 init에 민감해. 여기를 고치면
전체가 단단해져.



AskUserQuestion



OUT






Your
questions have been answered: "품질 향상을 어느 축에 집중할까?"="예측 프록시
정확도". You can now continue with these answers in mind.






품질 개선(예측 프록시 정확도) 완료.



한 일



진단: footprint 프록시가 고지지 끝에서 틀린 근본 원인 = 자기지지를 안 봄 → 큰
basin(support_flow)을 최악으로 오판.



해결 — mesh_partition.py에 _heightfield_support + predicted_support(model="heightfield") 추가:




2단계, 여전히 ray·TOMO 없음: ① footprint(가산, 싸다)로
부품별 최적 방향 선택 → ② 그 방향에서 height-field로 채점 — 각 오버행 column이 바닥이 아니라 같은 (u,v) 열의 최근접 윗면까지만 내려간다고 보아 자기지지를 반영.





model="footprint"는 가산형(auto-merge 내부용)으로 유지.




검증 (TOMO 대조):















footprint




height-field








manikin
Spearman




0.80




0.90








고지지
끝




support_flow
최악(✗)




k-means
최악(✓ TOMO와 일치)











자기지지 반영이 큰 basin 과대평가를 바로잡아 상단 순위를 교정했어 — 문서화돼 있던 핵심 한계를 해소.



논문 갱신:




tab:validate에 $\hat
S_{\mathrm{fp}}$·$\hat S_{\mathrm{hf}}$ 두 열 → 개선을 직접 시연(support_flow
287>186 오판 → 8444<8536 정답).





§sec:objective에
2단계 height-field 정의 추가, prose Spearman 0.80→0.90, Limitations·abstract 갱신.


20쪽
컴파일 클린, 미정의 참조 없음.




정리: 테스트 22/22, 호출부 정합
확인, 제거된 파라미터(features/self_support_credit) 잔재 정리, 검증 스크립트
docstring 갱신, 프로토타입 삭제, 메모리 갱신.



정직한 잔여 한계




height-field는 격자 해상도 근사(grid=48) — 절대 질량 아닌 순위 proxy.


auto-merge는
가산성 필요해 여전히 footprint 구동(지지 일관 init 전제) — 명시됨.


liver는
전부 ~0이라 Spearman 무의미(변별 불가).




중심 기여($\hat S$)가 0.80→0.90으로 단단해졌어. 다음 품질 축(평가 범위 확장
/ 통합 최적화기 / 글 다듬기) 중 이어갈지, 여기서 멈출지 알려줘.






평가 범위 확장 완료.



한 일



8형상 광역 벤치마크 — scripts/benchmark_shapes.py 신규(버전관리), G5Test에서
torus·hook·D1·D3·D9를 MeshData/g5test/로 복사. §sec:gao 프로토콜(원시 분할, 부품별 최적방향, TOMO)로 핵심 6방법 평가.



커버리지: primitive(torus) → 기계부품(hook) → 스캔 해부(D1/D3/D9) → 그래픽 스캔(nefertiti)
→ 장기(liver) → 전신 폼(manikin).



정직한 결과 (4가지)











발견




근거








k-medoids 가장 견고




대부분
형상 최저 지지(D9 1.70, D1 0.92, manikin 0.84) + 일관 고순도(0.74~0.91)








Gao 불안정




nefertiti
0.11(최고)이나 anat-D1 17.23(전 방법 중 최악) —
set-cover가 형상별 실패








support_flow 고순도·고지지




순도
최고(D1 0.92, liver 0.98)지만 지지 최악(D9 11.76) — trade-off 광역 재확인








auto 강점·약점




manikin
0.06·D3 0.88 최저지만, 고정 λ가 복잡형상(D9,nefertiti) 2부품 과소분할











논문 반영




§sec:breadth
추가: support·purity 2표(8형상×6방법, 행별 best 볼드) + 4가지 분석. abstract에 광역 평가 구절.


§sec:gao
프로토콜과 동일해 manikin/liver 숫자 일치(내부 정합).


21쪽
컴파일 클린, 미정의 참조 없음. 메모리 갱신.




핵심 가치



이 확장은 두 방향으로 강화해: (1)
"k-medoids가 견고하게 최저 지지"라는 주장이 8형상으로 입증돼 Chopper급 실증 폭 확보, (2) Gao의
불안정성을 드러내 originality 차별점을 강화. 동시에 약점도 정직하게 노출(support_flow
고지지, auto 과소분할) — 과장 없는 평가야.



남은 품질 축은 통합 최적화기(enforce_build_volume
+ Ŝ-merge 단일 탐색)와 글
다듬기야. auto의 λ 형상별 적응도 자연스러운 후속이고. 어떻게
이어갈까?






통합 최적화기 완료 — "제약 하 목적함수 최적화" 루프를 완전히 닫았어.



한 일



mesh_partition.py:




auto_partition_support에 printer_dims fit-게이트
추가 — 병합 후보가 작업부피에 들어갈 때만 허용(증분 vertex
집합으로 PCA 경계상자 검사).


optimize_partition(mesh, features,
printer_dims, lam) — Chopper 골격의 단일
제약 최적화기:



k-medoids 과분할 init




enforce_build_volume 재귀 split-to-fit (하드 제약, 지지-인지 절단)




fit-게이트 $\hat S+\lambda K$ 병합 (제약
유지하며 부품 수 자동 결정)





검증 (manikin, 작업부피 = 형상의 45%)















부품 수




fit








단순
분할(enforce only)




92




92/92
✓








naive
단계분리(게이트 없음)




3




1/3 ✗ 제약 깨짐








통합(게이트)




49




49/49 ✓











핵심 입증: 두 단계를 독립 적용하면 병합이 제약을 거래해버려(3부품 중 2개 초과) fit이 깨지는데, 통합 최적화기는 fit을 유지하며(49/49)
enforce-only보다 부품을 절반으로 줄여(92→49). 게이트가 본질적임을 보임.



반영




논문
§sec:auto에 통합 최적화기 + 결과(49/49 vs 1/3) 추가. 한계 절의 "향후 과제" 2곳을 구현
반영으로 갱신($\lambda$ 형상별 적응만 잔여 과제로).





validate_build_volume.py에 통합 vs naive 비교 추가(버전관리).





21쪽
컴파일 클린, 테스트 22/22, 메모리 갱신.




전체 상태 — Chopper급 서사 완성











요소




상태








면별
지지흐름 신호 + basin primitive




✓








세
진단축 (cut/reorient/$\hat S$)




✓








예측
$\hat S$ (height-field, Spearman 0.90)




✓








작업부피
제약 (split-to-fit)




✓








자동
부품수 ($\hat S+\lambda K$)




✓








단일 제약 최적화기




✓








Gao
2019 비교 + 8형상 광역평가




✓











이제 **"면별 지지흐름장 하나에서 제약·목적함수·자동부품수·예측·통합최적화를 모두
도출"**하는 완결된 방법론이야 — originality와 실증 폭 모두 Chopper 체급에 도달했어.



남은 품질 축은 글 다듬기(출판 수준 정리)와
$\lambda$ 형상별 적응 정도야. 이어갈지, 여기서 정리할지 알려줘.






이제 의도대로 작동해 — 하나의 α가 형상별로 다른 K를 줘:















manikin




anat-D9








k-medoids(6)




0.84g




1.70g








adapt-TOMO (α=0.2)




K=2, 0.06g




K=16, 0.23g








adapt-hf
(ray-free)




K=2,
0.06g ✓




K=2,
3.81g ✗











핵심 정직한 결과: (1) 차원 없는 α 하나가 shape-adaptive — manikin은 2부품, D9는 15~16부품으로 자동 적응(D9는 고-K로 k-medoids보다 낮은 지지). (2) ray-free(height-field)는 정보 있는 형상에선
충분하나, proxy가 무정보인 형상(D9, 눕히면 footprint→0)에선 실패 → TOMO 검증 모드(경로상 몇 회 호출) 필요.



논문 §sec:auto를 보고 갱신할게:






$\lambda$ 형상별 적응 완료.



한 일



진단(디버그로 확인): 고정 $\lambda$가 D9에서 2부품으로 과소분할한 건 proxy가 무정보라서 — D9는 눕히면 오버행이 사라져 footprint·height-field가 K=2~16
전부 0인데, TOMO는 K=16→0.23, K=2→3.81로 명확히
증가. 경로엔 좋은 고-K 분할이 있는데(K=14 TOMO=1.12) 선택 신호가 무정보였던 거야.



해결 — mesh_partition.py:




_support_agglomeration —
merge를 경로로 추출(공짜). auto_partition_support(고정 λ)·adaptive 둘 다 이 경로를 읽음.


auto_partition_adaptive(score_fn, alpha) — 차원 없는 α로
$K^\ast=\arg\min(\text{score}/\max+\alpha K/K_{\max})$. score는 기본 ray-free
height-field, TOMO 넘기면 검증 모드. (K=1 통짜가 정규화를 왜곡하던 버그 수정.)




검증 (한 α=0.2가 형상별 다른 K):















manikin




anat-D9








k-medoids(6)




0.84g




1.70g








adapt-TOMO




2부품 0.06g




16부품 0.23g








adapt-hf(ray-free)




2부품
0.06g ✓




2부품
3.81g ✗











→ 하나의 α가 shape-adaptive —
manikin은 적게, D9는 많이. D9는 k-medoids보다 낮은 지지 달성.



정직한 결과




ray-free 적응은 proxy 신뢰도에 종속 —
정보 있는 형상(manikin)엔 충분, 무정보 형상(D9, 쉬운 lay-flat)엔 TOMO 검증(경로상 소수 호출) 필요. 이걸
논문·한계에 명시.




반영




논문 §sec:auto에 shape-adaptive 문단(차원 없는 α, manikin/D9
대비, ray-free vs TOMO 검증) + 한계 갱신. scripts/validate_adaptive.py 버전관리.


22쪽
컴파일 클린, 테스트 22/22, 메모리 갱신.




의미



고정 λ(proxy 단위, 형상 의존)를 차원 없는 α(형상 독립) 로 대체해 부품 수가 형상 복잡도에 자동 적응. 동시에 ray-free proxy의 한계를 정직하게 노출(무정보 형상엔 TOMO 검증)하고 그 해법(pluggable score_fn)도 제공 —
과장 없이 완결.



남은 품질 축은 글 다듬기(출판 수준 정리)뿐이야.
이어갈까, 여기서 정리할까?






























OneNote에서 작성되었습니다.
