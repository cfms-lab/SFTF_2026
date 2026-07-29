# TDP submission artifact specification

## Reference template

- Source template: `D:\OneDrive\Documents\__PaperWorks\__InProgress\__SFTF논문작성(2026)\SFTF(2026)\2026-07-28_TDP_submit3\SFTF_style_template.dotx`
- SHA-256: `F20BF03494C8C2ED6D4E6A195BD911A0B109180B5AD2CD2BDBFE41826426308A`
- Blank reference DOCX derived from the same template: `D:\__SFTF_Projects(2026)\Tomo_SFTF_dev\draft\TDP_v2.1\_reference_style.docx`
- Reference DOCX SHA-256: `4C950A55DE7D65F9900C32DC6119D2959FFD98A7788953E93FD8EB8E22C6A232`

The template is intentionally minimal: it supplies page geometry, theme, numbering,
and named paragraph styles rather than branded headers, artwork, or boilerplate.

## Page system

- A4 portrait, one column.
- Margins: 0.5 in on every side.
- Header distance: approximately 0.591 in.
- Footer distance: approximately 0.689 in.
- No required header, footer, page number, watermark, or decorative image.

## Typography and hierarchy

- Normal/body: Times New Roman, 11 pt, justified, double spaced.
- Title: Times New Roman, 16 pt, bold, centered; 12 pt before and 6 pt after.
- Author: centered.
- Heading 1: 14 pt, bold.
- Heading 2: 12 pt, bold.
- Heading 3/4: bold.
- Abstract: template Abstract style, 5 pt before and 15 pt after.
- Figure and table captions: use the template's caption styles.

## Content slots

1. Article title.
2. Full author and affiliation block.
3. Unstructured abstract below 300 words.
4. At least four keywords.
5. Main body: Introduction, Materials and Methods, Results, Discussion,
   Conclusions.
6. Acknowledgments and AI-assistance disclosure.
7. Author Contributions.
8. Statements and Declarations with the journal-required subheadings.
9. Numbered Vancouver reference list.

The cover letter uses the same page geometry and type family but a compact,
left-aligned business-letter body.

## Fidelity gates

- Preserve the template theme, styles, numbering, section geometry, and A4 page
  setup.
- Preserve all six display equations as editable Word math and all seven figures
  from the manuscript source.
- Keep the main manuscript within the Original Article limits: abstract below
  300 words, main text below 4,000 words, no more than eight figures, no more
  than five tables, and no more than 100 references.
- Use author-year citations only as conversion input; final in-text citations
  must be numeric and the reference list must follow Sage Vancouver order.
- Do not add visual elements absent from the reference template.
- Render the final DOCX files through Microsoft Word and inspect every page for
  clipping, overflow, unintended blank pages, broken equations, and caption or
  table defects.
