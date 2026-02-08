from __future__ import annotations

from pathlib import Path

try:
    from google import genai
    _GENAI_MODE = "new"
except Exception:
    import google.generativeai as genai
    _GENAI_MODE = "legacy"

from prompts.researcher import RESEARCHER_PROMPT
from agents.base_agent import BaseAgent


class Researcher(BaseAgent):
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        super().__init__(config, exporter, cost_tracker, log_path)

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
        if _GENAI_MODE == "new":
            client = genai.Client(api_key=self.config.google_api_key)

            def _call():
                return client.models.generate_content(model=model_name, contents=prompt)

            try:
                response = self._call_with_retry(_call, "research", section["number"])
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
                cost = self.cost_tracker.log_api_call(model_name, input_tokens, output_tokens, section["number"], "research")
                self._log_api(model_name, "research", section["number"], input_tokens, output_tokens, cost, True)
                return text
            except Exception as exc:
                self._log_api(model_name, "research", section["number"], 0, 0, 0.0, False, str(exc))
                raise

        genai.configure(api_key=self.config.google_api_key)
        model = genai.GenerativeModel(model_name)

        def _legacy_call():
            return model.generate_content(prompt)

        try:
            response = self._call_with_retry(_legacy_call, "research", section["number"])
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
