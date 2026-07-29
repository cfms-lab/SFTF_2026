"""Build a text-first corpus for the cross-project SFTF research logic graph."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path


SOURCE_EXTENSIONS = {".tex", ".md", ".txt"}
BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "table", "h1", "h2", "h3", "h4",
    "h5", "h6", "blockquote", "pre",
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"style", "script", "head"}:
            self.hidden_depth += 1
        elif not self.hidden_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script", "head"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif not self.hidden_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape("".join(self.parts)).replace("\xa0", " ")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r" *\n *", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


def mht_to_text(path: Path) -> str:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_type() != "text/html":
            continue
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        parser = TextExtractor()
        parser.feed(payload.decode(charset, errors="replace"))
        return parser.text()
    raise ValueError(f"No HTML body found in {path}")


def safe_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣._ -]+", "_", name).strip() or "untitled"


def build(workspace: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing corpus: {output}")
    output.mkdir(parents=True)
    manifest: list[tuple[str, str, str]] = []

    notes_out = output / "00_dev_notes"
    notes_out.mkdir()
    notes_root = workspace / "_dev_notes"
    for source in sorted(notes_root.glob("*.mht"), key=lambda p: p.name.lower()):
        destination = notes_out / f"{safe_name(source.stem)}.md"
        body = mht_to_text(source)
        destination.write_text(
            f"# {source.stem}\n\n"
            f"Source: `{source}`\n\n"
            f"{body}\n",
            encoding="utf-8",
        )
        manifest.append(("dev_note", str(source), str(destination.relative_to(output))))

    projects_out = output / "10_project_drafts"
    projects_out.mkdir()
    for project in sorted(workspace.iterdir(), key=lambda p: p.name.lower()):
        draft = project / "draft"
        if not project.is_dir() or not draft.is_dir():
            continue
        sources = [
            path for path in draft.iterdir()
            if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
        ]
        if not sources:
            continue
        project_out = projects_out / safe_name(project.name)
        project_out.mkdir()
        for source in sorted(sources, key=lambda p: p.name.lower()):
            if source.suffix.lower() == ".tex":
                destination = project_out / f"{source.name}.md"
                latex = source.read_text(encoding="utf-8", errors="replace")
                destination.write_text(
                    f"# LaTeX source: {source.name}\n\n"
                    f"Source: `{source}`\n\n"
                    f"{latex}\n",
                    encoding="utf-8",
                )
            else:
                destination = project_out / source.name
                shutil.copy2(source, destination)
            manifest.append(("draft", str(source), str(destination.relative_to(output))))

    lines = [
        "# Research logic graph corpus manifest",
        "",
        "This corpus is intentionally text-first. It includes converted `_dev_notes` MHT files and",
        "top-level draft `.tex`, `.md`, and `.txt` sources. PDFs, DOCX files, images, bibliography",
        "databases, generated artifacts, and nested draft assets are excluded to reduce duplication.",
        "",
        f"- Total source documents: {len(manifest)}",
        f"- Development notes: {sum(kind == 'dev_note' for kind, _, _ in manifest)}",
        f"- Draft sources: {sum(kind == 'draft' for kind, _, _ in manifest)}",
        "",
        "| Kind | Original source | Corpus file |",
        "|---|---|---|",
    ]
    lines.extend(f"| {kind} | `{source}` | `{target}` |" for kind, source, target in manifest)
    (output / "CORPUS_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built {len(manifest)} documents at {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.workspace.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
