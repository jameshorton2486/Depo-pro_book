from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from prompts.expander import EXPANDER_PROMPT
from agents.base_agent import BaseAgent


class Expander(BaseAgent):
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        super().__init__(config, exporter, cost_tracker, log_path)

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
            response = self._call_with_retry(_call, "expand", section["number"])
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
