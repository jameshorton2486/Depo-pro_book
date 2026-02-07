from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

PIPELINE_VERSION = "2.0"


class MarkdownExporter:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.console = Console()

    def _front_matter(self, section: dict, step_name: str) -> str:
        timestamp = datetime.utcnow().isoformat()
        return (
            "---\n"
            f"section: {section['number']}\n"
            f"title: \"{section['title']}\"\n"
            f"generated: \"{timestamp}\"\n"
            f"pipeline_version: \"{PIPELINE_VERSION}\"\n"
            f"step: \"{step_name}\"\n"
            "---\n\n"
        )

    def save_file(self, chapter_dir: Path, subfolder: str, filename: str, content: str, section: dict, step_name: str) -> Path:
        target_dir = chapter_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        full_path = target_dir / filename
        payload = self._front_matter(section, step_name) + content.strip() + "\n"
        full_path.write_text(payload, encoding="utf-8")
        self.console.print(f"[dim]{full_path}[/dim]")
        return full_path

    def load_file(self, chapter_dir: Path, subfolder: str, filename: str) -> Optional[str]:
        full_path = chapter_dir / subfolder / filename
        if not full_path.exists():
            return None
        return full_path.read_text(encoding="utf-8")

    def save_prompt(self, chapter_dir: Path, filename: str, prompt_content: str) -> Path:
        target_dir = chapter_dir / "prompts"
        target_dir.mkdir(parents=True, exist_ok=True)
        full_path = target_dir / filename
        full_path.write_text(prompt_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[dim]{full_path}[/dim]")
        return full_path
