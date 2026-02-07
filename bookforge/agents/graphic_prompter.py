from __future__ import annotations

from prompts.graphic_generator import generate_graphic_tasks


class GraphicPrompter:
    def generate_graphic_tasks(self, text: str, section: dict) -> tuple[str, str]:
        return generate_graphic_tasks(text, section["number"])
