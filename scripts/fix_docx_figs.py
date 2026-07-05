#!/usr/bin/env python3
"""
fix_docx_figs.py — pandoc로 만든 .docx 안의 PDF 그림을 PNG로 교체한다.

배경:
    LaTeX 소스가 \\includegraphics{*.pdf} 로 벡터 그림을 넣으면, pandoc은 그 PDF를
    그대로 .docx 안(word/media/*.pdf)에 박는다. 그런데 MS Word는 PDF를 그림으로
    표시하지 못해 해당 그림들이 빈칸/깨진 이미지로 보인다.
    이 스크립트는 docx 안에 박힌 PDF 그림만 골라 PNG로 래스터화하고,
    관계(rels)와 [Content_Types].xml을 갱신해 Word에서 정상 표시되도록 만든다.

의존성:
    pip install pymupdf      # 외부 프로그램 불필요 (Windows에 가장 무난)

사용법 (draft 폴더 기준 자동 경로):
    python scripts/fix_docx_figs.py                     # draft/SFTF_draft_eng.docx -> *_fixed.docx
    python scripts/fix_docx_figs.py path/to/in.docx -o out.docx
    python scripts/fix_docx_figs.py --inplace           # 원본 덮어쓰기(.bak 백업 생성)
    python scripts/fix_docx_figs.py --dpi 300           # 해상도 지정(기본 220)

pandoc 변환 직후 한 줄 덧붙여 자동화에 끼워 넣으면 된다.
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys
import tempfile
import zipfile

DEFAULT_DOCX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "draft", "SFTF_draft_eng.docx",
)


def rasterize_pdf(pdf_path: str, png_path: str, dpi: int) -> tuple[int, int]:
    """PDF 1페이지를 PNG로 렌더링. (width, height) px 반환."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("[fix_docx_figs] PyMuPDF가 필요합니다.  pip install pymupdf")
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(png_path)
    doc.close()
    return pix.width, pix.height


def fix_docx(src: str, out: str, dpi: int) -> int:
    if not os.path.isfile(src):
        sys.exit(f"[fix_docx_figs] 입력 파일을 찾을 수 없습니다: {src}")

    tmp = tempfile.mkdtemp(prefix="docxfix_")
    try:
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            z.extractall(tmp)

        pdf_media = [n for n in names
                     if n.startswith("word/media/") and n.lower().endswith(".pdf")]
        if not pdf_media:
            print("[fix_docx_figs] 교체할 PDF 그림이 없습니다. 그대로 복사합니다.")
            if os.path.abspath(src) != os.path.abspath(out):
                shutil.copyfile(src, out)
            return 0

        mapping: dict[str, str] = {}  # old member -> new member
        for rel in pdf_media:
            pdf_path = os.path.join(tmp, rel)
            png_member = rel[:-4] + ".png"
            png_path = os.path.join(tmp, png_member)
            w, h = rasterize_pdf(pdf_path, png_path, dpi)
            os.remove(pdf_path)
            mapping[rel] = png_member
            print(f"  {os.path.basename(rel)} -> {os.path.basename(png_member)}  {w}x{h}px")

        # word/_rels/document.xml.rels : Target 경로의 .pdf -> .png
        rels_path = os.path.join(tmp, "word", "_rels", "document.xml.rels")
        _replace_in_file(rels_path, [
            (f'Target="{o[len("word/"):]}"', f'Target="{n[len("word/"):]}"')
            for o, n in mapping.items()
        ])

        # [Content_Types].xml : application/pdf override -> image/png
        ct_path = os.path.join(tmp, "[Content_Types].xml")
        ct = open(ct_path, encoding="utf-8").read()
        for o, n in mapping.items():
            ct = ct.replace(
                f'<Override PartName="/{o}" ContentType="application/pdf" />',
                f'<Override PartName="/{n}" ContentType="image/png" />',
            )
        if 'Extension="png"' not in ct:
            ct = ct.replace("</Types>", '<Default Extension="png" ContentType="image/png" /></Types>')
        open(ct_path, "w", encoding="utf-8").write(ct)

        # 원본 멤버 순서를 유지하며 재패키징(이름만 .pdf->.png 로 치환)
        out_dir = os.path.dirname(os.path.abspath(out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        if os.path.exists(out):
            os.remove(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for n in names:
                member = mapping.get(n, n)
                z.write(os.path.join(tmp, member), member)
        return len(mapping)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _replace_in_file(path: str, replacements):
    s = open(path, encoding="utf-8").read()
    for a, b in replacements:
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


def main():
    ap = argparse.ArgumentParser(description="pandoc docx의 PDF 그림을 PNG로 교체")
    ap.add_argument("input", nargs="?", default=DEFAULT_DOCX,
                    help=f"입력 .docx (기본: {DEFAULT_DOCX})")
    ap.add_argument("-o", "--output", help="출력 .docx (기본: 입력명_fixed.docx)")
    ap.add_argument("--inplace", action="store_true",
                    help="원본을 덮어쓴다(.bak 백업 생성)")
    ap.add_argument("--dpi", type=int, default=220, help="래스터화 해상도(기본 220)")
    args = ap.parse_args()

    src = args.input
    if args.inplace:
        backup = src + ".bak"
        if not os.path.exists(backup):
            shutil.copyfile(src, backup)
            print(f"[fix_docx_figs] 백업 생성: {backup}")
        out = src
        # 같은 경로로 쓰면 안 되므로 임시 파일에 만든 뒤 교체
        tmp_out = src + ".tmp.docx"
        n = fix_docx(src, tmp_out, args.dpi)
        os.replace(tmp_out, out)
    else:
        out = args.output or (os.path.splitext(src)[0] + "_fixed.docx")
        n = fix_docx(src, out, args.dpi)

    print(f"[fix_docx_figs] 완료: {out}  (그림 {n}개 변환)")


if __name__ == "__main__":
    main()
