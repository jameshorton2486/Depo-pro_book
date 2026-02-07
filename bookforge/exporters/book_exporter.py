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
