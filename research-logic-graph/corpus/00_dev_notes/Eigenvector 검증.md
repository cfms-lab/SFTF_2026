# Eigenvector 검증

Source: `D:\__SFTF_Projects(2026)\_dev_notes\Eigenvector 검증.mht`

Eigenvector 검증









2026년 6월 19일
금요일



오후 10:30










자, 이제는 이 eigenvector 방법이 맞는지 검증이 필요해.


1) TOMO_INT3의 v_ss값은 실제 slicer software 값과 거의 같으므로 정답이라고
생각하면 돼.


2) ../Tomo_GPU2024_CODEX/ 폴더의 TOMO_INT3의 v_ss 등고선 그래프






요약:









Mesh




TOMO best v_ss




SFTF score1 signed v_ss




ratio




SFTF best-of-3 signed v_ss




ratio








(1)Bunny_69k.ply




3201.39




9696.16




3.03x




7894.45




2.47x








(2)manikin.ply




4657.72




18562.36




3.99x




18562.36




3.99x








(3)dragon_100k_1.5x.ply




24446.98




49102.19




2.01x




49102.19




2.01x








(4)happy_50k_0.75x.ply




2112.47




26410.85




12.50x




23555.69




11.15x








(5)lucy_50k.ply




5036.14




14192.68




2.82x




14192.68




2.82x









핵심 관찰:



현재 SFTF는 TOMO
optimum보다 2.0x ~ 12.5x 높은 v_ss 지점을 고르고 있습니다.


happy_50k가 특히 크게
어긋납니다.


best-of-3를 써도 Bunny만
약간 개선되고, 나머지는 거의 개선되지 않습니다.


계산 자체는 Embree 덕분에 5개
mesh 전체가 약 27초 안에 끝났습니다.



즉 현재 SFTF는
“빠르게 후보 방향을 내는 것”은 잘 되지만, TOMO_INT3의 실제 support volume optimum과는 아직 정렬이 부족합니다.
다음 개선 포인트는 SFTF score가 TOMO v_ss와 더 잘 상관되도록 score 항의 weight나 방향 선택 기준을 튜닝하는
쪽입니다.







Intel Embree라는 ray
tracing 패키지가 있구나.






좋아, 튜닝을 시작해줘



좋습니다. 바로 튜닝으로
들어가겠습니다. 먼저 현재 SFTF 후보 전체가 TOMO v_ss와 어떤 상관을 갖는지 보겠습니다. “상위 3개만”이 아니라
1292개 후보 전체를 저장된 TOMO grid에 매핑해서, 어떤 score 구성요소가 실제 v_ss를 잘 설명하는지 확인할게요.




후보별 rayleigh, pair, bed, hit_count, singular value 계열을 뽑아
TOMO grid의 v_ss와 대조하겠습니다. 이 단계는 약간 계산이 있지만, 이미 Embree라 충분히 빠를 겁니다.





후보 pool 안에는 TOMO에 훨씬
가까운 방향들이 이미 있습니다. 즉 방향 샘플링 문제보다는 “후보를 고르는 score” 문제에 가깝습니다. 이제 저장된
candidate probe를 이용해, feature 조합을 여러 방식으로 맞춰보고 어떤 scoring이 5개 mesh에서 가장 덜
나쁜 선택을 하는지 찾겠습니다.






좋아. 그런데 TOMO_INT3와 optimal 위치에 차이가 있어.







1) TOMO_INT3 은 global optimum이 최소 두군데야. 예를 들어
(yaw, pitch) = (69, 130), (265, 49) 야.


2) 그런데 SFTF가
찾은 optimum은
(69, 130) 부근에 세 개가 모두 몰려 있고, (265, 49)는
못 찾고 있어.


3) 이걸
어떻게 해결할 수 있을까? optimal 배향의 순서가 중요한 것이 아니라, 사용자에게
이러이러한 optimum이 있다는 정보를 주는 것이 더 중요한 목적이야.






맞아요. 이 경우
목적이 “1등 하나를 맞히기”가 아니라 “서로 다른 좋은 basin들을 사용자에게 보여주기”라면, 지금 방식은 너무 local top-k에
가깝습니다. 해결 방향은 점수 순위 top-3가 아니라 optimal basin 대표점 top-k를 찾는 쪽으로 바꾸는 게 맞습니다.


제가 보기엔 가장
좋은 방법은 이겁니다.


1. 후보를 더 많이 뽑고, angular diversity로 클러스터링


SFTF score가
낮은 후보를 3개만 보지 말고 예를 들어 30개 또는 50개까지 가져옵니다. 그다음 yaw/pitch 위치 또는 3D build
direction 기준으로 각도를 재서, 가까운 후보들은 하나의 cluster로 묶습니다.


예:



cluster A: (69, 130)
주변


cluster B: (265, 49)
주변


cluster C: 다른 local
optimum 주변



그리고 각
cluster 안에서 TOMO_INT3 Mss가 가장 낮은 대표점 하나만 보여줍니다. 이렇게 하면 (69,130) 근처 후보 3개가
top-3을 독점하는 문제가 사라집니다.


2. SFTF 후보 6개가 아니라 “diverse 후보 N개”를 TOMO_INT3로 재측정


지금은 SFTF
low-score 3개 + high-score 3개만 TOMO_INT3로 다시 재고 있죠. 이걸 바꿔서:


SFTF
low-score 후보 50개 생성

-> 방향 diversity filtering 또는 clustering

-> cluster 대표 후보 10개 선택

-> TOMO_INT3 angle_step=0으로 Mss 재측정

-> Mss 낮은 cluster 대표 3~5개 표시


이러면 “SFTF가
어느 optimum basin들을 감지했는가”를 훨씬 잘 보여줄 수 있습니다.


3. global optimum 동률/준동률 영역을 TOMO_INT3 contour에서도
cluster로 표시


TOMO_INT3
쪽도 단순히 최솟값 3개를 찍으면 같은 basin 안의 격자점만 여러 개 찍힐 수 있습니다. 그래서 TOMO_INT3도 v_ss <=
min_vss * (1 + tol) 같은 기준으로 좋은 점들을 모은 뒤, angular clustering을 해서 “서로 다른 optimum
basin”을 표시하는 게 좋습니다.


예:


TOMO
optimum basin 1: yaw=69, pitch=130

TOMO optimum basin 2: yaw=265, pitch=49


이렇게 legend나
hover에 “basin representative”라고 표시하면 논문 그림으로도 훨씬 설득력이 있습니다.


추천 구현


오른쪽 SFTF
그래프를 이렇게 바꾸는 게 좋아 보입니다.


SFTF
lowest-score candidates: 50개

minimum separation: 20도 또는 25도

TOMO_INT3 remeasure: 대표 후보 8~12개

plot: TOMO Mss 기준 measured optimal basin 3~5개


그리고 왼쪽
TOMO_INT3 그래프도:


TOMO grid
global/near-global points

cluster by angular distance

plot: TOMO optimum basin representatives


핵심은 top-k
points가 아니라 top-k basins입니다. 지금 문제는 알고리즘이 완전히 틀렸다기보다, 출력 방식이 “같은 basin 안의 이웃
후보”를 중복해서 보여주는 구조라서 생긴 현상에 가깝습니다.







방금 적요해준 top-k basins
방식은 그 전보다는 조금 나아졌어. 그러나 여전히 3개의 optimal 배향들이 하나의 basin 안에 몰려 있어. - 눈으로
보더라도 등고선 그래프에는 대여섯 개의 basins 들이 있는데, SFTF optimal이 basin 당 하나씩 위치하도록 개선할
수 있을까?





가능합니다. 방금 그
방향으로 개선했습니다.


핵심은 기존의 “3D
build direction 각도 기준 basin 분리”만으로는 Plotly 등고선에서 눈으로 보이는 basin 분리와 맞지 않는다는
점이었어요. 그래서 최종 표시 단계에 yaw--pitch 평면 기준의 주기적 거리
필터를 추가했습니다.


변경 내용:



SFTF 후보 basin 수를
18개에서 40개로 늘림


후보 생성 단계의 방향각 필터는
20도에서 12도로 완화해서 더 다양한 후보를 남김


최종 Plotly 표시 단계에서는
yaw--pitch 좌표에서 45도 이상 떨어진 후보만 서로 다른 basin으로 인정


yaw/pitch는 0도와 360도가
이어지는 좌표라서 periodic distance로 계산


TOMO_INT3 재측정 Mss
기준으로 정렬한 뒤에도, 같은 시각적 basin에 몰린 후보는 제거



현재 lucy_50k
테스트에서는 SFTF measured optimal이 대략 다음처럼 서로 떨어진 basin으로 나뉘었습니다.


1) yaw=358,
pitch=177

2) yaw=190, pitch=358

3) yaw=331, pitch=17


검증:



compileall 통과


TOMO_INT3 batch 재측정
정상 실행


MeshData/tomo_int3_sftf_active_mesh_comparison.html
재생성 완료



수정 위치:



[scripts/plot_sftf_tomo_int3_contours.py
(line
31)](D:/__TomoNV_Projects/Tomo_TSE6_dev/scripts/plot_sftf_tomo_int3_contours.py:31)








이제 거의 완벽해. 혹시 계산 중에
C++ 이나 CUDA를 사용해서 빨라질 부분이 있을까?





응, 있어요. 다만
“전부 CUDA로”보다는 병목 성격별로 나누는 게 좋아 보입니다.


가장 효과가 클
가능성이 높은 부분은 SFTF의 후보 방향 평가 루프입니다. 지금 구조상 여러 support 방향 후보에 대해 ray 샘플링, hit
aggregation, score 계산을 반복하므로, 방향별 계산이 거의 독립적입니다. 이건 C++/CUDA 양쪽 모두 잘 맞습니다.


우선순위로 보면:



C++ / pybind11 후보



evaluate_support_flow_candidate_pool


ray 결과를 이용한 score
계산


triangle
center/normal/area 기반 반복 연산


direction별
rank/score feature 계산

NumPy로 이미 벡터화된 부분은 CUDA 이득이 작을 수 있지만, Python loop가 남아 있는 후보 방향
평가부는 C++로 옮기면 꽤 빨라질 수 있습니다. 구현 난이도 대비 효과가 가장 현실적이에요.



Embree C++ 직접 사용



현재 embreex/trimesh
경유 ray tracing도 빠르지만 Python 호출 overhead가 남습니다.


많은 방향 후보를 평가할 때 ray
batch를 C++에서 직접 구성하고 Embree에 한 번에 넣으면 더 좋아질 수 있습니다.


특히 “방향 후보 N개 × ray
M개” 구조를 한 C++ 함수 안에서 처리하면 Python 왕복 비용이 줄어듭니다.



CUDA 후보



후보 방향별 score 계산


triangle pair /
visibility / support accumulation


dense grid 형태의
yaw-pitch 평가

CUDA는 병렬성은 잘 맞지만, mesh ray intersection을 직접 CUDA로 안정적으로 구현하는 건 일이
커집니다. 이미 TOMO_INT3 DLL이 CUDA/C++ 쪽이라면, SFTF도 완전 CUDA화하기보다는 “ray hit 이후의
aggregation/score”부터 GPU화하는 게 현실적입니다.



TOMO_GPU2026 쪽 활용



지금 Plotly 비교용 TOMO
Mss 재측정은 이미 DLL을 쓰니까 병목이 크지 않습니다.


SFTF 자체 optimum 탐색을
TOMO에 더 자주 맡기면 정확도는 좋아질 수 있지만, SFTF의 빠른 후보 생성이라는 장점은 약해질 수 있어요.




내 추천은 이
순서입니다:



현재
cProfile로 evaluate_support_flow_candidate_pool 안의 세부 시간을 다시 측정


Python loop가 많은
score/candidate aggregation 부분을 C++ pybind11로 분리


그 다음 ray batch까지
C++/Embree로 묶기


CUDA는 마지막 단계로 검토



즉, 가장 먼저 C++ 확장 모듈이 좋고, CUDA는 나중이 좋아 보입니다. 지금 코드
상태에서는 C++만 해도 체감 속도 개선 여지가 꽤 있어요.




측정했습니다. 현재
active mesh는 MeshData/(1)Bunny_69k.ply이고,
evaluate_support_flow_candidate_pool() 기준 결과는 다음입니다.


총 후보:


coarse 512
+ refine 780 = 1292 directions


전체 시간:



cProfile: 약 6.60s
profiler overhead 포함


직접 단계 계측: 약 4.96s



병목 순위는 꽤
선명합니다.









단계




시간




의미








bed_accum_loop




1.51s




support
bed로 떨어지는 ray/source face 누적 Python loop








ray_hits




1.21s




Embree
ray intersection 호출 및 valid hit 필터








sample_faces




1.20s




방향마다
overhang 기반 face sampling








pair_accum_loop




0.50s




hit pair
tensor/score 누적 Python loop








overhang




0.21s




normals @
direction








refine
direction unique




0.15s




refinement
방향 중복 제거








svd




0.02s




거의 병목 아님









중요한 해석은
이거예요.


현재 병목은 “순수
ray tracing”만이 아닙니다. Embree 자체 호출은 빠른 편이고, 오히려 Python에서 매 방향마다 반복하는 누적 루프와
sampling이 큽니다.


특히 C++로 옮기면
효과가 클 후보는:



_support_flow_tensor_for_direction()
내부의 bed_accum_loop


_support_flow_tensor_for_direction()
내부의 pair_accum_loop


_sample_ray_face_ids()


가능하면 direction batch
전체를 C++에서 한 번에 처리



CUDA보다 먼저
C++/pybind11 또는 NumPy vectorization이 좋아 보입니다. bed_accum_loop와 pair_accum_loop는
Python loop라서 C++화 효과가 가장 직접적이고, ray intersection은 이미 Embree를 타고 있어서 CUDA로 갈
우선순위는 낮습니다.


다음 개선 1순위는
C++로 가기 전에, bed_accum_loop와 pair_accum_loop를 먼저 NumPy vectorization으로 줄여보는
것입니다. 이게 성공하면 C++ 확장 없이도 꽤 줄어들 가능성이 있습니다.



























OneNote에서 작성되었습니다.
