# SFTF 퀄리티

Source: `D:\__SFTF_Projects(2026)\_dev_notes\SFTF 퀄리티.mht`

SFTF 퀄리티









2026년 6월 20일
토요일



오후 6:53









결론부터: 현재 상태로는 IF 3~4점대가 현실적



가장 완성도 높은 메인 논문(Support_Flow_Tensor_Field_With_BuildPlate) 기준입니다. 나머지 두 편은 아래에서 따로 다룹니다.



적합한 타깃 (IF 3~4, 현재 상태로 투고 가능):




Rapid Prototyping Journal (IF
~3.5) — 주제 정합성 최상


International Journal of Advanced Manufacturing
Technology (IF ~3) — 채택 가능성 높음


Computer-Aided Design (IF 34) — 기하/알고리즘 측면 강조 시


3D Printing and Additive Manufacturing (IF
~3)




왜 그 위(IF 6~12)로 바로 못 가는가



이 논문의 가장 큰 약점은 본인이 이미 정직하게 드러내 놓았다는 점입니다 (§7 ablation). 이게 양날의 칼입니다.




간판
novelty(텐서)가 정작 예측력에 기여하지 않음. Table
7~8에서 $P, S, \sigma_1$ 등 비대칭 텐서 파생 항은 평균 상관이 음수이고, 예측력의
대부분이 build-plate penalty $B$와 ray-casting 가시성에서 나옵니다. 즉 "Support Tensor
Field"라는 제목의 수학적 핵심이 결과를 설명하지 못합니다. 심사자가 반드시 짚습니다. → 텐서를 간판으로 둘지,
"fast build-plate + visibility 기반 후보 생성기"로 리프레이밍할지 결정해야 합니다.


정확도 자체는 평범. best-of-3 ratio가 LOMO 평균 2.37 — 선택 방향의 지지체적이 최적의
2.4배. 속도(13~365×)는 강하지만 정확도는 "warm-start용"이라는 포지셔닝에 의존합니다.


물리 검증 부재. 실제 프린트나 상용 슬라이서(Cura/Prusa) 지지량 비교가 없고 TOMO_INT3
proxy만 씁니다. IF 6+ 저널(Journal
of Manufacturing Processes ~6, Virtual and Physical Prototyping ~10, Additive Manufacturing ~11)은 거의
예외 없이 실측을 요구합니다.


벤치마크가 작고(Stanford 5종) related work가
빈약. Build orientation optimization은 문헌이
매우 두꺼운데 인용이 4개뿐입니다. 최근 방법들과의 정량 비교가 없으면 high-IF에서 바로 reject됩니다.




IF 6~10으로 끌어올리려면




상용
슬라이서 실제 지지량으로 재검증 (proxy 탈피)


기존
published orientation 방법 2~3개와 직접 비교 (현재 PCA/Support Tensor만)


벤치마크를
Thingi10K 수십 개로 확장 (D그룹 채우기 — 이미 자리는 잡혀 있음)


텐서
서사 재정립 또는 텐서가 실제로 이기는 케이스 발굴




나머지 두 편




Support_Tensor_Theory (영문) — 실험이 "Experimental Design"으로만 있고 결과가
없습니다. 현재로선 SCI 저널 불가, 워크숍/short paper 수준. 메인 논문에 흡수시키는 게 낫습니다.


SFTF_Clustering —
purity 0.51→0.87 향상은 명확한 셀링 포인트지만 "예비 실험(preliminary)"이라고 본인이
명시했고, 약속한 build-direction 재검증(§결론 (i))이 빠져 있습니다. 보강하면 CAD / Computers & Graphics (IF 2.54)급 별도 논문이 됩니다.







직설적으로: 속도 강조 + 정직한 ablation이라는
조합은 IF 3~4에서는 오히려 강점(신뢰성)이지만, 그 위로 가려면 "텐서가 핵심"이라는 현재 프레임을 정리하고 실측
검증을 붙여야 합니다.



원하시면 (1) 메인 논문을 특정 타깃 저널(예: Rapid Prototyping
Journal) 포맷·스코프에 맞춰 다듬거나, (2) 텐서 리프레이밍 방안을 구체적으로 제안하거나, (3) 부족한 related work를
조사해 드리겠습니다. 어느 쪽이 좋으세요?












진단: 데이터가 말하는 텐서의 실제 위상



§7 ablation을 그대로 읽으면 이렇습니다.




스칼라 텐서 불변량(invariants)은 죽었다. $R$(평균
상관 −0.08), $P$(−0.34), $S$(−0.28), $\sigma_1$(−0.21) — 부호가 메쉬마다 뒤집힙니다.
$J=R+P+B$가 nuclear 항 포함 구 목적함수와 완전히 동일하다는
건, 텐서의 특이값 구조가 후보 선택에 0을 기여한다는 뜻입니다.


살아있는 건 두 가지: build-plate penalty $B$(평균 +0.58, 전
메쉬 부호 일관)와 ray-casting 가시성(유효 receiver를 "찾는" 행위 자체).




여기서 함정: 흔한 충동은 "텐서를 살리자"입니다. 하지만 데이터가 허락하는
리프레이밍과 허락하지 않는 리프레이밍을 구분해야 합니다. 고유벡터로 후보를 생성하자는 서사는 금지
— Table 11에서 Support Tensor 고유벡터가 PCA보다도 나쁩니다(lucy 8.67). 그쪽으로 프레이밍하면 본인 데이터에
자기모순입니다.






핵심 통찰: ablation은 텐서를 부정하는 게
아니라, 무엇을 버리면 안 되는지를 증명한다



비대칭 텐서 $F(n)=\sum w_{ij}A_iA_j, m_i m_j^T$의 진짜
novelty는 고유값이 아니라 방향성(directed)
결합 $m_i m_j^T$입니다 — source 법선 ⊗
receiver 법선. 기존 Support Tensor $m_i m_i^T$(대칭)와의 차이가 바로
"흐름(flow)"입니다.



그런데 $n^T F_s n$으로 스칼라화하는 순간 이 흐름 정보가
평균화되어 사라집니다. 즉 ablation이 보여준 건 "텐서가 쓸모없다"가 아니라 "스칼라 불변량으로 환원하면 정보가
파괴된다"입니다. 그리고 이건 정확히
SFTF_Clustering이 면별 특징을 보존했을 때 purity 0.51→0.87로 이긴 이유와 같은 현상입니다. 두 논문이 같은
명제의 양면입니다.



이걸 축으로 세 가지 리프레이밍을 제안합니다.






리프레이밍 A — "Field가 주인공, Tensor는
요약" (가장 안전, 데이터 100% 지지)



제목·서사의 무게중심을 per-face directed support-flow field로 옮깁니다. 텐서는 (i) 기존 Support Tensor와의 수학적 다리이자, (ii)
방향별 regime 분해($R/P/B/$hit, Table 10)를 주는 해석용 요약통계로 격하. 점수는
field의 build-plate·가시성 항에서 직접.




헤드라인
기여: "스칼라 불변량은 흐름 정보를 버린다"를 정량
증거(ablation)로 입증 → 그래서 field/per-face를 써야 한다.


장점:
지금 가진 데이터만으로 100% 정합. 거짓이 한 줄도 안 들어감.


비용:
텐서가 간판에서 부제로 내려감. "Tensor" 단어를 못 버리면 아쉬움.




리프레이밍 B — "Tensor를 고쳐서 살린다: 가상
접지 노드" (가장 야심적, 검증 필요하지만 강력)



텐서가 죽은 진짜 이유를 짚으면: 지배 항인
build-plate $B$가 텐서 밖에 스칼라로 붙어 있어서입니다. 빌드플레이트를 가상 receiver 노드로 텐서에 흡수시키면 됩니다.



플레이트 지지면의 법선은 $+n$이므로, 플레이트로 흐르는 면 $i$의 쌍은 receiver
법선이 $n$인 항 $w_{iP}A_iA_P, m_i n^T$가 됩니다. 그러면 Rayleigh 형의 플레이트 기여는



$$n^T(m_i n^T)n = (m_i\cdot n),(n\cdot n) = m_i\cdot
n < 0 \quad(\text{오버행}),$$



즉 $R(n)=\max(0,-n^TF_sn)$가 자동으로 build-plate 비용을 흡수합니다. 현재 텐서가 실패한 건 가장 예측력 높은 신호를 구조적으로 배제했기 때문이고, 접지
노드를 넣으면 $R$이 예측력을 회복할 가능성이 있습니다.




장점:
부끄러운 ablation을 동기가 분명한 수정안으로
전환. 제목의 "Tensor"가 정당해짐.


비용: 검증 필수. 위 유도는 스케치이고, "통합 텐서
$\tilde F$의 $R$이 실제로 $v_{ss}$와 양의 상관을 회복하는가"를 저장된 grid로 재실험해야 주장 가능.
이건 코드 한 번 돌리면 확인됩니다(GPU 재계산 불필요, 기존 npz 재사용).




리프레이밍 C — "최적화기가 아니라 통합
descriptor" (포지셔닝 전환)



"텐서가 방향을 최적화한다"는 주장을 아예 내려놓고, 하나의 per-direction support-flow
descriptor로 재정의: (a) 비용을 해석 가능한
$R/P/B/$hit regime으로 분해하고, (b) 고속 후보 생성을 구동하며, (c) 다운스트림(메쉬 분할)에 그대로 먹입니다. 가치 =
해석성 + 속도(13–365×) + 재사용성. 정확도 경쟁을 회피.




장점:
정확도 ratio 2.37의 약점을 프레이밍으로 우회. 두 논문을 한 프레임으로 묶음.


비용:
novelty가 "통합/해석"이라 reviewer가 "그래서 새 수학이 뭐냐"고 물으면 약함.







추천: A를 본문 골격으로, B를 헤드라인 기여로,
C를 포지셔닝으로



세 개는 배타적이지 않습니다. 가장 강한 논문은:




포지셔닝(C): 방향성 support-flow field라는 통합 표현.


수학적 핵심(B): 가상 접지 노드로 build-plate를 텐서에 흡수 → 비대칭 통합 텐서 $\tilde
F(n)$. 이게 "왜 기존 대칭 Support Tensor로는 안 되는가"에 대한 깔끔한 수학적 답이 됩니다.


정직한 검증(A): 스칼라 불변량의 실패를 흐름 정보 손실의 증거로 제시하고, 통합 텐서가 그걸 일부 회복함을
보임.




이 조합이면 제목의 "Tensor"가 거짓이 아니게 되고, ablation이
약점에서 서사의 엔진으로 바뀝니다.






다음 한 걸음 (B 검증): 가상 접지 노드를 넣은 $\tilde F(n)$의 $R$이 실제로 $v_{ss}$ 상관을
회복하는지가 이 리프레이밍 전체의 사활입니다. 저장된 TOMO grid + 후보 풀로 30분이면 확인됩니다. 회복되면 → B 중심으로 강하게
가고, 안 되면 → A/C로 안전하게 후퇴.



이 검증 실험을 제가 코드에서 직접 설계·실행해 드릴까요? 아니면 먼저 세 리프레이밍 중
하나를 골라 abstract/intro를 다시 써볼까요?









검증 결과 종합



1. 수학적 identity — 증명 + 수치 확인
(airtight)



$$\tilde R(n)=\max(0,-n^T\tilde F_s n) =
R(n)+B(n),\qquad \max_n|\tilde R-(R{+}B)|\approx 10^{-12}$$



5개 메쉬 전부에서 부동소수점 0. 빌드플레이트 penalty $B$는 ad-hoc 외부 스칼라가 아니라, 가상 접지 노드를 더한
flow 텐서의 Rayleigh 항 그 자체임이 코드로 확정됐습니다.
또한 기존 논문 수치(R=−0.08, B=0.58, J=0.47 평균)를 정확히 재현 → 파이프라인 신뢰성도 확인.



2. Correlation 회복 (Spearman vs
$v_{ss}$)















Bunny




manikin




dragon




happy




lucy




평균








$R$
(기존 텐서)




0.40




−0.33




−0.57




−0.03




0.14




−0.08








$B$




0.50




0.66




0.85




0.29




0.62




0.58








$\tilde R=R{+}B$ (접지 텐서)




0.52




0.65




0.89




0.31




0.62




0.60








$J=R{+}P{+}B$
(현재 목적함수)




0.46




0.26




0.80




0.27




0.57




0.47











→ 죽었던 텐서 Rayleigh 항($R$, −0.08)이 접지 노드를 넣자 0.60으로 부활, 단일 feature 중 최고이며 현재 J(0.47)보다도 높습니다.



3. best-of-3 ratio (방향 선택 정확도, 낮을수록
좋음)















Bunny




manikin




dragon




happy




lucy




평균(전체)




평균(happy 제외)








$J=R{+}P{+}B$




2.47




3.99




2.01




11.15




2.82




4.49




2.82








$\tilde R=R{+}B$




2.57




2.89




1.70




16.70




2.82




5.34




2.50











정직한 결론: 이건 단순 리네이밍이 아니라 실질
개선이다



제가 처음 우려했던 "정합성만 좋아지고 정확도는 그대로"는 틀렸습니다. 데이터가 더 강한 걸 말합니다:




해로운 항은 텐서가 아니라 $P$였다. $J=R+P+B$의
pair-flow $P$가 음의 상관(−0.34)으로 J를 오염시킵니다. 접지 리프레이밍은 자연스럽게 $P$를 떼고 **단일 텐서 항
$\tilde R$**로 가게 합니다.


그 결과
후보 생성이 정상인 4개 메쉬에서 $\tilde R$(2.50)가 현재
J(2.82)를 이깁니다. manikin 3.99→2.89, dragon 2.01→1.70으로 큰
폭.


단, happy는 악화(11→16.7). 하지만 happy는 논문이 이미
"후보 생성 실패 케이스(샘플링 한계, scoring과 무관)"로 분리해 둔 메쉬입니다. LOMO 교차검증도
happy를 제외하므로 일관됩니다.




즉 주장 가능한 것 (모두 데이터로 뒷받침됨):




$B$ = 접지 노드 텐서의 Rayleigh 항 (정확, 증명됨) → 제목의
"Tensor"가 정직해짐.


텐서
Rayleigh 상관 −0.08 → 0.60 회복, 단일 feature 최고.


$P$
제거 + 접지 통합($\tilde R$)이 후보 생성 정상 메쉬에서 J보다 정확.




리뷰어 방어 포인트 (반드시 짚어야 함)



심사자가 "어떤 스칼라든 이차형식으로 쓸 수 있다 — trivial하지
않냐"고 칠 겁니다. 방어는: 접지
항은 면-면 흐름과 같은 구조
$c,m_{\text{source}},m_{\text{receiver}}^T$의 극한 케이스입니다 —
receiver가 실제 면($m_j!\cdot!n\in(\eta,1)$)이냐, 빌드플레이트라는 "완전히 수평인
receiver"($m_j!\cdot!n=1$)냐의 차이일 뿐. 즉 "모든 오버행은 receiver로 흐르고,
receiver는 면 아니면 플레이트"라는 통일된 그림. 임의의 이차형식 트릭이 아닙니다.



한 가지 정직하게 정리할 wrinkle: 면-면 가중치는 높이 감쇠 $1/(1+\alpha
h)$, 접지 가중치는 높이 증폭 $(1+\alpha h)$로 부호가 반대입니다("가까운 자기지지는 선호 / 높은
플레이트 지지는 비싸다"는 서로 다른 물리). 통합 텐서의 정합성을 완벽히 하려면 이 height convention을 논문에서
명시적으로 정당화하거나, 완전 대칭 버전($\tilde B' = \sum O_iA_i/(1+\alpha h)$)을 별도 변형으로 재검증하는 게
좋습니다. — 현재 검증한 건 기존 $B$를 정확히 보존하는 안전한 버전입니다.






검증 스크립트는 verify_ground_node_reframing.py에 남겨뒀습니다(언제든 재현 가능).



다음으로 (1) 이 결과를 메인 논문의 §목적함수 + §ablation에 녹여
**"$J=R+P+B$ → 통합 텐서 $\tilde R$"**로 재서술하는 개정안을 써드릴까요, 아니면 (2) height
convention wrinkle을 없앤 완전 대칭 버전 $\tilde B'$를 추가 검증해 어느 쪽이 더 정확한지 먼저 확인할까요?









전체 결과가 나왔습니다. 두 지표가 서로 다른 이야기를 하므로 정직하게 갈라서 보겠습니다.



검증 결과



전역 상관 — Spearman(플레이트 항, $v_{ss}$),
높을수록 좋음











mesh




B_amp (현재)




B_flat




B_att (대칭, 2b)




B_uni (통일, 2a)








Bunny




0.50




0.36




0.25




0.35








manikin




0.66




0.66




0.66




0.69








dragon




0.85




0.82




0.77




0.83








happy




0.29




0.07




−0.18




−0.21








lucy




0.62




0.66




0.63




0.67








평균




0.58




0.51




0.43




0.47











best-of-3 ratio — $R+B_{변형}$ 랭킹,
낮을수록 좋음











mesh




B_amp




B_flat




B_att




B_uni








Bunny




2.57




3.10




3.10




3.10








manikin




2.89




2.89




2.89




1.37








dragon




1.70




1.62




1.62




1.62








lucy




2.82




2.82




2.82




2.82








평균(happy 제외)




2.49




2.61




2.61




2.23











결론: 제가 제안했던 "대칭
버전(2b)"은 기각됩니다



가장 중요한 발견부터:




면-면과 대칭으로
맞춘 attenuation(B_att)이 두 지표 모두에서 최악에 가깝습니다. 상관 0.43(최저), happy에선 음수(−0.18)로 부호까지 뒤집힘. "height convention을 면-면과 통일해야 정합적"이라는
제 직관은 틀렸습니다.


즉 amplification(현재 $B$)은 고쳐야 할 불일치가
아니라, 물리적으로 옳고 실증적으로 검증된 의도적 비대칭입니다. "먼
자기지지는 약하니 감쇠, 키
큰 플레이트 기둥은 비싸니 증폭"
— 두 항이 달라야 맞습니다. B_amp는 상관 0.58로 가장 높고 가장 일관적입니다.





→ 이건 지난 턴의 (E1) 리프레이밍을 오히려 강화합니다. height wrinkle은 "정당화 필요한
약점"이 아니라 "데이터로 뒷받침되는 설계 결정"으로 논문에 쓸 수 있습니다. 리뷰어가 "왜
플레이트만 부호가 반대냐"고 물으면 → 이 표가 답입니다.




한 가지 와일드카드: B_uni (2a, 완전 통일)



수학적으로 가장 깔끔한 버전(하나의 weight 법칙, 플레이트 = 법선 $n$인
receiver)인 B_uni는:




전역
상관은 0.47로 amp보다 낮지만,


best-of-3(happy 제외) 2.23으로 최고 —
단, 이게 거의 전적으로 manikin 한 메쉬(2.89→1.37,
oracle 1.13에 근접)에서 나옵니다. Bunny에선 오히려 나쁨(3.10).




→ 흥미롭지만 단일 메쉬가 끌고 가는 불안정한 결과라
지금 채택하긴 이릅니다. "향후 연구: $O^2$ 가중 + 통일 weight 법칙이 세장형(elongated) 형상에서
유리한지" 정도의 future work 항목으로 남기는 게 정직합니다.



최종 권고



B_amp(현재 $B$)를 유지하고, (E1) 방식 — 가상
접지 노드로 텐서에 흡수 — 로 갑니다. (2)번 검증의 순수익은:




제안했던
대칭 버전이 틀렸음을 데이터로 확인 →
막다른 길 제거.


height
convention 비대칭이 약점이 아니라 검증된 강점임을
확보 → (1) 리프레이밍의 방어력이 올라감.




스크립트는 experiment_plate_height_convention.py에 있습니다.



이제 정리된 그림으로 (1) 메인 논문의 §목적함수 + §ablation을 "통합 텐서 $\tilde R =
R+B$" 서사로 재서술하는 작업으로 넘어갈까요? 지난 두
검증(접지 노드 identity + height convention)이 그 근거를 모두 제공합니다.












새로 추가된 핵심 (§Build Plate 항 안):




§빌드플레이트의 가상 접지 노드 해석 (sec:groundnode) — 증강 텐서 $\tilde F(n)$ 정의, 플레이트 항의 Rayleigh 기여
유도, $\tilde R = R+B$ 정확 동치(식 eq:Rtilde)와 $10^{-12}$ 수치 확인. "플레이트 = 면-면 자기지지의 극한(법선이
$n$인 receiver)"이라는 통합 그림 + 높이 규약 비대칭의 의도성 명시.




재서술된 곳:




§목적함수 — $J = R+P+B =
\underbrace{\tilde R}_{R+B} + P$ 로 재표현. "통합 텐서 Rayleigh cost + 면-면
지지량"으로 해석, $P$가 음의 신호임을 명시.


§Ablation에 신규 소절 §통합 텐서로의 재구성 (sec:unified) — 표 2개 추가:



tab:unified-corr: $\tilde R$ 상관 0.60 (단일
feature 최고, $J$의 0.47 압도)


tab:unified-b3: $P$ 제거 시 best-of-3가
happy 제외 2.82→2.50 개선




높이 규약 검증 문단: amp 0.58 / flat 0.51 / att 0.43 /
uni 0.47 → "대칭(att)이 최악, 현재 증폭이 옳음"을 데이터로 못박음. B_uni의 manikin
와일드카드는 future work로.



Abstract / Conclusion — 통합 텐서 동치와
"$\tilde R$가 $J$보다 우수"를 일관되게 반영.




검증 재현 스크립트 (논문 주장 뒷받침용): verify_ground_node_reframing.py, experiment_plate_height_convention.py.






이제 논문의 "Tensor" 정식화가 정직해졌고, ablation이 약점에서
서사의 엔진으로 바뀌었습니다.



다음 후보:




제목/서론 톤 조정 — 여전히 "Support Flow Tensor Field"인데,
본문이 "통합 텐서 = 접지 노드"로 정리됐으니 서론에서 이 통합을 한 문장으로 예고하면 일관성이 올라갑니다.


§구현 의사코드 갱신 — 알고리즘 박스가 아직 $J=R+P+B$ 기준인데, $\tilde R$ 관점 주석을
달지 결정.





이대로 두고 다른 작업으로.




어느 쪽으로 갈까요?
























OneNote에서 작성되었습니다.
