from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from prompts.checker import CHECKER_PROMPT
from agents.base_agent import BaseAgent


class Checker(BaseAgent):
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        super().__init__(config, exporter, cost_tracker, log_path)

    def _call_with_web_search(self, client: OpenAI, model: str, prompt: str):
        try:
            return client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": CHECKER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                tools=[{"type": "web_search"}],
            )
        except Exception as exc:
            from rich.console import Console
            Console().print(f"[yellow]⚠ Web search unavailable: {exc}[/yellow]")
            Console().print("[yellow]  Fact-checking will use model knowledge only (no live web verification).[/yellow]")
            return None

    def check_section(self, section: dict, draft: str, expansion_notes: str, chapter_dir: Path) -> str:
        combined = f"{draft}\n\n{expansion_notes}" if expansion_notes else draft
        prompt = f"Fact-check the following chapter:\n\n{combined}"
        self.exporter.save_prompt(chapter_dir, "fact-check-prompt.md", prompt)

        client = OpenAI(api_key=self.config.openai_api_key)
        model = self.config.openai_model

        def _call():
            web_response = self._call_with_web_search(client, model, prompt)
            if web_response is not None:
                return web_response
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": CHECKER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8000,
            )

        try:
            response = self._call_with_retry(_call, "fact_check", section["number"])
            if hasattr(response, "output_text"):
                text = response.output_text
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
            else:
                text = response.choices[0].message.content
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(usage, "completion_tokens", 0) or 0
            cost = self.cost_tracker.log_api_call(model, input_tokens, output_tokens, section["number"], "fact_check")
            self._log_api(model, "fact_check", section["number"], input_tokens, output_tokens, cost, True)
            return text
        except Exception as exc:
            self._log_api(model, "fact_check", section["number"], 0, 0, 0.0, False, str(exc))
            raise
