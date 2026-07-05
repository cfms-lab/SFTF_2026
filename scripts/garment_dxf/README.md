# scripts/garment_dxf — 의복 블록 DXF(AAMA/ASTM) 생성기

치수만 주면 **실측 산업 제도법(Aldrich식 기본 블록)**으로 의복 패턴을 그려
**AAMA/ASTM 레이어 규약을 갖춘 DXF**를 로컬에서 찍어냅니다. GarmentCodeData 같은
합성 파라메트릭이 아니라, 실제로 재단·봉제할 수 있는 기본 블록(스커트/바디스/소매)이라
drape·CAD 파이프라인 테스트 입력으로 적합합니다. **외부 의존성 없음**(순수 파이썬;
미리보기 PNG에만 matplotlib 사용).

## 생성되는 블록

| 블록 | 파일명 | 비고 |
|---|---|---|
| 스커트 앞/뒤 | `skirt_front`, `skirt_back` | 직선 스커트 기본 블록(faithful). 허리 다트 + 엉덩이 곡선 옆선 |
| 바디스 앞/뒤 | `bodice_front`, `bodice_back` | 기본 바디스(simplified). 목둘레·진동·어깨경사·허리 다트 |
| 소매 | `sleeve` | 한장 소매(simplified). 앞/뒤 비대칭 소매산 + 밸런스 노치 |

> 스커트는 표준 기본 블록을 충실히 구현했고, 바디스/소매는 **단순화된 기본 드래프트**
> 입니다(깔끔하고 그럴듯하지만 그레이딩된 생산용 블록은 아님). 모든 치수는
> `drafting.Measurements`(cm)에서 파생됩니다.

## DXF 레이어 규약 (AAMA/ASTM)

| 레이어 | 내용 | 엔티티 |
|---|---|---|
| `1` | 외곽선(재단선) | 닫힌 POLYLINE |
| `8` | 다트·내부 구성선 | 열린 POLYLINE |
| `11` | 노치 | 짧은 LINE |
| `13` | 식서(그레인라인) | 화살표 LINE |
| `15` | 조각 라벨(이름/사이즈) | TEXT |

단위는 기본 **mm**(AAMA 관례). `--units cm` 로 cm 출력 가능. Lectra/Gerber/Optitex/
Seamly2D 등에서 임포트되는 R12 ASCII DXF입니다.

## 사용법

```bash
# 5개 블록 전부, 여성 사이즈 12, mm, 미리보기 PNG까지
uv run python scripts/garment_dxf/make_patterns.py --size 12 --preview

# 스커트만, 사이즈 14, cm 단위
uv run python scripts/garment_dxf/make_patterns.py --size 14 \
    --blocks skirt_front skirt_back --units cm

# 개별 치수 덮어쓰기(cm)
uv run python scripts/garment_dxf/make_patterns.py --size 12 --waist 72 --hip 98
```

사이즈 프리셋: `10, 12, 14, 16` (bust/waist/hip + 보조 치수, Aldrich식 표준 표).
결과는 `scripts/garment_dxf/out/` 에 조각별 `*.dxf` + `preview_szNN.png` 로 저장됩니다.
`out/` 폴더에 샘플(사이즈 12) DXF와 미리보기가 이미 들어 있습니다.

## 구조

- `drafting.py` — 측정값 프리셋 + 곡선(베지어)·다트 헬퍼 + `Piece` 자료형
- `blocks.py` — 스커트/바디스/소매 드래프팅 로직 → `Piece`
- `dxf_aama.py` — 의존성 없는 DXF(R12) **작성기 + 간이 판독기**
- `make_patterns.py` — CLI: 치수 → DXF 파일들 (+ 되읽어 그린 미리보기 PNG)

## 검증

`make_patterns.py --preview` 는 **생성한 DXF를 다시 읽어** 그림을 그립니다. 즉 미리보기가
나온다는 것은 파일이 정상적으로 파싱된다는 뜻(라운드트립 검증). 추가로 외부 검증을
원하면 `ezdxf`로 열어보면 됩니다:

```bash
uv pip install ezdxf
python -c "import ezdxf; d=ezdxf.readfile('scripts/garment_dxf/out/skirt_front_sz12.dxf'); print([e.dxftype() for e in d.modelspace()])"
```

## 커스터마이즈

- 새 사이즈: `drafting.PRESETS` 에 `Measurements(...)` 추가.
- 다트 분배·곡선 강도: `blocks.py` 의 각 `_skirt/_bodice/sleeve` 상수(예: `dart_take`,
  `side_take`, `shoulder_slope`, `cap`).
- 레이어 번호를 회사 표준에 맞춰 바꾸려면 `dxf_aama.py` 상단의 `LAYER_*` 와 `_LAYERS`.
- 더 정밀한 바디스/소매(그레이딩·정확한 Aldrich 좌표)가 필요하면 말씀 주세요 — 블록을
  교체/고도화해 드립니다.
