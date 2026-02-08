from __future__ import annotations

from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from prompts.master_writer import MASTER_WRITER_PROMPT
from agents.base_agent import BaseAgent


class Writer(BaseAgent):
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        super().__init__(config, exporter, cost_tracker, log_path)

    def _build_draft_prompt(self, section: dict, research_content: str, additional_context: str, subsections: Optional[list[str]] = None) -> str:
        subs = subsections or section.get("subsections", [])
        bullets = "\n".join(f"- {item}" for item in subs)
        elements = "\n".join(f"- {item}" for item in section.get("specific_elements", []))
        diagrams = "\n".join(f"- {item}" for item in section.get("diagrams", []))
        return (
            f"Write Section {section['number']}: {section['title']}  {section['subtitle']}\n"
            f"Part: {section['part']}\n"
            f"Word target: {section['word_target']} words\n\n"
            "Subsections to cover:\n"
            f"{bullets}\n\n"
            "RESEARCH (verified facts to incorporate):\n"
            f"{research_content}\n\n"
            f"Source notes: {section.get('source_notes', '')}\n\n"
            "Specific elements to include:\n"
            f"{elements}\n\n"
            "Diagrams to mark:\n"
            f"{diagrams}\n\n"
            f"{additional_context}".strip()
        )

    def draft_section(self, section: dict, research_content: str = "", additional_context: str = "", chapter_dir: Path | None = None, prompt_name: str = "writing-prompt.md") -> str:
        if chapter_dir is None:
            raise ValueError("chapter_dir is required for saving prompts.")
        prompt = self._build_draft_prompt(section, research_content, additional_context)
        self.exporter.save_prompt(chapter_dir, prompt_name, prompt)

        client = Anthropic(api_key=self.config.anthropic_api_key)
        model = self.config.claude_model

        def _call():
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                system=MASTER_WRITER_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response

        try:
            response = self._call_with_retry(_call, "draft", section["number"])
            text = response.content[0].text
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            cost = self.cost_tracker.log_api_call(model, input_tokens, output_tokens, section["number"], "draft")
            self._log_api(model, "draft", section["number"], input_tokens, output_tokens, cost, True)
            return text
        except Exception as exc:
            self._log_api(model, "draft", section["number"], 0, 0, 0.0, False, str(exc))
            if "context" in str(exc).lower() and len(section.get("subsections", [])) > 1:
                return self._draft_with_batches(section, research_content, additional_context, chapter_dir)
            raise

    def _draft_with_batches(self, section: dict, research_content: str, additional_context: str, chapter_dir: Path) -> str:
        subsections = section.get("subsections", [])
        chunks = [subsections[i : i + 3] for i in range(0, len(subsections), 3)]
        outputs = []
        for idx, chunk in enumerate(chunks, start=1):
            prompt = self._build_draft_prompt(section, research_content, additional_context, subsections=chunk)
            prompt_name = f"writing-prompt-part-{idx}.md"
            self.exporter.save_prompt(chapter_dir, prompt_name, prompt)
            client = Anthropic(api_key=self.config.anthropic_api_key)
            model = self.config.claude_model
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                system=MASTER_WRITER_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            cost = self.cost_tracker.log_api_call(model, input_tokens, output_tokens, section["number"], f"draft-part-{idx}")
            self._log_api(model, f"draft-part-{idx}", section["number"], input_tokens, output_tokens, cost, True)
            outputs.append(text)
        return "\n\n".join(outputs)

    def revise_section(
        self,
        section: dict,
        draft: str,
        expansion_notes: str,
        fact_report: str,
        review_report: str,
        human_notes: str = "",
        chapter_dir: Path | None = None,
        prompt_name: str = "revision-prompt.md",
    ) -> str:
        if chapter_dir is None:
            raise ValueError("chapter_dir is required for saving prompts.")
        prompt = (
            "Revise this chapter draft incorporating all feedback below.\n\n"
            "CURRENT DRAFT:\n"
            f"{draft}\n\n"
            "CONTENT TO ADD (from expansion review):\n"
            f"{expansion_notes}\n\n"
            "FACT-CHECK CORRECTIONS (fix all INCORRECT and OUTDATED items):\n"
            f"{fact_report}\n\n"
            "QUALITY REVIEW (address all issues scored below 8):\n"
            f"{review_report}\n\n"
            "AUTHOR NOTES:\n"
            f"{human_notes or 'No additional notes.'}\n\n"
            "INSTRUCTIONS:\n"
            "- Fix all factual errors identified in the fact-check report.\n"
            "- Incorporate the best expansion suggestions naturally.\n"
            "- Address all quality issues from the review.\n"
            "- Maintain the Style Bible voice throughout.\n"
            "- Keep the 3-Layer structure for every subsection.\n"
            "- Output the complete revised chapter as clean Markdown."
        )
        self.exporter.save_prompt(chapter_dir, prompt_name, prompt)

        client = Anthropic(api_key=self.config.anthropic_api_key)
        model = self.config.claude_model

        def _call():
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                system=MASTER_WRITER_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response

        try:
            response = self._call_with_retry(_call, "revise", section["number"])
            text = response.content[0].text
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            cost = self.cost_tracker.log_api_call(model, input_tokens, output_tokens, section["number"], "revise")
            self._log_api(model, "revise", section["number"], input_tokens, output_tokens, cost, True)
            return text
        except Exception as exc:
            self._log_api(model, "revise", section["number"], 0, 0, 0.0, False, str(exc))
            if "context" in str(exc).lower():
                return self._revise_with_batches(section, draft, expansion_notes, fact_report, review_report, human_notes, chapter_dir)
            raise

    def _revise_with_batches(
        self,
        section: dict,
        draft: str,
        expansion_notes: str,
        fact_report: str,
        review_report: str,
        human_notes: str,
        chapter_dir: Path,
    ) -> str:
        parts = draft.split("### ")
        header = parts[0]
        subsections = ["### " + part for part in parts[1:]] if len(parts) > 1 else [draft]
        outputs = [header.strip()]
        for idx, subsection in enumerate(subsections, start=1):
            prompt = (
                "Revise this chapter subsection incorporating all feedback below.\n\n"
                "CURRENT SUBSECTION:\n"
                f"{subsection}\n\n"
                "CONTENT TO ADD (from expansion review):\n"
                f"{expansion_notes}\n\n"
                "FACT-CHECK CORRECTIONS (fix all INCORRECT and OUTDATED items):\n"
                f"{fact_report}\n\n"
                "QUALITY REVIEW (address all issues scored below 8):\n"
                f"{review_report}\n\n"
                "AUTHOR NOTES:\n"
                f"{human_notes or 'No additional notes.'}\n\n"
                "INSTRUCTIONS:\n"
                "- Fix all factual errors identified in the fact-check report.\n"
                "- Incorporate the best expansion suggestions naturally.\n"
                "- Address all quality issues from the review.\n"
                "- Maintain the Style Bible voice throughout.\n"
                "- Keep the 3-Layer structure for every subsection.\n"
                "- Output the complete revised subsection as clean Markdown."
            )
            prompt_name = f"revision-prompt-part-{idx}.md"
            self.exporter.save_prompt(chapter_dir, prompt_name, prompt)
            client = Anthropic(api_key=self.config.anthropic_api_key)
            model = self.config.claude_model
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                system=MASTER_WRITER_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            input_tokens = getattr(response.usage, "input_tokens", 0)
            output_tokens = getattr(response.usage, "output_tokens", 0)
            cost = self.cost_tracker.log_api_call(model, input_tokens, output_tokens, section["number"], f"revise-part-{idx}")
            self._log_api(model, f"revise-part-{idx}", section["number"], input_tokens, output_tokens, cost, True)
            outputs.append(text.strip())
        return "\n\n".join(output for output in outputs if output)
