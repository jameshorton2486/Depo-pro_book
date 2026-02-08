# CODEX_PUBLISHING_PROMPT.md — Multi-Format Publishing Expansion

This document describes the publishing expansion for BookForge v2: Kindle, paperback, Google Docs, and website exports.

---

## 1. Dependencies

Add to **requirements.txt** (if not already present):

- `python-docx>=1.1.0` — for DOCX generation (e.g. gdoc export).
- `weasyprint>=62.0` — for PDF generation when xelatex is not available (paperback fallback).

Install with:

```bash
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

---

## 2. Config files to create

Create these in the project so export can use them:

- **kindle-metadata.yaml** — Kindle EPUB metadata (title, author, language, etc.). Place in `bookforge/` or `bookforge/config/` and have BookExporter load it for `export_kindle()`.
- **paperback-header.tex** — LaTeX header for paperback PDF (margins, geometry, fonts). Used when xelatex is available.
- **paperback.css** — CSS for WeasyPrint when generating paperback PDF without LaTeX (margins, page size, typography).
- **website.css** — CSS for the website export (index.html and chapter HTML). Place in `exports/website/` or referenced by the website exporter.

Exact paths can be under `bookforge/config/` or next to the exporter; ensure `book_exporter.py` and any docx/website logic reference them correctly.

---

## 3. DocxExporter (gdoc export)

- Create **exporters/docx_exporter.py** (or equivalent) that:
  - Takes the final merged Markdown or chapter content.
  - Uses **python-docx** to build a .docx with title, headings, body text, and basic formatting.
  - Writes to `exports/gdoc/` (e.g. `mastering-legal-transcription.docx`).
- **book_exporter.py** should call this for the “gdoc” format so that `bookforge export gdoc` produces the file.

---

## 4. BookExporter updates

In **exporters/book_exporter.py** add (or keep) methods:

- **export_kindle()** — Build EPUB for Kindle (Pandoc with kindle-metadata.yaml). Output to `exports/kindle/`. Return path to the .epub file.
- **export_paperback()** — Build PDF for paperback: try xelatex with paperback-header.tex; if not available, use WeasyPrint with paperback.css. Output to `exports/paperback/`. Return path to the .pdf file.
- **export_gdoc()** — Use DocxExporter to produce a .docx in `exports/gdoc/`. Return path to the .docx file.
- **export_website()** — Generate `exports/website/index.html` and `exports/website/chapters/*.html` (and copy or embed website.css). Return path to the website directory or index.

Ensure paths and filenames match what the Action Plan expects (e.g. `mastering-legal-transcription.epub`, `mastering-legal-transcription.pdf`).

---

## 5. Export CLI

Update the **export** command in **bookforge.py** so it accepts:

- **epub**, **pdf**, **docx**, **html** (existing).
- **kindle** — runs `export_kindle()`.
- **paperback** — runs `export_paperback()`.
- **gdoc** — runs `export_gdoc()`.
- **website** — runs `export_website()`.
- **all** — runs all of the above (epub, pdf, docx, html, kindle, paperback, gdoc, website) and reports each output path.

Help text should list all options: `epub, pdf, docx, html, kindle, paperback, gdoc, website, all`.

---

## 6. Verification

After implementing:

1. `python bookforge.py export --help` — Lists epub, pdf, docx, html, kindle, paperback, gdoc, website, all.
2. Run each export format once (e.g. `export kindle`, `export paperback`, `export gdoc`, `export website`) and confirm output files appear under `bookforge/exports/` in the correct subfolders.
3. If Pandoc is missing, at least kindle/paperback/gdoc/website logic should not crash; Pandoc-dependent formats (epub, pdf) may report a clear error.

---

*End of CODEX_PUBLISHING_PROMPT.md*
