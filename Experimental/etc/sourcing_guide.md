# TOO_TSE6_DEV 검증용 3D 메쉬 수집 가이드

## 먼저: 솔직한 두 가지

**1. 이 도구 환경에서는 바이너리 메쉬를 직접 다운로드할 수 없습니다.**
작업 샌드박스가 외부 호스트(Thingi10K 서버·GitHub·Stanford·Printables 등)로의 네트워크가 모두
차단되어 있습니다. 그래서 Group A·B는 *절차적으로 생성*해 드렸고(아래), Group C·D는
본인 PC에서 실행할 스크립트와 검증된 직접 링크로 드립니다.

**2. 요청하신 "깨끗한 이름 형상 20개"는 검증 목표와 부분적으로 어긋납니다.**
지정하신 우선순위는 *견고성(깨진 메쉬)* 과 *성능(대용량)* 입니다. 그런데 Cube·Gear·Bunny 같은
정상 형상은 모두 watertight·정상 메쉬라, 파서/처리 파이프라인의 **견고성을 전혀 자극하지 못합니다.**
Thingi10K의 진짜 가치는 바로 그 결함 메쉬 비율에 있습니다(공식 통계):

| 결함 | 비율 |
|---|---|
| non-solid (열린/비solid) | 50% |
| self-intersection | 45% |
| 다중 컴포넌트 | 26% |
| non-manifold | 22% |
| degenerate face | 16% |
| 위상적으로 열림(open) | 11% |

→ **권장 구성**: 이름으로 고른 정상 형상은 *이론 검증용*으로만 쓰고, 견고성 셋은 형상 이름이 아니라
**결함 속성으로 필터링**해서 별도로 확보하세요. `fetch_thingi10k.py`의 `robustness`·`large`
프리셋이 그 역할을 합니다.

---

## Group A — 기본 형상 (5개) · 생성 완료

이론 검증/디버깅용으로는 다운로드보다 **생성본이 더 낫습니다**(해석적으로 정확, 좌표·치수 기지).
`validation_meshes/` 에 binary STL로 제공. 전부 watertight·2-manifold 검증 통과(단위 mm).

| 파일 | 형상 | 삼각형 | 치수 |
|---|---|---|---|
| A1_cube.stl | Cube | 12 | 20×20×20 |
| A2_sphere.stl | Sphere | 2,976 | ⌀20 |
| A3_cylinder.stl | Cylinder | 192 | ⌀16×20 |
| A4_cone.stl | Cone | 96 | ⌀16×20 |
| A5_torus.stl | Torus | 2,304 | 32×32×8 |

## Group B — Concave 형상 (5개) · 생성 완료

오버행·내부 캐비티 특성을 갖도록 설계. 마찬가지로 전부 watertight·2-manifold.

| 파일 | 형상 | 삼각형 | 검증 특성 |
|---|---|---|---|
| B1_u_bracket.stl | U-Bracket | 28 | 슬롯 오버행 |
| B2_hook.stl | Hook | 1,560 | 곡선 스윕·급격한 오버행 |
| B3_c_clamp.stl | C-Clamp | 28 | C자 개구부 |
| B4_pipe_elbow.stl | Pipe Elbow | 2,400 | 90° 중공 관(내벽) |
| B5_hollow_box.stl | Hollow Box | 24 | **완전 밀폐 내부 캐비티**(이중 셸) |

> 참고: 더 "거친 실물" 변종이 필요하면 Group C·D에서 Thingiverse 원본을 받으세요.
> 생성본은 의도적으로 깨끗해서 견고성보다는 알고리즘 정확도 검증에 적합합니다.

---

## Group C — 기계 CAD (5개) · 본인 PC에서 수집

심사위원이 선호하는 "실제 산업 부품" 류. 두 가지 경로:

**(a) Thingi10K에서 시맨틱 검색** — `fetch_thingi10k.py mechanical`
CLIP 쿼리(gear housing / L bracket / motor mount / impeller / machined block)로 근사 매칭.
장점: 라이선스·메타데이터가 데이터셋에 정리되어 인용이 깔끔. 단점: 베타 기능이라 결과가 들쭉날쭉.

**(b) CAD 정식 테스트셋** — 더 "정품 CAD"스러운 B-rep/STEP이 필요하면:
- **ABC Dataset** (100만+ CAD 모델, STEP+메쉬): https://deep-geometry.github.io/abc-dataset/
- **FabWave / MFCAD** 등 기계부품 라벨 데이터셋
- **GrabCAD** (수동 다운로드, 라이선스 개별 확인): https://grabcad.com/library

> 제안서·논문용이면 라벨이 명확한 ABC Dataset 쪽이 "산업 부품"이라는 주장에 더 강력합니다.

## Group D — 유기 형상 (5개) · 본인 PC에서 수집

**중요:** 이 5개 중 4개는 사실상 Thingi10K 출처가 아닙니다. 정식 출처를 쓰세요.

| 모델 | 정식 출처 | 비고 |
|---|---|---|
| Stanford Bunny | Stanford 3D Scanning Repository | PLY 원본, ~35k~70k면 |
| Stanford Dragon | 〃 | ~871k 삼각형(대용량 테스트 겸용) |
| Armadillo | 〃 | ~346k 삼각형 |
| Human Bust | 임의 — Thingiverse/Sketchfab 검색 또는 사진측량 스캔 | 정식 "표준본" 없음 |
| 3DBenchy | 공식 3dbenchy.com | 2025년 CC0 공개 도메인 전환 |

- Stanford repo: https://graphics.stanford.edu/data/3Dscanrep/
- 3DBenchy 다운로드: https://www.3dbenchy.com/download/ (라이선스: https://www.3dbenchy.com/license/ — CC0)
- 편의용 STL 변환 묶음(비공식): Printables "Stanford 3D Scanning Repository Models"

> Stanford Dragon/Armadillo는 그 자체로 **수십만~백만 삼각형**이라 Group D이면서 동시에
> *성능/대용량* 테스트 케이스로 재활용할 수 있습니다.

---

## 권장 최종 구성 (검증 목표 정렬)

| 목적 | 셋 | 출처 |
|---|---|---|
| 이론/정확도 검증 | Group A + B (생성본 10개) | 제공 완료 |
| 산업부품 시연(심사 대비) | Group C 5개 | `fetch_thingi10k.py mechanical` 또는 ABC |
| 곡면/유기 | Group D 5개 | Stanford repo + 3dbenchy.com |
| **견고성(핵심)** | 결함 메쉬 10~30개 | `fetch_thingi10k.py robustness` |
| **성능(핵심)** | 50만+ 면 메쉬 5~10개 | `fetch_thingi10k.py large` + Stanford Dragon |

## 실행 방법 (요약)

```bash
pip install "thingi10k[clip]"
python fetch_thingi10k.py                 # 4개 프리셋 모두
python fetch_thingi10k.py robustness large --per 10
```
각 출력 폴더의 `MANIFEST.csv`에 `file_id`와 라이선스가 기록됩니다.
**논문/제안서 인용 시 file_id와 라이선스를 반드시 함께 표기**하세요(Thingi10K 항목별 라이선스 상이).

## 인용

```
@article{Thingi10K,
  title={Thingi10K: A Dataset of 10,000 3D-Printing Models},
  author={Zhou, Qingnan and Jacobson, Alec},
  journal={arXiv preprint arXiv:1605.04797}, year={2016}
}
```
