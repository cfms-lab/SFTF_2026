# PFTF_kDOP의 novelty

Source: `D:\__SFTF_Projects(2026)\_dev_notes\PFTF_kDOP의 novelty.mht`

PFTF_kDOP의 novelty









2026년 7월 8일
수요일



오후 5:55









좋아.
그런데 특정 메쉬에 대해 최대 6% 이득인데, 이 정도로 SCI-E 저널에 투고 가능할까?



솔직하게
말씀드리겠습니다 — 그리고 핵심은 6%로 이 논문을 판단하면 안 된다는 것입니다.



6%는 이 논문의 기여가 아닙니다



6%는
Discussion의 배포 현실 각주입니다. 논문의 실제 기여는 세 가지입니다:



첫째, 증명된
안전성을 가진 방향 컬링입니다 — 거짓음성 0(합성 + 실의복 13벌 전부), 기존 리핏에 얹는 O(1) 유지, coherent 드레이프에서
트리 방문 최대 −99%·narrow 후보 중앙값 −71%. 이건 "빠르다"가 아니라 "공짜로 안전하게 후보를
줄이는 새 서술자"라는 알고리즘 기여입니다.



둘째, 미분가능
접촉장(M2)입니다 — sharp 극한 수렴 증명, 관통 132→0 해소 gradient, 마찰까지. 이건 속도가 아니라 새
능력(학습·최적화·물성추정과 연결)이라, 속도 지표와 무관하게 평가됩니다.



셋째, 정직한
부정 결과들 — Gaussian annealing이 접촉엔 unsound라는 발견, 그리고 배포 경계의 특성화. 리뷰어에 따라 이건
엄밀함의 증거로 읽힙니다.



즉
이건 "6% 빨라졌다" 논문이 아니라 "증명가능 안전한 방향 서술자 + 미분가능 접촉장" 논문입니다.



6%를 제대로 프레이밍하는 법



지금
원고에는 빠져 있는 결정적 논거가 하나 있습니다: 컬의 이득은
narrow phase 비용에 비례한다. cfmsDrape의 narrow phase가 유난히 싸서(방향무관 근접 테스트
한 줄) 99% 횟수 감소가 6% 시간으로 희석된 것이지, 비싼 narrow phase(정확 CCD, element-exact
접촉)를 쓰는 엔진에서는 같은 99% 횟수 감소가 큰 wall-clock으로 옮겨집니다. 즉 6%는 이 방법의 천장이
아니라, 가장 값싼 narrow phase를 상대로 한 바닥입니다. 이 문장을 넣으면 "6%뿐?"이라는 반박이
"6%는 최악 조건의 수치"로 뒤집힙니다.



정직한 리스크



과대포장은
안 하겠습니다. 리뷰어가 걸 만한 세 가지:



자체
엔진 하나에서만 검증됐다는 점(일반화·재현성). 브로드페이즈 브루트포스 ground truth와 합성 씬이 이를 일부 방어하지만, 레퍼런스
코드 공개나 두 번째 엔진/공개 데이터셋이 있으면 훨씬 강해집니다.



논문의
정직함(6% 공개, annealing unsound, 적층 한계)이 깐깐한 리뷰어에게는 무기가 될 수 있습니다 —
"저자도 이득이 미미하고 일반적으로 unsound라 인정한다"로 읽힐 위험. 프레이밍으로 이걸
"엄밀함"으로 돌려세워야 합니다(우리가 Discussion에서 이미 그 방향으로 썼습니다).



두
개(컬 + 접촉장)를 묶은 게 초점을 분산시킬 수 있습니다. 다만 대개는 "기여가 둘"이 플러스로 작용합니다.



판정



중급
SCI-E 그래픽스/CAD/텍스타일 저널이면 충분히 투고 가능합니다 — 단, 속도 논문이 아니라 방법·능력 논문으로 프레이밍했을 때. 현실적 후보: The Visual Computer, Computer Animation and Virtual
Worlds, Computers & Graphics, Computer-Aided Design, Textile Research
Journal, Fashion and Textiles 등. 반대로 TVCG/SIGGRAPH 같은 최상위에는 이
수치만으로는 부족합니다(거긴 2×+ 이득이나 훨씬 강한 신규성을 요구).



핵심은:
지금 원고를 abstract·intro부터 **"증명가능 안전한 방향 컬 + 미분가능 접촉장, 이득은 narrow phase 비용에
비례"**로 재배치하고, 6%는 Discussion의 정직한 배포 노트로 두는 것입니다. 지금도 그 구조에 가깝지만 intro가 아직
"속도"에 무게가 실려 있으면 조정할 여지가 있습니다.



원하시면
(a) intro/abstract를 "방법·능력 우선 + 이득은 narrow-phase 비용 비례" 논거로 재작성해
드리거나, (b) 타깃 저널 2–3곳의 최신 scope·SCI-E 등재 상태를 확인해 적합도를 비교해 드리겠습니다. 어느 쪽이 좋을까요?






출처:
<https://claude.ai/cowork/cse_018D9RKhEoMLebs3JGjUNX8H>






두 가지 다
완료했습니다.



(a) 재프레이밍 — 반영 완료



영문 논문의 intro
"Scope and honesty" 문단에 핵심 논거를
넣었습니다(재컴파일 11쪽, tex/pdf/docx 갱신 + 디바이스 반영):



컬이 줄이는 것은 traversal 횟수이고, 그
wall-clock 가치는 자기가 공급하는 narrow phase의 비용에 비례한다.
우리 엔진은 narrow phase가 일부러 값싸서 end-to-end 이득이 견실하지만 완만한 2–7%이지만, narrow phase가 정확
기하검사나 CCD인 파이프라인에서는 같은 최대 99% traversal 감소가 곧 지배 지표가 된다. 따라서 횟수 감소(엔진 무관)와
wall-clock 이득(이 엔진)을 분리해 보고하며, O(1)로 유지되는
증명가능-무손실 서술자 자체를 (특정 속도 수치가 아니라) 기여로 삼는다.



intro는 원래도
method-first였고(기여 1~4가 컬·구현·미분접촉·완화규칙, 헤드라인은 "false negatives=0"), 이제
6%가 "천장이 아니라 값싼 narrow phase에서의 바닥"임이 도입부에서 못박힙니다. 기존 abstract
캐비앗·Discussion과 일관됩니다.



(b) 저널 검토 (TRJ·F&T 제외)



전부 SCIE 등재·Q2권이고, 이 논문(자가충돌 컬 + 미분가능 접촉)과의 적합도
순으로:











저널




출판사




IF(대략)*




SCIE/분위




적합도




비고








Computer Animation and Virtual Worlds




Wiley




~1–3.4*




SCIE,
CS-SW




★★★ 최적




옷·캐릭터
애니메이션·물리기반 시뮬의 본진. 자가충돌+미분접촉 둘 다 정확히 scope. 상대적으로 문턱·속도 온건.








The Visual Computer




Springer




~2.9




SCIE, Q2




★★★ 강력




"Animation,
Simulation, Digital Humans" 포함, 폭넓은 그래픽스. 요즘 AI-그래픽스 지향이라 미분가능·학습 연결 각도가
유리.








Computers & Graphics




Elsevier




~2.7




SCIE, Q2




★★★ 강력




기하·모델링·시뮬·충돌
전반. 방법+재현성+정직한 평가를 높이 삼 → 부정결과(annealing unsound) 있는 이 논문에 우호적. SMI 특별호 채널도.








Computer-Aided Design




Elsevier




~3.2




SCIE, Q2




★★ 조건부




k-DOP·충돌검출·계산기하·의류
CAD 각도엔 잘 맞음. 단 미분가능 접촉/직물 동역학 절반은 fit이
약함 → 컬·기하 서술자 중심으로 프레이밍해야. 심사 느린 편.











*IF는 트래커마다
편차가 큽니다(특히 CAVW는 소스별 ~1~3.4). 투고 전 반드시 현재 JCR로
확인하시고, 실무에선 IF보다 scope 적합도가 게재 확률을 더 좌우합니다.



추천: 지금 원고(컬 + 미분접촉의 이중 기여, "이득은
narrow-phase 비용에 비례" 프레이밍)에는 CAVW를 1순위, The
Visual Computer / Computers & Graphics를 공동 2순위로 봅니다 — 셋 다 "미분가능
접촉"이라는 새 능력을 속도와 무관하게 평가해 줍니다. CAD는
미분접촉 절반을 덜어내고 "증명가능 안전한 방향 컬 + 의류 CAD 충돌" 단일 축으로 다시 쓸 때만 권합니다.



참고: IEEE TVCG(최상위)는 이 수치·단일엔진만으로는 reach이고, Graphical Models(Elsevier)는 기하 편향이라 컬만 강조하면 대안은
됩니다.



원하시면
1순위(CAVW) 기준으로 cover letter 초안과 저널
서식(레퍼런스 스타일·분량) 맞춤 체크를 해드리겠습니다. 어떻게 할까요?





















OneNote에서 작성되었습니다.
