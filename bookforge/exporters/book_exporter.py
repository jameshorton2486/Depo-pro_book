from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

class BookExporter:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.exports_dir = project_root / "exports"
        self.chapters_dir = project_root / "chapters"
        self.console = Console()

    def _check_pandoc(self) -> None:
        if not shutil.which("pandoc"):
            raise RuntimeError("Pandoc not found. Install Pandoc and ensure it is on PATH.")

    def _check_xelatex(self) -> None:
        if not shutil.which("xelatex"):
            raise RuntimeError("xelatex not found. Install TeX Live/MiKTeX with xelatex.")

    def compile_finals(self) -> list[str]:
        files = []
        if not self.chapters_dir.exists():
            return files
        for chapter_dir in sorted(self.chapters_dir.glob("[0-9][0-9]-*")):
            final_dir = chapter_dir / "final"
            if not final_dir.exists():
                continue
            for md in final_dir.glob("*.md"):
                files.append(str(md))
        toc_path = self.project_root / "config" / "toc.json"
        if toc_path.exists():
            expected = []
            data = json.loads(toc_path.read_text(encoding="utf-8"))
            for section in data.get("sections", []):
                expected.append(f"{section['number']:02d}-{section['slug']}.md")
            existing = {Path(path).name for path in files}
            missing = [name for name in expected if name not in existing]
            if missing:
                self.console.print("[yellow]Warning: Missing final chapters:[/yellow]")
                for name in missing:
                    self.console.print(f"[dim]- {name}[/dim]")
        return files

    def _run(self, cmd: list[str]) -> None:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Pandoc failed with unknown error.")

    def export_epub(self) -> Path:
        self._check_pandoc()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")
        output = self.exports_dir / "mastering-legal-transcription.epub"
        cmd = ["pandoc", "metadata.yaml"] + files + ["--toc", "-o", str(output)]
        self._run(cmd)
        return output

    def export_pdf(self) -> Path:
        self._check_pandoc()
        self._check_xelatex()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")
        output = self.exports_dir / "mastering-legal-transcription.pdf"
        base_cmd = [
            "pandoc",
            "metadata.yaml",
            *files,
            "--pdf-engine=xelatex",
            "--toc",
            "--toc-depth=2",
            "-V",
            "geometry:margin=1in",
            "-V",
            "fontsize=11pt",
            "-V",
            "documentclass=book",
            "-o",
            str(output),
        ]
        try:
            self._run(base_cmd)
        except RuntimeError as exc:
            fallback_cmd = base_cmd[:-2] + [
                "-V",
                "mainfont=DejaVu Serif",
                "-V",
                "monofont=DejaVu Sans Mono",
                "-o",
                str(output),
            ]
            self._run(fallback_cmd)
        return output

    def export_docx(self) -> Path:
        self._check_pandoc()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")
        output = self.exports_dir / "mastering-legal-transcription.docx"
        cmd = ["pandoc", "metadata.yaml"] + files + ["--toc", "--toc-depth=2", "-o", str(output)]
        self._run(cmd)
        return output

    def export_html(self) -> Path:
        self._check_pandoc()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")
        output = self.exports_dir / "mastering-legal-transcription.html"
        css_path = self.exports_dir / "style.css"
        if not css_path.exists():
            css_path.write_text(
                "body { font-family: Georgia, serif; line-height: 1.6; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }\n"
                "code, pre { font-family: 'Courier New', monospace; }\n"
                "h1, h2, h3 { color: #1b3a4b; }\n",
                encoding="utf-8",
            )
        cmd = [
            "pandoc",
            "metadata.yaml",
            *files,
            "--standalone",
            "--toc",
            "--toc-depth=2",
            f"--css={css_path}",
            "-o",
            str(output),
        ]
        self._run(cmd)
        return output

    def export_kindle(self) -> Path:
        self._check_pandoc()
        output_dir = self.exports_dir / "kindle"
        output_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")
        output = output_dir / "mastering-legal-transcription.epub"
        metadata = self.project_root / "config" / "kindle-metadata.yaml"
        cmd = [
            "pandoc",
            str(metadata),
            *files,
            "--toc",
            "--toc-depth=2",
            "--epub-chapter-level=1",
            "-o",
            str(output),
        ]
        self._run(cmd)
        return output

    def _check_weasyprint(self) -> None:
        try:
            import weasyprint  # noqa: F401
        except Exception as exc:
            raise RuntimeError(f"WeasyPrint not available: {exc}") from exc

    def export_paperback(self) -> Path:
        self._check_pandoc()
        output_dir = self.exports_dir / "paperback"
        output_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")
        output = output_dir / "mastering-legal-transcription.pdf"

        if shutil.which("xelatex"):
            header_path = self.project_root / "config" / "paperback-header.tex"
            cmd = [
                "pandoc",
                "metadata.yaml",
                *files,
                "--pdf-engine=xelatex",
                "--toc",
                "--toc-depth=2",
                "-V",
                "geometry:paperwidth=6in,paperheight=9in,inner=0.75in,outer=0.5in,top=0.75in,bottom=0.75in",
                "-V",
                "fontsize=11pt",
                "-V",
                "documentclass=book",
                "-V",
                "classoption=twoside",
                "-V",
                "mainfont=Georgia",
                "-V",
                "monofont=Courier New",
                "--include-in-header",
                str(header_path),
                "-o",
                str(output),
            ]
            self._run(cmd)
            return output

        self._check_weasyprint()
        html_path = output_dir / "paperback.html"
        css_path = self.project_root / "config" / "paperback.css"
        cmd = [
            "pandoc",
            "metadata.yaml",
            *files,
            "--standalone",
            "--toc",
            "--toc-depth=2",
            "-o",
            str(html_path),
        ]
        self._run(cmd)
        from weasyprint import HTML

        HTML(filename=str(html_path)).write_pdf(str(output), stylesheets=[str(css_path)])
        return output

    def export_gdoc(self) -> Path:
        try:
            from exporters.docx_exporter import DocxExporter
        except Exception as exc:
            raise RuntimeError(f"python-docx not available: {exc}") from exc
        exporter = DocxExporter(self.project_root)
        return exporter.export()

    def export_website(self) -> Path:
        self._check_pandoc()
        output_dir = self.exports_dir / "website"
        chapters_dir = output_dir / "chapters"
        output_dir.mkdir(parents=True, exist_ok=True)
        chapters_dir.mkdir(parents=True, exist_ok=True)
        files = self.compile_finals()
        if not files:
            raise RuntimeError("No final chapter files found to export.")

        source_css_path = self.project_root / "config" / "website.css"
        css_path = output_dir / "style.css"
        shutil.copy2(source_css_path, css_path)
        template_path = self.project_root / "config" / "website-template.html"
        index_path = output_dir / "index.html"

        cmd = [
            "pandoc",
            "metadata.yaml",
            *files,
            "--standalone",
            "--toc",
            "--toc-depth=2",
            f"--css={css_path}",
            f"--template={template_path}",
            "-o",
            str(index_path),
        ]
        self._run(cmd)

        for md_path in files:
            name = Path(md_path).name
            html_name = name.replace(".md", ".html")
            chapter_out = chapters_dir / html_name
            chapter_cmd = [
                "pandoc",
                str(md_path),
                "--standalone",
                "--toc",
                "--toc-depth=2",
                f"--css=../style.css",
                "-o",
                str(chapter_out),
            ]
            self._run(chapter_cmd)
        return output_dir

    def _pandoc_html(self, md_path: Path) -> str:
        cmd = ["pandoc", str(md_path), "--from", "markdown", "--to", "html"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Pandoc HTML conversion failed.")
        return result.stdout

    def export_site(self) -> Path:
        self._check_pandoc()
        site_dir = self.exports_dir / "site"
        assets_dir = site_dir / "assets"
        chapters_dir = site_dir / "chapters"
        assets_dir.mkdir(parents=True, exist_ok=True)
        chapters_dir.mkdir(parents=True, exist_ok=True)

        css_path = assets_dir / "style.css"
        if not css_path.exists():
            css_path.write_text(
                ":root { --bg: #f6f2ee; --ink: #1b2a2f; --accent: #1f4e5f; --muted: #6b7b83; --card: #ffffff; }\n"
                "body { margin: 0; font-family: 'Georgia', 'Times New Roman', serif; background: radial-gradient(circle at top, #ffffff 0%, var(--bg) 55%); color: var(--ink); }\n"
                "a { color: var(--accent); text-decoration: none; }\n"
                "a:hover { text-decoration: underline; }\n"
                "header { padding: 2.5rem 1.5rem 1.5rem; border-bottom: 1px solid #e0d8d0; }\n"
                "header h1 { margin: 0; font-size: 2.2rem; letter-spacing: 0.02em; }\n"
                "header p { margin: 0.5rem 0 0; color: var(--muted); }\n"
                ".container { max-width: 980px; margin: 0 auto; padding: 1.5rem; }\n"
                ".grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }\n"
                ".card { background: var(--card); border: 1px solid #e6dfd8; padding: 1rem; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.05); }\n"
                ".card h3 { margin: 0 0 0.5rem; font-size: 1.1rem; }\n"
                ".chapter { background: var(--card); padding: 2rem; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.06); }\n"
                ".chapter h1 { color: var(--accent); }\n"
                ".chapter nav { margin-bottom: 1.5rem; font-size: 0.95rem; }\n"
                ".chapter nav a { color: var(--muted); }\n"
                ".toc { margin: 0; padding: 0; list-style: none; }\n"
                ".toc li { margin: 0.3rem 0; }\n"
                "footer { padding: 2rem 1.5rem 3rem; color: var(--muted); text-align: center; }\n",
                encoding="utf-8",
            )

        toc_path = self.project_root / "config" / "toc.json"
        toc = json.loads(toc_path.read_text(encoding="utf-8")) if toc_path.exists() else {"sections": []}

        chapter_links = []
        for section in toc.get("sections", []):
            chapter_dir = self.chapters_dir / f"{section['number']:02d}-{section['slug']}"
            md_path = chapter_dir / "final" / f"{section['number']:02d}-{section['slug']}.md"
            slug = f"{section['number']:02d}-{section['slug']}"
            html_path = chapters_dir / f"{slug}.html"
            if md_path.exists():
                body_html = self._pandoc_html(md_path)
                html = (
                    "<!doctype html>\n"
                    "<html lang=\"en\">\n"
                    "<head>\n"
                    f"  <meta charset=\"utf-8\" />\n  <title>{section['title']}</title>\n"
                    "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
                    f"  <link rel=\"stylesheet\" href=\"../assets/style.css\" />\n"
                    "</head>\n"
                    "<body>\n"
                    "  <header>\n"
                    f"    <h1>{section['title']}</h1>\n"
                    f"    <p>Part: {section.get('part', '')}</p>\n"
                    "  </header>\n"
                    "  <main class=\"container\">\n"
                    "    <div class=\"chapter\">\n"
                    "      <nav><a href=\"../index.html\">← Back to contents</a></nav>\n"
                    f"{body_html}\n"
                    "    </div>\n"
                    "  </main>\n"
                    "  <footer>BookForge Web Edition</footer>\n"
                    "</body>\n"
                    "</html>\n"
                )
                html_path.write_text(html, encoding="utf-8")
                chapter_links.append((section, f"chapters/{slug}.html", True))

                graphics_dir = chapter_dir / "graphics"
                if graphics_dir.exists():
                    target_graphics_dir = assets_dir / "graphics" / slug
                    target_graphics_dir.mkdir(parents=True, exist_ok=True)
                    for asset in graphics_dir.glob("*.*"):
                        shutil.copy2(asset, target_graphics_dir / asset.name)
            else:
                chapter_links.append((section, f"chapters/{slug}.html", False))

        cards = []
        for section, href, exists in chapter_links:
            status = "Available" if exists else "Coming soon"
            cards.append(
                "<div class=\"card\">"
                f"<h3>{section['number']}. {section['title']}</h3>"
                f"<p>{section.get('subtitle', '')}</p>"
                f"<p><strong>{status}</strong></p>"
                + (f"<a href=\"{href}\">Read chapter →</a>" if exists else "")
                + "</div>"
            )
        cards_html = "\n".join(cards)

        index_html = (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\" />\n  <title>BookForge Web Edition</title>\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
            "  <link rel=\"stylesheet\" href=\"assets/style.css\" />\n"
            "</head>\n"
            "<body>\n"
            "  <header>\n"
            "    <h1>Mastering Legal Transcription</h1>\n"
            "    <p>Web edition generated by BookForge.</p>\n"
            "  </header>\n"
            "  <main class=\"container\">\n"
            "    <section class=\"grid\">\n"
            f"{cards_html}\n"
            "    </section>\n"
            "  </main>\n"
            "  <footer>BookForge Web Edition</footer>\n"
            "</body>\n"
            "</html>\n"
        )

        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(index_html, encoding="utf-8")
        return site_dir
