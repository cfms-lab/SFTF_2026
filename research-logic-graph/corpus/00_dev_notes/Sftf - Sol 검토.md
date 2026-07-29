# Sftf - Sol 검토

Source: `D:\__SFTF_Projects(2026)\_dev_notes\Sftf - Sol 검토.mht`

Sftf - Sol 검토









2026년 7월 11일
토요일



오전 6:59









냉정한 결론



현재 투고본은
**PiAM 범위에는 잘 맞지만, 심사 결과는 “Major Revision과 Reject 사이”**로 봅니다. 제가 심사자라면 Major Revision을 주되, 수학적 차원 문제와 독립 검증을 해소하지 못하면
2차에서 Reject하겠습니다.



주관적 추정치는 다음과
같습니다.




편집자 단계 통과: 70–85%


첫 심사에서 Major
Revision: 40–50%


첫 심사에서 Reject: 45–55%


현 상태로 Minor
Revision/Accept: 5% 미만


대규모 보완 후 최종 accept: 35–50%


아래 핵심 실험과 이론 문제를 제대로
보완한다면: 60–75%




PiAM은 design
tool, process optimization, simulation, AM speed-up을 명시적으로 다루므로 주제 적합성은 좋습니다. PiAM Aims and
scope



좋은 점




SFTF를 정밀 최적화의 대체물이
아니라 TOMO/slicer 검증을 위한 warm start로 제한한 것은 현실적입니다.


top-20, ±10° 검증으로 평균
ratio 1.13, grid budget 3.57%라는 결과는 충분히 관심을 끕니다. 균일·무작위 budget-matched
control까지 둔 것도 좋습니다.


Happy 50k 실패 사례를 숨기지
않고 AVE로 처리하며 과적합 가능성도 인정합니다. 이런 정직한 서술은 심사자에게 긍정적입니다.


35개 메시까지 timing
audit을 확장한 점과 구현 규모별 비용을 보여준 점도 장점입니다.




Accept를 위협하는 핵심 문제




독립적인 물리·slicer 검증이 없습니다.




방법은 TOMO를
학습·검증 기준으로 삼고 최종 성능도 다시 TOMO grid에 대해 측정합니다. 본문에는 “commercial-slicer-based
optimum”이 비교 대상으로 적혀 있지만 실제 Cura/PrusaSlicer 또는 실물 출력 결과는 없습니다. 따라서 심사자는 “SFTF가
TOMO의 특성을 근사한 것인지, 실제 support material을 예측하는지”를 구분할 수 없습니다.



직접적인 2024년
경쟁 연구는 산업 부품 orientation을 Cura로 평가하고 있어, 현 원고의 검증 수준과 대비될 수 있습니다. Efficient
part orientation algorithm for additive manufacturing in industrial
applications




“Unified tensor”의 차원 일관성이 설명되지 않습니다.




본문 정의대로라면
face-to-face 항은 \(A_iA_j\)를 포함해 면적의 제곱 차원이고, ground 항은 \(A_i\)만 포함해 면적 차원입니다.
그런데 Eq. (8–10)에서 두 항을 하나의 텐서로 더하고 “exact unified Rayleigh contribution”이라고
해석합니다. 후단의 rank normalization은 이 텐서 합 자체의 차원 문제를 해결하지 못합니다.



또한 핵심 기여를
“asymmetric tensor”라고 하지만, 주 cost가 \(n^TF_sn\)이라면 반대칭 성분은 Rayleigh
contraction에서 사라집니다. 즉 비대칭성이 최종 예측에 어떤 고유 정보를 주는지 명확하지 않습니다. 수학·최적화 심사자가 잡으면
Reject 사유까지 될 수 있습니다.




일반화 검증이 생각보다 훨씬 작고 일부 누수가 있습니다.



주 정확도 결과는 5개 메시입니다.


AVE threshold는 이 5개
메시에서 in-sample입니다.


A–E audit의 Group C는
동일한 Bunny/Manikin/Dragon/Happy/Lucy이므로 전체 audit을 완전한 held-out으로 부르기
어렵습니다.


35개 중 19개는 TOMO 값이 0
이하라 ratio 분석에서 제외되어, 실제 유효 표본은 16개뿐입니다. A와 B는 각각 1개만 남습니다.


LOMO 표에서는 가장 어려운
Happy 50k가 빠진 4개만 평가됩니다. 그 평균으로 PCA와 Support Tensor보다 낫다고 결론 내리면 선택적 제외로
보일 수 있습니다.





현재의
“held-out”, “generalization” 표현은 증거보다 강합니다. mesh-family 단위 outer CV와 Happy 포함
평가가 필요합니다.




속도 비교가 end-to-end 비교가 아닙니다.




실제 배치 방식은
SFTF 후보 생성 + local TOMO verification + 필요 시 AVE인데, timing headline은 주로 SFTF
candidate evaluation과 exhaustive TOMO를 비교합니다. 최종 파이프라인 전체 wall-clock이 없습니다.
C++은 “pure computation time”이고 TOMO는 DLL 호출 시간이므로 측정 경계도 다릅니다.



더구나 본문은 A–E
timing을 3° sweep이라고 하지만, Supplementary Table S1 caption은 TOMO_CPU/CUDA를 1°
exhaustive sweep이라고 명시합니다. 이는 반드시 정정해야 할 직접적 모순입니다.




재현성이 논문 내부에서 충분하지 않습니다.




가중치 7개를 어떻게
학습했는지—목적함수, optimizer, regularization, candidate-level 의존성 처리, random seed—가
명확하지 않습니다. coarse 후보 수 이후의 refinement 개수, NMS 각도, ray tolerance, mesh
preprocessing도 재현하기 어렵습니다.



Data/code
statement도 “요청 시 제공, acceptance 후 공개” 수준입니다. 계산 논문에서는 masked reviewer
repository가 사실상 필요합니다. PiAM도 double-anonymous 심사에서 익명 데이터 링크 제공 방법을 안내하고 있습니다. PiAM
submission and research-data guidelines



이전 작업 기록상
reviewer snapshot은 준비된 적이 있지만, 이번 검토에서는 현재 공개 상태를 재검증하지 않았습니다.



즉시 보이는 완성도 문제




본문이 Supplementary
Table S6를
인용하지만 보충자료에는 S1–S5만 있습니다.


Fig. 3 내부에는 아직
happy-method라는 개발 중 명칭이 남아 있지만 본문과 캡션은 AVE라고 부릅니다.


Supplementary Figs.
S6–S7은 경계의 마커·라벨이 잘려 보입니다.


참고문헌 15는
특허번호·출원기관·URL이 없고, Thingi10K arXiv 번호는 160504797로 잘못 표기되어 있습니다.


Word metadata 기준
4,883 words입니다. PiAM Research Paper 권고는 2,000–4,000 words이므로 실제 산정 범위를
확인해야 합니다. 보충자료가 실제로 DOCX로 업로드됐다면, 공식 지침은 text SI를 PDF로 제출하도록 요구합니다. PiAM submission
guidelines




가장 효과적인 보완 순서




10개 이상의 완전
held-out 산업 메시에서 Cura/PrusaSlicer support volume으로 검증


\(A_iA_j\)와 \(A_i\)의
차원을 통일하거나, ground/face 항을 별도로 무차원화


Happy를 포함한
family-held-out nested CV와 35개 전체를 다루는 zero-support metric 제시


SFTF+local TOMO+AVE의
전체 wall-clock 및 동일 조건 비교


익명 repository 링크와 정확한
reproduction command 제공


S6 누락, 1°/3° 모순,
happy-method 명칭, 참고문헌·그림 clipping 수정




요약하면, 아이디어는 출판 가치가 있고 PiAM에도 맞습니다. 그러나 현재 증거는 강한 headline에
비해 작고, 수학적 차원 문제와 검증 누수가 심사자의 신뢰를 흔들 수 있습니다. 응용 중심 심사자라면 Major Revision,
계산·수학 중심 심사자라면 Reject 가능성이 더 큽니다.



참고로 DOCX의
텍스트·표·저장된 페이지 구분과 포함된 그림은 전부 검사했지만, LibreOffice와 Word 자동 페이지 렌더링은 두 경로 모두 시간
초과되어 완전한 페이지별 시각 QA는 완료하지 못했습니다.


















OneNote에서 작성되었습니다.
