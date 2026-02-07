from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class CostTracker:
    PRICES = {
        "claude": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
        "gpt-4o": {"input": 2.5 / 1_000_000, "output": 10.0 / 1_000_000},
        "gemini": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
    }

    def __init__(self, logs_dir: Path):
        self.costs_path = logs_dir / "costs.json"
        self.costs_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list:
        if not self.costs_path.exists():
            return []
        return json.loads(self.costs_path.read_text(encoding="utf-8"))

    def _save(self, data: list) -> None:
        self.costs_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _price_key(self, model: str) -> str:
        model_lower = model.lower()
        if "claude" in model_lower:
            return "claude"
        if "gpt" in model_lower:
            return "gpt-4o"
        if "gemini" in model_lower:
            return "gemini"
        return "gpt-4o"

    def log_api_call(self, model: str, input_tokens: int, output_tokens: int, section_number: int, step_name: str) -> float:
        key = self._price_key(model)
        prices = self.PRICES[key]
        cost = input_tokens * prices["input"] + output_tokens * prices["output"]
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "section": section_number,
            "step": step_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 6),
        }
        data = self._load()
        data.append(entry)
        self._save(data)
        return cost

    def get_section_cost(self, section_number: int) -> float:
        data = self._load()
        return sum(entry["cost"] for entry in data if entry["section"] == section_number)

    def get_total_cost(self) -> float:
        data = self._load()
        return sum(entry["cost"] for entry in data)

    def get_cost_table(self) -> list[dict]:
        data = self._load()
        by_section = {}
        for entry in data:
            sec = entry["section"]
            by_section.setdefault(sec, 0.0)
            by_section[sec] += entry["cost"]
        return [{"section": sec, "cost": round(cost, 2)} for sec, cost in sorted(by_section.items())]
