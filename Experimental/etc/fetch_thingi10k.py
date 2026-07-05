#!/usr/bin/env python3
"""
fetch_thingi10k.py  —  네트워크가 되는 '본인 PC'에서 실행하세요.
(이 도구가 도는 샌드박스는 외부 다운로드가 막혀 있어 여기서는 못 받습니다.)

설치:
    pip install "thingi10k[clip]"      # CLIP 시맨틱 검색 포함
    # 시맨틱 검색이 필요 없으면:  pip install thingi10k

동작:
    1) Thingi10K 'raw' 변형(원본 STL/OBJ)을 받아 캐시
    2) 아래 4개 프리셋으로 모델을 필터링/검색해 ./thingi10k_out/<프리셋>/ 으로 복사
       - robustness : 견고성 테스트용 결함 메쉬 (self-intersection / non-manifold / open)
       - large      : 대용량 성능 테스트용 고폴리곤 메쉬
       - mechanical : 기계 CAD 류 (gear/bracket/impeller ... CLIP 검색)
       - organic    : 유기 곡면 (bunny/dragon ... CLIP 검색; 주의: 정식 스캔본은
                      Thingi10K가 아니라 Stanford repo / 3dbenchy.com 사용 — 가이드 참고)

사용:
    python fetch_thingi10k.py                 # 전체 프리셋
    python fetch_thingi10k.py robustness large
    python fetch_thingi10k.py --per 8 mechanical
"""
import os, sys, shutil, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", nargs="*",
                    default=["robustness", "large", "mechanical", "organic"])
    ap.add_argument("--per", type=int, default=5, help="프리셋당 받을 최대 개수")
    ap.add_argument("--out", default="thingi10k_out")
    ap.add_argument("--cache", default=None, help="데이터셋 캐시 경로(선택)")
    args = ap.parse_args()

    import thingi10k
    # raw 변형 = 원본 메쉬 파일(STL/OBJ). 결함을 '있는 그대로' 보존하므로
    # 견고성 테스트에 필수. (기본 npz는 정제된 numpy 배열이라 결함 검증엔 부적합)
    thingi10k.init(variant="raw", cache_dir=args.cache)

    # (필터 키, dataset()에 넘길 kwargs, CLIP 쿼리 리스트)
    PRESETS = {
        # 견고성: 데이터셋의 진짜 가치. 45% self-intersect, 22% non-manifold 등
        "robustness": dict(self_intersecting=True, closed=False),
        # 대용량: 면 수 상한 없이 50만+ 페이셋
        "large":      dict(num_facets=(500_000, None)),
        # 기계 CAD: 시맨틱 검색
        "mechanical": dict(_queries=["mechanical gear housing", "metal L bracket",
                                     "motor mount", "pump impeller", "machined block"]),
        # 유기 곡면: 시맨틱 검색 (정식 스캔본 아님 — 가이드의 정식 출처 사용 권장)
        "organic":    dict(_queries=["stanford bunny rabbit", "dragon statue",
                                     "armadillo figure", "human head bust", "toy boat"]),
    }

    os.makedirs(args.out, exist_ok=True)
    for name in args.presets:
        if name not in PRESETS:
            print(f"[skip] 알 수 없는 프리셋: {name}"); continue
        cfg = dict(PRESETS[name]); queries = cfg.pop("_queries", [None])
        dst = os.path.join(args.out, name); os.makedirs(dst, exist_ok=True)
        got = 0
        for q in queries:
            kw = dict(cfg)
            if q is not None:
                kw["query"] = q
            for entry in thingi10k.dataset(**kw):
                if got >= args.per:
                    break
                src = entry["file_path"]
                fid = entry["file_id"]
                lic = entry.get("license", "unknown")
                ext = os.path.splitext(src)[1] or ".stl"
                out = os.path.join(dst, f"{fid}{ext}")
                try:
                    shutil.copy(src, out)
                    with open(os.path.join(dst, "MANIFEST.csv"), "a") as m:
                        m.write(f"{fid},{lic},{q or ''}\n")
                    got += 1
                    print(f"[{name}] {fid}  ({lic})")
                except Exception as e:
                    print(f"[{name}] {fid} 복사 실패: {e}")
            if got >= args.per:
                break
        print(f"  -> {name}: {got}개 저장  ({dst})\n")

    print("완료. 각 폴더의 MANIFEST.csv 에 file_id 와 라이선스가 기록됩니다.")
    print("논문/제안서에는 file_id 와 라이선스를 반드시 함께 인용하세요.")

if __name__ == "__main__":
    main()
