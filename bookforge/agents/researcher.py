from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

from prompts.researcher import RESEARCHER_PROMPT


class Researcher:
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

    def research_section(self, section: dict, chapter_dir: Path) -> str:
        subsections = "\n".join(f"- {item}" for item in section.get("subsections", []))
        elements = "\n".join(f"- {item}" for item in section.get("specific_elements", []))
        diagrams = "\n".join(f"- {item}" for item in section.get("diagrams", []))
        prompt = (
            f"{RESEARCHER_PROMPT}\n\n"
            f"Research Section {section['number']}: {section['title']}\n"
            f"Subsections:\n{subsections}\n\n"
            f"Specific elements:\n{elements}\n\n"
            f"Diagrams to support:\n{diagrams}\n"
        )
        self.exporter.save_prompt(chapter_dir, "research-prompt.md", prompt)

        model_name = self.config.gemini_model
        genai.configure(api_key=self.config.google_api_key)
        model = genai.GenerativeModel(model_name)

        def _call():
            return model.generate_content(prompt)

        try:
            response = self._call_with_retry(_call)
            text = response.text
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            cost = self.cost_tracker.log_api_call(model_name, input_tokens, output_tokens, section["number"], "research")
            self._log_api(model_name, "research", section["number"], input_tokens, output_tokens, cost, True)
            return text
        except Exception as exc:
            self._log_api(model_name, "research", section["number"], 0, 0, 0.0, False, str(exc))
            raise
