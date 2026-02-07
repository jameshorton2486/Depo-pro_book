from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from prompts.expander import EXPANDER_PROMPT


class Expander:
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        self.config = config
        self.exporter = exporter
        self.cost_tracker = cost_tracker
        self.log_path = log_path

    def _log_api(self, model: str, step: str, section: int, input_tokens: int, output_tokens: int, cost: float, success: bool, error: str | None = None) -> None:
        line = (
            f"{datetime.utcnow().isoformat()} | model={model} | step={step} | section={section} | "
            f"input_tokens={input_tokens} | output_tokens={output_tokens} | cost={cost:.6f} | success={success}"
        )
        if error:
            line += f" | error={error}"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _call_with_retry(self, call_fn):
        delay = 2
        for attempt in range(3):
            try:
                return call_fn()
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("Retry loop failed unexpectedly.")

    def expand_section(self, section: dict, draft: str, chapter_dir: Path) -> str:
        prompt = f"Expand this chapter:\n\n{draft}"
        self.exporter.save_prompt(chapter_dir, "expansion-prompt.md", prompt)

        client = OpenAI(api_key=self.config.openai_api_key)
        model = self.config.openai_model

        def _call():
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXPANDER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8000,
            )

        try:
            response = self._call_with_retry(_call)
            text = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
            cost = self.cost_tracker.log_api_call(model, input_tokens, output_tokens, section["number"], "expand")
            self._log_api(model, "expand", section["number"], input_tokens, output_tokens, cost, True)
            return text
        except Exception as exc:
            self._log_api(model, "expand", section["number"], 0, 0, 0.0, False, str(exc))
            raise
