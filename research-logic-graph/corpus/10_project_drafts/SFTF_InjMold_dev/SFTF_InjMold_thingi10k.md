# Thingi10K real-part audit — superseded

이 파일의 초기 n=8 감사는 표본 확대(2026-06-29, n=45)와 전면 재검증(2026-07-02,
n=46)으로 대체되었습니다. 현행 보고서와 데이터:

- 보고서: `draft/SFTF_InjMold_realparts.md` (R7, off-principal 46개)
- 정본 매니페스트: `../sftf_Mesh_Data/thingi10k_off_ingest_manifest.json`
- 스크리닝: `../sftf_Mesh_Data/thingi10k_screen.json` (302개 코퍼스, 후보 139개)
- 재현: `uv run python scripts/reverify_thingi10k.py --corpus-names <screen.json>`
