from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


class BaseAgent:
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        self.config = config
        self.exporter = exporter
        self.cost_tracker = cost_tracker
        self.log_path = log_path

    def _log_api(
        self,
        model: str,
        step: str,
        section: int,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        line = (
            f"{datetime.utcnow().isoformat()} | model={model} | step={step} | section={section} | "
            f"input_tokens={input_tokens} | output_tokens={output_tokens} | cost={cost:.6f} | success={success}"
        )
        if error:
            line += f" | error={error}"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _call_with_retry(self, call_fn: Callable[[], T], step: str, section: int, attempts: int = 3) -> T:
        delay = 2
        for attempt in range(attempts):
            try:
                return call_fn()
            except Exception:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Retry loop failed unexpectedly for {step} section {section}.")
