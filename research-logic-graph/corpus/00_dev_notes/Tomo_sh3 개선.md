# Tomo_sh3 개선

Source: `D:\__SFTF_Projects(2026)\_dev_notes\Tomo_sh3 개선.mht`

Tomo_sh3 개선









2026년 6월 21일
일요일



오후 1:36












TSE_TomoSh3 분석 (인체 계측 논문 + 러너)



먼저 정리: TSE_TomoSh3.pdf(md5 7ac541a0)는 인체계측 논문이고
TSE_TomoSh3.py는 그 실행 러너입니다. 이 논문의 핵심 코드(BodyMeasure, cut_function, cut_math, gltfLoader)는 앞서 TSE_TomoSh2 분석에서 이미 깊이 점검·수정했으므로,
여기서는 러너
스크립트 자체와 아직 다루지 않은 정합성 항목에
집중합니다.



1. 정합성 (논문 ↔ 러너) — 대체로 일치, 일부 불일치



일치 (✓)




파이프라인이
논문과 일치: bone_pairdist로
Torso(목·겨드랑이 분리용), bone_p2bdist로 6개 부위 —
논문 2.3절 서술과 동일 (TSE_TomoSh3.py:26-37).





max_height에 SizeKorea 키(165.001/175.99) 사용 → 앞서 고친
gltfLoader 덕분에 stature가 정확히 재현됨(F20 164.96, M20 175.99).





계측 출력값이 논문 Table 3/4와
일치(검증 완료).




불일치 (⚠)




군집 수 5 vs 6 — 논문 2.3절은 "k-means, k-medoids, 병합 군집
… 목표 군집 수를 6개로"
라고 명시하나, 러너의 통계 기법은 5개를 사용 (line 23-25: kmeans/5, kmedoids/5, aggler5). 6부위 분할에는 6이 맞고 논문과도 일치 → 5는 6으로 수정 필요(선택 옵션이지만 논문과
모순).


존재하지 않는 데이터 파일 — line 16의 주석 SK6th_M20_4k_NoFinger_JumpDown.gltf가 저장소에 없음. 논문 Figure 11(임의 자세,
Jumping Down) 을 이 데이터로 재현 불가(SK6th 점프 메쉬 부재;
masha1 점프 메쉬만 존재).




2. 개선점



A. 러너가 노이즈에 취약한 원본 분할(bone_p2bdist)을 사용 (가장 중요) line 27, 31-37이 bone_p2bdist를 쓰므로,
M20/87k에서 엉덩이
둘레 검출 실패(앞서 확인한 31.3 cm,
66.7% 오차)가 그대로 발생합니다. 우리가 추가·검증한 bone_p2bdist2(연속 패널티)로 바꾸면 동일 입력에서 hip이 82.6 cm로
복원되고, 정상 케이스 값은 그대로 유지됩니다. → 러너의 'bone_p2bdist'를 'bone_p2bdist2'(또는 'bone_skinweight')로 교체 권장.



B. 이미 적용된 수정들이 이 러너에 직접 이득 gltfLoader max_height 하드코딩(170) 수정, 측지선 솔버 1회 빌드 재사용, 중복 rear_waist 제거, cut_math.normalize/rescale 정리 — 모두 이 러너 경로에 반영되어 동작·정확도·속도가 개선된 상태입니다.



C. 견고성(robustness) 분할 실패로 특정 부위/둘레가 없으면 BodyMeasure._find_breast_point 등에서 get_girth(...).vertices가 None 참조로 크래시할 수 있습니다(앞서 skin 초기 시도에서 관측). 둘레/부위 존재 가드를 추가하면 임의
자세·고해상도에서 안전해집니다.



D. 정량 출력
러너는 polyscope GUI + 길이 출력만 제공합니다. 4종 메쉬 오차표는 우리가 만든 draft_sh2/make_tables.py가 자동 생성하므로, 러너에 CSV 출력 옵션을 더하거나 make_tables.py를 표준 검증 경로로
사용하는 것을 권장합니다.






권장 적용 우선순위




A — 러너를 bone_p2bdist2로 (실패 사례 즉시 해결)


불일치 1 — 통계 기법 군집 수 5→6 (논문 정합)


C — None 가드 (견고성)


불일치 2 — JumpDown 데이터 부재 명시(주석) 또는 masha1
점프 메쉬로 교체




원하시면
위 1~4를 코드에 적용하겠습니다. 특히 A·1·C는 안전하게 적용
가능하고(정상값 보존), 적용 후 4종 메쉬로 재검증해 드리겠습니다. 어떤 것을 진행할까요?



좋아.
이것도 논문용 테마가 될 수 있겠어. 수정 전후를 비교할 수 있도록, 개선되는 부분은 별도의 함수와 네이밍으로 진행해 줘. - 생성되는 데이터
파일들은 draft_sh3 폴더에 보관해 줘.






좋은 방향입니다. TSE_TomoSh3 개선을 별도 클래스/네이밍으로 구현해 전후 비교가 가능하게 하고, 생성 데이터는 draft_sh3에 보관하겠습니다.



먼저 핵심 개선을 담은 별도 클래스 BodyMeasureRobust를 만듭니다 (원본 BodyMeasure는 그대로 유지): ①None 크래시 가드, ②둘레선 유효성 검증(축을
감싸지 못한 허위 검출 제거), ③유두점 곡률 반경 보정.









개선을 별도 클래스/네이밍으로 구현 (원본 보존)



원본 BodyMeasure는 그대로 두고, 개선판을 별도 클래스로 추가 — cfms_bodym/robust.py의 BodyMeasureRobust(BodyMeasure):











개선




내용








R1 무크래시 가드




각
특징점 탐색을 격리 실행 → 일부 실패(부위 누락·임의 자세)가 전체 계측을 중단시키지 않음








R2 둘레선 유효성 검증




닫힌
단면이 절단 축(원점)을 실제로 감싸는지 확인 →
축을 벗어난 허위 단면(예: M20/87k hip 31.3cm) 거부








R3 유두점 곡률 반경




radius 0.01→3.0 cm(인체 스케일) → 노이즈에 강한 유두점











(세그멘테이션 개선 bone_p2bdist2는 draft_sh2에서 이미 별도
cutType으로 구현되어 그대로 활용)



전후 비교 데이터 → draft_sh3/



make_reliability.py(재현 스크립트) + reliability.csv. 4종 메쉬 × 3구성(orig / robust+p2b / robust+p2b2):











mesh




orig(원본)




robust+p2b




robust+p2b2








F20/4k




82.5
(10.7%)




=




=








F20/10k




85.7
(7.2%)




=




=








M20/4k




82.9
(11.8%)




=




=








M20/87k




31.3 (66.7%, 허위)




거부(미검출)




82.6 (12.1%)











→ 3단계 전후 스토리: ①원본은 허위 hip(31.3)을
정상처럼 보고 → ②robust(R2)가 이를 자동
탐지·거부(정직한 미검출, n_rejected=1) →
③robust+개선분할이 정확값(82.6)
복원. 정상 케이스(나머지 3종)는 세 구성이 완전 동일(무회귀).



사용법 (전후 전환)



# 기존(before):

from cfms_bodym import BodyMeasure; 
bodym = BodyMeasure(...)

# 개선(after):

from cfms_bodym.robust import BodyMeasureRobust; bodym = BodyMeasureRobust(...)



원본 BodyMeasure와 TSE_TomoSh3.py 러너는 변경하지 않아
baseline이 보존됩니다.






이 테마("자동 실패 탐지 기반 강건 인체 계측")는
draft_sh2와 구별되는 독립 논문이 됩니다(분할 품질 → 계측 신뢰성/실패탐지로 관점 이동). 원하시면
draft_sh2처럼 ① 신뢰성 그림(pgfplots: 메쉬별 hip 상태 3구성 비교)·robust 전후 스크린샷 생성, ② 국문/영문 논문
manuscript.tex 작성, ③ R3(유두점) 시각
검증까지 이어서 진행하겠습니다.






세 작업 모두 완료했습니다 (논문은 국문). 원고는 3페이지로 정상 컴파일됩니다.



① 신뢰성 그림 + hip 곡선 전후 스크린샷




pgfplots: 엉덩이 오차율 막대그래프(기존 vs 개선, M20/87k
66.7%→12.1%) — 본문 Figure.


polyscope 스크린샷 (figures/hip_original.png, hip_improved.png): 기존은 몸통 앞만 도는 열린 호(허위 31.3 cm), 개선은 인체를 감싸는 닫힌 고리(정상 82.6
cm) — R2 검증 식의 의미를 직관적으로 시각화.


신뢰성 표 + reliability.csv: 4종×3구성.




② 국문 논문



draft_sh3/manuscript.tex — "자동 실패 탐지를 통한 강건한 뼈대 기반 삼차원 인체 계측". 국문 초록·본문, 식 (1)(둘레선
유효성), 표 1, 그림 3종(오차 막대·hip 곡선·유두점), thebibliography. xelatex 2회로 컴파일(3쪽).



③ R3 시각 검증 → 기각 (정직한 부정
결과)



figures/breast_r001.png(반경 0.01) vs breast_r300.png(반경 3.0) 비교 결과: 원본 작은 반경이 유두점을 가슴 앞면에 정확히 찍고, 큰 반경은 날카로운 유두를 과평활해 검출점이
몸통 옆면으로 이동(악화). → R3을 BodyMeasureRobust에서 제거하고 원본 반경 유지, 논문에 민감도 분석(기각 사례)으로 수록.



별도 클래스/네이밍 (원본 보존, 전후 비교)



cfms_bodym/robust.py의 BodyMeasureRobust(BodyMeasure) = R1(실패 격리·무크래시) + R2(둘레선 유효성 검증, 허위 단면 자동 기각). 원본 BodyMeasure·TSE_TomoSh3.py는 미변경 →
baseline 보존.



핵심 전후 결과 (M20/87k 엉덩이):











구성




결과








원본




31.3
cm (66.7% 오차, 허위값을 정상처럼 보고)








robust+p2b




기각(정직한 미검출)








robust+p2b2




82.6
cm (12.1%, 정상 복원)











정상 케이스 3종은 세 구성 완전 동일(무회귀).



최종 draft_sh3/



draft_sh3/

├─ manuscript.tex / .pdf # 국문
논문(3쪽)

├─ reliability.csv # 신뢰성 비교
데이터

├─ make_reliability.py # 표
재현

├─ make_figures.py # 그림
재현

└─ figures/ hip_original.png hip_improved.png breast_r001.png breast_r300.png



추가로 원하시면 ① draft_sh3도 BibTeX·영문 캡션 병기로 통일, ② 임의
자세(점프) 메쉬로 강건성 시연(masha1 점프 데이터 활용), ③ TSE_TomoSh3.py 러너에 robust 옵션 추가를
진행하겠습니다.












②③ 완료했습니다. 원고는 3페이지로 정상 컴파일됩니다.



② robust 길이(측지선) 예외 견고화 — R4



cfms_bodym/robust.py의 find_lengths/shortest_path를 추가:




메쉬 정리(repair) 후 edge-flip 측지선 시도 → 실패 시 그래프(에지) 최단경로 폴백(비다양체 허용).


결과:
점프 포즈에서 길이가 0개(크래시) → 5/9개 산출.
SizeKorea 메쉬는 여전히 geodesic, 값 완전 동일(무회귀:
arm 53.97, outseam 95.01, crotch 76.64).




③ 점프 데모 정량 표



make_jump_stats.py + jump_stats.csv, 논문에 Table 2 추가:











구성




크래시




둘레 검출




둘레 기각




길이 측정




길이 방식








기존(orig)




예(RuntimeError)




24/24*




0




0/9




–








강건(robust)




아니오




17/24




7




5/9




graph











*원본은 허위 둘레선을 구분 없이 모두 보고 후 길이 단계에서 중단. robust는 R2로
7개 기각·R4로 길이 5개 산출.



강건 계측기 최종 구성 (별도 클래스, 원본 보존)



BodyMeasureRobust = R1(실패 격리·무크래시) + R2(둘레선 유효성 검증) + R4(비다양체-허용 길이). R3(유두점
반경 확대)는 시각 검증으로 기각. 원본 BodyMeasure·러너 baseline은 그대로.



최종 draft_sh3/



manuscript.tex/.pdf/.bbl,
references.bib

reliability.csv, jump_stats.csv

make_reliability.py, make_figures.py, make_jump_stats.py

figures/ hip_original/improved.png breast_r001/r300.png jump_robust.png



논문 흐름: 신뢰성(Table 1·hip 곡선) → 유두점 민감도(R3 기각) → 임의 자세 강건성(Table 2·점프 그림, R1/R2/R4) → 결론. draft_sh2(분할 품질)·draft_sh3(계측 신뢰성)가 독립 두 편으로
정리됐습니다.





















OneNote에서 작성되었습니다.
