from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class StatusTracker:
    def __init__(self, base_dir: Path):
        self.status_path = base_dir / "chapters" / "status.json"
        self.status_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.status_path.exists():
            return {}
        return json.loads(self.status_path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.status_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_status(self, section_number: int) -> dict:
        data = self._load()
        return data.get(str(section_number), {})

    def update_step(self, section_number: int, step_number: int, section: dict) -> None:
        data = self._load()
        entry = data.get(str(section_number), {})
        steps = set(entry.get("steps_completed", []))
        steps.add(step_number)
        entry.update(
            {
                "title": section.get("title"),
                "build_order": section.get("build_order"),
                "steps_completed": sorted(steps),
                "status": entry.get("status", "In Progress"),
                "last_updated": datetime.utcnow().isoformat(),
            }
        )
        data[str(section_number)] = entry
        self._save(data)

    def set_approved(self, section_number: int, section: dict) -> None:
        data = self._load()
        entry = data.get(str(section_number), {})
        entry.update(
            {
                "title": section.get("title"),
                "build_order": section.get("build_order"),
                "status": "Final",
                "last_updated": datetime.utcnow().isoformat(),
            }
        )
        data[str(section_number)] = entry
        self._save(data)

    def update_metrics(self, section_number: int, word_count: int, grade: float | None, score: float | None) -> None:
        data = self._load()
        entry = data.get(str(section_number), {})
        entry.update(
            {
                "word_count": word_count,
                "readability_grade": grade,
                "review_score": score,
                "last_updated": datetime.utcnow().isoformat(),
            }
        )
        data[str(section_number)] = entry
        self._save(data)

    def get_all_statuses(self) -> dict:
        return self._load()

    def get_progress(self, total_sections: int) -> tuple[int, int]:
        data = self._load()
        completed = sum(1 for entry in data.values() if entry.get("status") == "Final")
        return completed, total_sections
