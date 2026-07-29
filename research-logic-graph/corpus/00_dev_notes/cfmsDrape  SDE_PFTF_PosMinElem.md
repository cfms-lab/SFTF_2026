# cfmsDrape  SDE_PFTF_PosMinElem

Source: `D:\__SFTF_Projects(2026)\_dev_notes\cfmsDrape  SDE_PFTF_PosMinElem.mht`

cfmsDrape : SDE_PFTF_PosMinElem









2026년 7월 8일
수요일



오후 12:48












1)SDE_PFTF_PosMinElem 
= 16



cfmsdrape2026-dev)
d:\__VSCode_Projects\cfmsDrape2026_dev>uv run python
scripts/bench_pftf_oblique.py



zip=자살색종이_oblique.zip frames=1200 
gravity=(1,1,1) dir



[off ] 93.95 ms/step skips(sum)= 0 
finite=True



[pos ] 101.66 ms/step skips(sum)= 
451197 finite=True



[cone] 96.09 ms/step skips(sum)= 0 
finite=True






===== vs off =====



off : 
93.95 ms/step speedup x1.000 max|Δ vs off|=0.000000 cm



pos : 
101.66 ms/step speedup
x0.924 max|Δ vs off|=0.000000 cm



cone: 
96.09 ms/step speedup x0.978 max|Δ vs off|=0.000000 cm






VERDICT: pos no-gain
(skips=451197, x0.924)






2)SDE_PFTF_PosMinElem 
= 64



(cfmsdrape2026-dev)
d:\__VSCode_Projects\cfmsDrape2026_dev>uv run python
scripts/bench_pftf_oblique.py



zip=자살색종이_oblique.zip frames=1200 
gravity=(1,1,1) dir



[off ] 93.44 ms/step skips(sum)= 0 
finite=True



[pos ] 99.49 ms/step skips(sum)= 
156807 finite=True



[cone] 96.99 ms/step skips(sum)= 0 
finite=True






===== vs off =====



off : 
93.44 ms/step speedup x1.000 max|Δ vs off|=0.000000 cm



pos : 
99.49 ms/step speedup x0.939 max|Δ vs off|=0.000000 cm



cone: 
96.99 ms/step speedup x0.963 max|Δ vs off|=0.000000 cm






VERDICT: pos no-gain
(skips=156807, x0.939)






3)SDE_PFTF_PosMinElem = 128



(cfmsdrape2026-dev)
d:\__VSCode_Projects\cfmsDrape2026_dev>uv run python
scripts/bench_pftf_oblique.py



zip=자살색종이_oblique.zip frames=1200 
gravity=(1,1,1) dir



[off ] 93.74 ms/step skips(sum)= 0 
finite=True



[pos ] 98.54 ms/step skips(sum)= 
141177 finite=True



[cone] 97.37 ms/step skips(sum)= 0 
finite=True






===== vs off =====



off : 
93.74 ms/step speedup x1.000 max|Δ vs off|=0.000000 cm



pos : 
98.54 ms/step speedup x0.951 max|Δ vs off|=0.000000 cm



cone: 
97.37 ms/step speedup x0.963 max|Δ vs off|=0.000000 cm






VERDICT: pos no-gain
(skips=141177, x0.951)






4)SDE_PFTF_PosMinElem = 256



(cfmsdrape2026-dev)
d:\__VSCode_Projects\cfmsDrape2026_dev>uv run python
scripts/bench_pftf_oblique.py



zip=자살색종이_oblique.zip frames=1200 
gravity=(1,1,1) dir



[off ] 94.26 ms/step skips(sum)= 0 
finite=True



[pos ] 99.06 ms/step skips(sum)= 
76922 finite=True



[cone] 95.56 ms/step skips(sum)= 0 
finite=True






===== vs off =====



off : 
94.26 ms/step speedup x1.000 max|Δ vs off|=0.000000 cm



pos : 
99.06 ms/step speedup x0.952 max|Δ vs off|=0.000000 cm



cone: 
95.56 ms/step speedup x0.986 max|Δ vs off|=0.000000 cm






VERDICT: pos no-gain
(skips=76922, x0.952)






결과가 명확하네요 —
그리고 이건 결정적인(그리고 논문에 좋은) 결론입니다.



스윕 요약 (오블리크, 이상적 케이스)











T (MinElem)




pos/off




skips/step








1 (게이트 없음)




0.725 (−38%)




4,595








16




0.924




376








64




0.939




131








128




0.951 (−5%)




118








256




0.952




64








cone(게이트
off, refit만)




0.96–0.99




0











high-level
게이트가 −38%를 −5%까지 끌어올렸지만, T를 아무리 키워도 x0.95에서 평평해지고 절대 1.0을 넘지 못합니다. 프룬을 4595→64/step로 줄여도 손해가 −5%로
남습니다.



왜 못 넘나 — refit 바닥



남은
−5%는 디스크립터
유지(refit) 세금입니다. pos 슬랩을 매 스텝
모든 리프에서 갱신해야(테스트하려면 슬랩이 있어야 하니까) 하고, 그 자체가 ~5%입니다. 결정적 증거: **게이트가 꺼진 cone 모드조차
refit만으로 −3%**입니다(프룬 0인데 느림). 즉 게이트가 아끼는 것보다 디스크립터를 들고 있는 비용이 더 큽니다 — 18-DOP도 narrow phase(방향무관 근접)도 이미 값싸서 아낄
게 없기 때문입니다. 이건 튜닝으로 못 넘는 구조적 바닥입니다.



결정적 결론



PFTF 방향 컬링(cone/pos)은 이 엔진에서 이기지 못합니다 —
축정렬·오블리크·게이트·T-스윕 전부, 모든 구성에서 5~38% 손해, 그러나 항상 byte-identical(건전). 5개 데이터포인트가 단조롭게 −5%
바닥으로 수렴하니 더 볼 것 없습니다. layer-aware BVH도 refit 바닥은 그대로라 잘해야 ~parity — 큰 작업 대비
무의미합니다.



이건 강한 정직 결과입니다 (논문용)



"좁게
이긴다"보다 **"값싼 broad phase(9-slab k-DOP) + 값싼 방향무관 narrow phase 앞에서는,
방향 디스크립터 유지 비용(3~5%)이 절감분을 초과해 어떤 파라미터로도 못 이긴다"**가 훨씬 깔끔한 경계 결과입니다.
VisCull의 "depth-bound가 방향컬을 포섭" + 앞선 "18-DOP가 오리엔티드 슬랩을
포섭"과 한 세트로, **"상위 자료구조가 이미 값쌀 때 방향 컬링은 순손실"**이라는 일관된 메시지가 됩니다.



실무 결론



PFTF 컬링은 off 유지(이미 기본값). auto-disable도 이 케이스(131
skips/step)는 못 잡으니, 정직하게는 이 엔진에서 방향 컬링을 성능 기능으로
홍보하지 않기가 맞습니다.



이 스윕 표 + 최종
판정을 draft/pftf_pos_culling_audit_2026-07-08.md에 확정 기록으로 추가해 둘까요? (원하시면 논문 kDop의
"언제 손해인가" 절 문단도 초안 잡아드리겠습니다.) 소득이 없어 보여도, 정직하게 닫힌 negative result를 하나 확보한 겁니다 — 이게 리뷰에서 오히려 신뢰를 삽니다.





















OneNote에서 작성되었습니다.
