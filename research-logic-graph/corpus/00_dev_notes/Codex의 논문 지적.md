# Codex의 논문 지적

Source: `D:\__SFTF_Projects(2026)\_dev_notes\Codex의 논문 지적.mht`

Codex의 논문 지적









2026년 6월 24일
수요일



오후 9:28









\draft\SFTF_draft_eng.tex
는 SCI 저널 투구용 논문이야. 내용이 길어서 수식 설명은 Appendix 쪽으로 옮겼어. 전체 내용이 additive
manufacturing 분야 리뷰어가 쉽게 이해가능할지 분석해 봐줘.



8:14 PM






Worked for
2m 9s



전체적으로는 AM 리뷰어가 큰 그림은 이해 가능합니다. 문제 정의, “TOMO 전수탐색을 대체하지
않고 후보 생성기로 앞단 비용을 줄인다”는 포지셔닝, 5-group 검증의 속도 비교는 설득력이 있어요. 다만 지금 상태는 AM 논문이라기보다 계산기하/텐서 방법 논문처럼 먼저 읽힐 위험이 큽니다. 수식 유도
일부를 Appendix로 뺀 방향은 맞지만, 본문에도 아직 구현/수식/튜닝 세부가 많아서 리뷰어가 핵심 기여를 늦게 만납니다.



좋은 점




초반의
FDM/support-volume 문제 설정은 명확합니다: [SFTF_draft_eng.tex (line
89)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:89)


“replacement가 아니라
candidate generator/warm-start”라는 방어적 포지셔닝이 좋습니다: [SFTF_draft_eng.tex
(line
201)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:201)


Appendix로 ground-node
유도와 Group C landscape를 분리한 것은 본문 부담을 줄이는 데 효과가 있습니다: [SFTF_draft_eng.tex
(line
1667)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:1667)


한계 인정이 솔직합니다.
in-sample bias, happy hard case, critical-angle invariance를 숨기지 않아 신뢰도는
올라갑니다.




가장 큰 이해 장벽




Abstract가 너무 많은 내부 용어를 한 번에 던집니다.

asymmetric flow tensor, Rayleigh contribution,
ground-node unification, negative signal, LOMO, TOMO_CUDA가 모두 초록에 들어가서 AM
리뷰어가 첫 문단에서 이미 수학 논문처럼 느낄 수 있습니다. 초록은 “문제 → 후보 생성 아이디어 → 검증 결과 → 한계” 중심으로
줄이고, ground-node는 한 문장으로만 두는 편이 좋습니다.


본문 Methods가 아직 implementation note처럼 깁니다.

K_ray, epsilon, first-hit fallback, exact weight vector,
rank-normalization 식까지 본문에 있습니다. AM 리뷰어에게 필요한 것은 “왜 support가 줄어드는 방향을 잘
고르는가”이지 “현재 코드가 어떤 상수를 쓰는가”가 먼저는 아닙니다.

특히 final rank tuning weight는 [SFTF_draft_eng.tex (line
733)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:733) 이후
Appendix나 supplementary로 보내고, 본문에는 “rank-normalized rescoring was used;
cross-validation is reported” 정도가 더 읽기 쉽습니다.


논문의 중심 주장과 ablation 결과 사이가 조심스럽습니다.

결과는 “순수 tensor-derived terms는 약하고, build-plate/internal
visibility가 핵심”이라고 말합니다. 이건 좋은 발견이지만, 제목과 novelty가 “Support Flow Tensor”에
강하게 걸려 있어서 리뷰어가 “그럼 tensor가 핵심이 아닌가?”라고 물을 수 있습니다.

표현을 “raw asymmetric tensor alone is insufficient; the augmented
ground-node tensor makes the build-plate term part of the tensor
formulation” 쪽으로 더 선명하게 잡으면 방어가 됩니다.




투고 전 반드시 고칠 것




[reference needed]가 두
군데 남아 있습니다: [line 635 (line
635)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:635),
[line 743 (line
743)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:743)


obsolete 용어 concave가
남아 있습니다: [line 845 (line
845)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:845)


5-group 설명에서
footnote는 36 meshes, 본문은 35 meshes입니다: [line 1330 (line
1330)](D:/__TomoNV_Projects/Tomo_SFTF_dev/draft/SFTF_draft_eng.tex:1330)


논문 안에
Experimental/etc/*.npz, script path, .html 같은 repo-local 표현이 많습니다. 재현성 문장은
좋지만 본문에는 줄이고, “data and scripts are provided in the repository”로 정리하는 게 저널
문체에 맞습니다.


FDM 중심이라고 시작하지만 관련
연구와 일부 표현은 AM 전반/metal/industrial part까지 넓습니다. “본 연구의 물리적 support
criterion은 single-build-direction, critical-angle 기반 support가 유효한 공정에 초점을
둔다”는 scope 문장이 필요합니다.




추천 수정 순서




Abstract를
250단어 안팎으로 재작성하고 수학 용어 밀도를 낮추기.


본문 Methods를
“algorithm overview” 중심으로 압축하고 세부 상수/weight/구현 최적화는 Appendix로 이동.


Figure 1 또는 Figure 2
근처에 “SFTF in 4 steps” 그림/박스 추가: overhang faces → ray-supported faces/build
plate → candidate score → TOMO/slicer verification.


TOMO_INT3가 왜 ground
truth로 충분한지 짧게 재강조. 가능하면 “prior work showed agreement with commercial
slicer”를 명확히 연결.


위의 투고 전 오류 4개를 먼저 정리.




결론적으로, 기술적 내용은 충분하지만 AM 리뷰어용 서사는 아직 조금 무겁습니다. “수식의
정당성”보다 “support minimization workflow에서 어디에 들어가고 얼마나 시간을 줄이는가”를 더 앞에 세우면 훨씬 쉽게
읽힐 원고입니다. 코드 수정은 하지 않았고, 테스트는 분석 작업이라 실행하지 않았습니다.









논문의 실제 위치 (제가 읽고 판단한 것)



핵심
기여는 (1) 방향별 비대칭 Support Flow Tensor Field F(n)F(n) F(n)정의, (2) build-plate
penalty가 augmented tensor에 가상 ground node를 더한 Rayleigh 기여와 정확히 동치라는 통합(R~=R+B\tilde R = R+B R~=R+B, 10−1210^{-12}
10−12이내 수치 검증), (3) exhaustive sweep 앞단의 빠른
candidate generator / warm-start 입니다. 속도 이득(Python 1.4~34×, C++ 10~5,160×),
LOMO 교차검증, ablation, PCA·Support Tensor 베이스라인 비교, 100만 face까지 확장성, 5그룹 35메쉬 —
실험 설계와 정직성(특히 happy 케이스 실패, in-sample 낙관 편향, "예측력 대부분이 사실 build-plate 항에서
나온다"는 점을 스스로 드러낸 것)은 상당히 좋습니다.



다만 티어를 결정짓는 약점들도 분명합니다.




정확도가 거친 편입니다.
best-of-3 ratio가 TOMO 최적 대비 약 2.37 — 즉 후보 방향이 최적의 약 2.4배 서포트 부피. 베이스라인(PCA
3.63, Support Tensor 4.30)보다는 낫지만, "정밀 솔버"가 아니라 warm-start
수준입니다.


저자들 스스로 ablation에서
**"tensor 항은 거의 기여하지 않고 예측력은 build-plate penalty에서 나온다"**고 밝힙니다.
정직해서 좋지만, 헤드라인인 "tensor" 신규성의 무게를 스스로 깎는 측면이 있어 리뷰어가 파고들 지점입니다.


저자들의 이전 MSST/GPU-MSST
연구의 **후속(follow-up)**으로 명시적으로 포지셔닝되어 있어, AM 리뷰어가 "incremental"로
볼 여지가 있습니다.


실제
프린팅 실험이 없고
표준 메쉬 + Thingi10K 계산 실험만 있습니다. AM 본지는 보통 강한 신규성 또는 물리적 검증을 선호합니다.


단독 저자, 최신
orientation-optimization 기법(학습 기반 등)과의 직접 벤치마크 부재.




티어별 추천



도전(reach) — Additive
Manufacturing 본지, Virtual and Physical
Prototyping(T&F, IF 높음). 가능은 하지만 위 약점 때문에 major revision~reject 리스크가
실재합니다. 굳이 노린다면 프레이밍 강화(아래)와 가능하면 정확도 개선이 필요합니다.



현실적 최적(best fit) — 이 논문의 성격(기하·계산 방법, ray
casting, tensor, spherical sampling, warm-start)에 가장 자연스럽게 맞는 곳들입니다. 게재 확률과
임팩트의 균형이 가장 좋습니다.




Computer-Aided
Design
(Elsevier) — 기하/계산 알고리즘의 정통 홈. 매우 잘 맞습니다.


Journal
of Manufacturing Processes (Elsevier, IF 약 6) — AM 계산 방법 수용 좋음.


3D
Printing and Additive Manufacturing (Mary Ann Liebert) — 이미 폴더에 이 저널 CSL을 갖고
계시네요.


Rapid
Prototyping Journal (Emerald) — AM 방법론의 클래식 venue.




안전(safe) — Progress
in Additive Manufacturing(Springer, 폴더에 CSL 있음), International Journal of Advanced Manufacturing Technology(Springer).
무난히 실릴 가능성이 높습니다.



참고로 폴더에
additive-manufacturing.csl, 3d-printing-and-additive-manufacturing.csl,
progress-in-additive-manufacturing.csl 세 개를 준비해 두신 걸 보면 이미 이 세 곳을 저울질하고 계신 것
같은데, 제 판단으로는 AM(도전) → 3DPAM(현실) → PiAM(안전)
순의 난이도 스펙트럼이 맞습니다.



만약 AM 본지를 노린다면



이전에 물어보신 special issue 경로가 여기서 유효합니다. AM이
"computational design for AM", "build orientation / process
planning", "data-driven or geometry-driven AM" 류의 특별호를 열고 있다면,
게스트 에디터가 방법론·속도 기여를 본지 일반 심사보다 더 환영할 수 있어 진입 장벽이 낮아질 수 있습니다. 동시에 프레이밍을
"tensor 신규성"보다 **"exhaustive sweep 대비 수십~수천 배 빠른, 정직하게 검증된
warm-start 프레임워크 + build-plate=ground-node 통합이라는 깔끔한 수학적 통찰"**로 재배치하고,
가능하면 슬라이서 기반 실검증이나 정확도(2.37 → 더 낮게)를 한 단계 끌어올리면 본지 승산이 올라갑니다.



원하시면 (1) 현재
AM이 열어둔 special issue 중 이 논문과 맞는 게 있는지 찾아보고, (2) 후보 저널 2~3곳의 scope·IF·최근 게재 경향을
비교한 표를 만들어 드릴 수 있어요. 어느 쪽부터 해볼까요?






확인한 최신
수치(2025 JCR 기준)로 정리했습니다.











저널




출판사




IF (2025)




5-yr / Quartile




이 논문과 scope 적합도




포지션·코멘트








Additive Manufacturing




Elsevier




11.1




13.0 · Q1




높음 (AM 전반)




도전. 분야 최정상. 신규성+물리검증 선호라 warm-start·계산 논문엔 벽이
높음. special issue 경로가 현실적 진입로








Journal of Manufacturing Processes




Elsevier




6.8




7.0 · Q1




중상 (제조공정
전반)




현실적 상단. IF 높고 계산·공정 방법 수용 폭 넓음. AM 대비 문턱 낮음








Progress in Additive Manufacturing




Springer




5.4




5.6 · Q1




높음 (AM 전반)




현실적 본명. AM 전용 + Q1 + 적정 문턱. 폴더에 CSL 준비해 두신 곳








Computer-Aided Design




Elsevier




3.1




3.5 · Q2




최상 (기하·계산 알고리즘)




fit 1순위. ray casting·tensor·spherical
sampling 류의 정통 홈. IF는 낮지만 리뷰어 풀이 가장 잘 맞음








3D Printing and Additive Manufacturing




Mary Ann
Liebert




2.1




2.9 ·
(Q2급)




중상 (AM 전반)




안전판. 무난한 게재. CSL 보유











핵심은 표에서 보이듯 "IF 순"과 "fit 순"이 갈린다는 점입니다.
IF만 보면 AM > JMP > PiAM > CAD > 3DPAM이지만, 논문 성격(순수 기하·계산 알고리즘, 물리
프린팅 실험 없음)으로 보면 CAD가 적합도 1순위입니다. 다만 CAD는
Q2에 IF 3.1이라, "임팩트"를 중시하시면 PiAM(5.4 Q1, AM 전용)이 균형점으로 가장 무난합니다.



제 추천 조합은 두
갈래입니다. 임팩트 우선이면 AM(special issue) 도전 → 리젝 시 PiAM,
적합도·게재 안정성 우선이면 PiAM 또는 CAD를 1순위로 바로.
JMP는 IF는 좋지만 "제조공정" 색이라 순수 기하 알고리즘 논문은 리뷰어 매칭이 들쭉날쭉할 수 있어 2순위로 두는 걸
권합니다.









이렇게
+로 연결하여 정의하는 것이 일반적인 것인가?



1분
전



네, 항들을
+로 더해 목적함수를 만드는 것 자체는 매우 일반적입니다. 이를 "가중합 스칼라화(weighted-sum
scalarization)"라고 부르고, 원래는 여러 목적을 가중치와 함께 더하는 형태



J=λ1f1+λ2f2+⋯J=λ1​f1​+λ2​f2​+⋯



입니다. 토폴로지 최적화(데이터항 + 제약/페널티항), 머신러닝 손실함수(loss = 데이터 적합 +
정규화항), 물리 에너지(여러 기여의 합) 등 거의 모든 분야에서 표준적으로 쓰입니다. 그러니 J=R+P+BJ=R+P+B라는 형태 자체는 전혀 이상하지 않습니다.



다만
"일반적이냐"와 "엄밀하냐"는 조금 다른 문제이고, 이 논문의 경우 리뷰어가 짚을 만한 두 가지
관례적 주의점이 있습니다.



첫째, 차원(단위)이 맞아야 합니다. 가중합의 암묵적 전제는 더해지는 항들이 같은 척도(또는
무차원화)되어 있다는 것입니다. 그런데 논문 본문에도 적혀 있듯 R,P∼R,P∼ 면적22, B∼B∼ 면적으로 단위가
다릅니다. 단위가 다른 양을 그냥 더하면 수치 스케일이 가장 큰 항이 사실상 결과를 지배하게 됩니다. 실제로
\S\ref{sec:robustness}의 분석에서 "세 항을 같은 스케일로 정규화하면 오히려 상관이 0.52→0.14로
급락"한 것이 바로 이 현상입니다 — raw JJ의 예측력이 항들의 균형이 아니라 스케일이 큰 BB의 지배에서 나왔다는 뜻이죠.



둘째, 가중치를 보통은 두거나 조정합니다. 표준형은 λR,λP,λBλR​,λP​,λB​를 두고 교차검증 등으로 정하는데, 이 논문은 λR=λP=λB=1λR​=λP​=λB​=1로 고정했습니다. 단위도 다른데 가중치까지 1로 두는 건 "물리적 의미 있는 합"이라기보다
편의적 선택에 가깝고, 이 점은 리뷰어가 "왜 1인가, 정규화는 했는가"라고 물을 수 있는 지점입니다.



그래서 정리하면 — 더하는 형식은 정통이고 문제없지만, 엄밀하게 하려면 (a) 항들을
무차원화/정규화하거나, (b) 가중치를 학습·튜닝하거나, (c) 애초에 단일 스칼라합 대신 다목적(Pareto) 또는 순위 기반으로
다루는 것이 권장됩니다. 흥미롭게도 선생님은 이미 (c) 쪽으로 한 발 옮기셨습니다 — 최종 후보 선택에서 raw JJ 대신 rank-normalized tuning
score TT(각 특징을 후보군 내 순위로 정규화한 뒤
가중)를 쓰신 게 그것이고, 이게 단위 불일치 문제를 우회하는 더 방어 가능한 방식입니다.



한
가지 덧붙이면, 가중합 스칼라화는 비볼록(non-convex) Pareto front의 일부 해에 도달하지 못한다는 이론적 한계도
알려져 있습니다. 지금 논문은 "정밀 최적화"가 아니라 "후보 생성"이 목적이라 이 한계가 치명적이진
않지만, 만약 나중에 다목적(서포트 부피 + 표면품질 + 프린트 시간 등)으로 확장하실 때는 단순 덧셈보다 정규화된 가중합이나 Pareto
방식을 고려하시는 게 좋습니다.






출처:
<https://claude.ai/cowork/cse_01UFJdBHubRcn2aUV6j84b4k>






Pareto 방식의
핵심은 여러 목적을 하나의 숫자로 합치지 않고,
"지배(dominance)" 관계로 해를 비교하는 것입니다. 선생님 문제(빌드 방향 최적화)에 바로 대응시켜
설명드릴게요.



먼저 개념입니다. 빌드
방향 후보 하나를 여러 목적으로 평가한다고 합시다 — 예를 들어 (서포트 부피, 표면 거칠기, 프린트 높이/시간, 제거 흔적 면적). 두 후보
AA A, BB B에 대해, AA A가 모든 목적에서 BB B보다 같거나 좋고, 적어도
하나에서 엄격히 더 좋으면 "AA A가 BB B를 지배한다"고 합니다. 어느 후보에게도 지배당하지 않는 해들의
집합이 Pareto 최적집합(Pareto front), 즉 "더
이상 한 목적을 손해 보지 않고는 다른 목적을 개선할 수 없는" 절충 경계입니다. 가중합처럼 "서포트 0.6 + 표면
0.4" 같은 임의의 환율을 정할 필요가 없다는 게 장점이죠.



구체적인 절차는 크게
세 단계입니다.



1) 각 후보를 여러 목적으로 평가. 선생님은 이미 SFTF가 **소수의 후보
풀(coarse+refined, 약 1,292개)**을 만들어내니, 각 후보 방향에 대해 서포트 부피(또는 R~\tilde R R~), 프린트
높이, 표면/접촉흔적 추정치 등을 벡터로 계산하면 됩니다.



2) 비지배 정렬(non-dominated filtering)로 Pareto front 추출.
후보가 이미 이산적인 작은 집합이라 이 부분이 아주 쉽습니다. 모든 쌍을 비교해 지배당하는 후보를 걸러내면 끝이고, 복잡도는
O(n2m)O(n^2 m) O(n2m)(후보 nn n, 목적 mm m) 수준 — 선생님의 후보 풀 크기면 순식간입니다. 즉 연속 공간 전체를 다목적 최적화할 필요 없이, SFTF가 뽑은 후보 위에서 Pareto 필터만
얹으면 됩니다. 이게 warm-start 철학과도 잘 맞아요.



(만약 후보 풀 없이
연속 공간에서 직접 다목적 최적화를 해야 한다면, 그때 쓰는 표준 알고리즘이 NSGA-II입니다
— 비지배 정렬 + crowding distance로 다양성을 유지하며 진화시키는 방법이고, 그 외 MOEA/D, SPEA2 등이 있습니다.
하지만 선생님 구조에선 보통 1)~2)면 충분합니다.)



3) Pareto front 위에서 최종 한 개 고르기(decision-making).
front는 여러 해의 집합이라, 결국 하나를 골라야 할 때 방법이 몇 가지 있습니다. 사용자 선호 가중치를 적용하거나, knee point(한 목적을 조금만 양보해도 다른 목적이 크게 좋아지는
"꺾이는 지점")를 자동 선택하거나, 아니면 front 자체를
사용자에게 보여주고 고르게 하는 방식입니다. 마지막 방식이 흥미로운데, 선생님이 이미 하고 계신 "top-k basin을 사용자에게 제시" 하는 철학과 거의
같습니다. 즉 "서로 떨어진 좋은 방향 그룹들을 보여준다"를 "Pareto 절충 후보들을 보여준다"로
자연스럽게 확장할 수 있습니다.



대안으로
**ε-제약법(ε-constraint)**도 알아두면 좋습니다. "표면 거칠기 ≤ 기준치, 프린트 높이 ≤ 기준치라는 제약 아래
서포트 부피만 최소화" 식으로, 한 목적만 최적화하고 나머지는 상한 제약으로 거는 방법입니다. 구현이 단순하고, 가중합과 달리 비볼록
front의 해도 잡을 수 있어서 실무에서 많이 씁니다.



간단한 예를 들면,
후보 세 방향이 (서포트, 높이) = A(100, 50), B(120, 30), C(130, 60)이라 할 때, C는 A보다 두 목적 모두
나쁘니 C는 지배당해 탈락, A와 B는 서로 한쪽씩 우위라 둘 다 Pareto front에 남습니다. 이때 "높이를 좀 감수하더라도
서포트를 줄이겠다"면 A, 반대면 B를 고르는 식이죠.



선생님 논문 맥락에서
권하는 형태는: 현재 J=R+P+BJ=R+P+B J=R+P+B가중합으로 1차 순위를
매기되, 최종 후보 제시 단계에서 (서포트 대리값, 프린트 높이, 표면 추정치) 같은 2~3개 목적으로 Pareto 필터를 적용해
"절충 후보 몇 개"를 보여주는 것입니다. 계산도 거의 공짜고, 단일 스칼라합의 단위·가중치 논란도 피해
갑니다.



원하시면 이
Pareto 후처리를 선생님 파이프라인(후보 풀 → Pareto 필터 → top-k basin 제시)에 어떻게 끼워 넣을지 의사코드나 실제 Python 함수로 만들어 드릴까요? 아니면 논문에 한
문단(future work 또는 방법 확장)으로 넣을 수 있게 글로 정리해 드릴 수도 있습니다.






happy의 진짜
문제는 TOMO optimum 주변이 비정상적으로 날카롭다는 점입니다. 저장된 1도 TOMO grid 기준으로 happy 최적은
(yaw=91, pitch=111)인데, 그 주변 window의 median ratio가 이렇게 튑니다.




±2°: median 4.68


±5°: median 6.48


±10°: median 9.28




반면 dragon은
±10° median이 1.59, manikin도 1.59 정도입니다. 즉 happy는 최적점에서 1-2도만 벗어나도 support
volume이 몇 배로 커지는, 아주 얇은 홈 같은 basin입니다.



또 하나 중요한 점은
SFTF가 그 basin 근처를 아예 못 보는 것은 아닙니다. happy에서 SFTF 후보 중 (yaw=90, pitch=109) 같은 거의
근처 후보가 있는데도 그 seed ratio가 4.348이고, score rank는 179입니다. 그래서 top-3/top-10에는 안
들어오고, local TOMO를 K=26 이상까지 넓혔을 때야 정확한 TOMO optimum (91,111)을 window 안에 포함해서
ratio 1.0을 회복합니다.



따라서 원인은 대략 세
가지가 겹친 것으로 보는 게 맞습니다.




happy의
TOMO landscape가 매우 sharp/narrow하다.


SFTF의 현재 proxy score
R/P/B와 rank tuning이 그 narrow basin을 좋은 후보로 보지 못한다.


SFTF는 기본적으로 build
direction 중심인데, TOMO grid는 yaw/pitch 표현과 voxel/discretization branch 영향이
커서 happy에서 방향이 조금만 달라도 값이 크게 바뀐다.




해결 방향은 “삼각형
수 줄이기”보다는 이쪽이 맞습니다.




먼저 happy 최적점 주변을 0.5°
또는 0.25° finer local TOMO로 재검증해서, 이 값이 물리적으로 안정적인 최적점인지 아니면 1도
grid/voxelization artifact인지 확인해야 합니다.


후보 생성은 SFTF top-3만 쓰지
말고, baseline top-K + Pareto branch + local TOMO verifier의 union 방식이 좋아
보입니다. Pareto는 이전 비교에서 happy를 더 빨리 잡았습니다.


refinement parent를
score 상위 12개만 쓰지 말고, Pareto/frontier/diversity 기준으로 happy 같은 낮은-rank
basin도 refinement 대상에 포함해야 합니다.


hard-case detector를
두는 것도 좋습니다. 예를 들어 top-3 local ratio가 높으면 자동으로 K=30 또는 dual-branch
yaw/pitch local search로 확장하는 방식입니다.




즉 happy는
“mesh가 커서 실패”라기보다, TOMO optimum이 너무 좁고 현재 SFTF
랭킹이 그 좁은 최적 방향을 상위 후보로 올리지 못하는 case입니다.





















OneNote에서 작성되었습니다.
