from __future__ import annotations

from pathlib import Path

try:
    from google import genai
    from google.genai import types
    _GENAI_MODE = "new"
except Exception:
    import google.generativeai as genai
    _GENAI_MODE = "legacy"

from prompts.reviewer import REVIEWER_PROMPT
from agents.base_agent import BaseAgent


class Reviewer(BaseAgent):
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        super().__init__(config, exporter, cost_tracker, log_path)

    def review_section(self, section: dict, draft: str, chapter_dir: Path) -> str:
        user_prompt = f"Review this chapter:\n\n{draft}"
        full_prompt = f"{REVIEWER_PROMPT}\n\n{user_prompt}"
        self.exporter.save_prompt(chapter_dir, "review-prompt.md", full_prompt)

        model_name = self.config.gemini_model
        if _GENAI_MODE == "new":
            client = genai.Client(api_key=self.config.google_api_key)

            def _call():
                return client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(system_instruction=REVIEWER_PROMPT),
                )

            try:
                response = self._call_with_retry(_call, "review", section["number"])
                text = getattr(response, "text", "") or ""
                usage = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
                input_tokens = (
                    getattr(usage, "prompt_token_count", 0)
                    or getattr(usage, "input_tokens", 0)
                    or getattr(usage, "prompt_tokens", 0)
                    or 0
                )
                output_tokens = (
                    getattr(usage, "candidates_token_count", 0)
                    or getattr(usage, "output_tokens", 0)
                    or getattr(usage, "completion_tokens", 0)
                    or 0
                )
                cost = self.cost_tracker.log_api_call(model_name, input_tokens, output_tokens, section["number"], "review")
                self._log_api(model_name, "review", section["number"], input_tokens, output_tokens, cost, True)
                return text
            except Exception as exc:
                self._log_api(model_name, "review", section["number"], 0, 0, 0.0, False, str(exc))
                raise

        genai.configure(api_key=self.config.google_api_key)
        model = genai.GenerativeModel(model_name, system_instruction=REVIEWER_PROMPT)

        def _legacy_call():
            return model.generate_content(user_prompt)

        try:
            response = self._call_with_retry(_legacy_call, "review", section["number"])
            text = response.text
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            cost = self.cost_tracker.log_api_call(model_name, input_tokens, output_tokens, section["number"], "review")
            self._log_api(model_name, "review", section["number"], input_tokens, output_tokens, cost, True)
            return text
        except Exception as exc:
            self._log_api(model_name, "review", section["number"], 0, 0, 0.0, False, str(exc))
            raise
