from __future__ import annotations

from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from prompts.master_writer import MASTER_WRITER_PROMPT
from agents.base_agent import BaseAgent


class Writer(BaseAgent):
    def __init__(self, config, exporter, cost_tracker, log_path: Path):
        super().__init__(config, exporter, cost_tracker, log_path)

    def _build_draft_prompt(
        self,
        section: dict,
        research_content: str,
        additional_context: str,
        source_material: str = "",
        subsections: Optional[list[str]] = None,
    ) -> str:
        subs = subsections or section.get("subsections", [])
        bullets = "\n".join(f"- {item}" for item in subs)
        elements = "\n".join(f"- {item}" for item in section.get("specific_elements", []))
        diagrams = "\n".join(f"- {item}" for item in section.get("diagrams", []))

        parts = [
            f"Write Section {section['number']}: {section['title']} — {section['subtitle']}",
            f"Part: {section['part']}",
            f"Word target: {section['word_target']} words",
            "",
            "Subsections to cover:",
            bullets,
            "",
        ]

        # Source material block — the key upgrade
        if source_material:
            parts.append(source_material)
            parts.append("")

        if research_content:
            parts.append("RESEARCH (verified facts to incorporate):")
            parts.append(research_content)
            parts.append("")

        if section.get("source_notes"):
            parts.append(f"Author notes: {section['source_notes']}")
            parts.append("")

        if elements:
            parts.append("Specific elements to include:")
            parts.append(elements)
            parts.append("")

        if diagrams:
            parts.append("Diagrams to mark:")
            parts.append(diagrams)
            parts.append("")

        # Reinforcement block — prevents common AI writing failures
        parts.append("REMINDERS (enforce these throughout your output):")
        parts.append("- Write in PROSE PARAGRAPHS. Bullet lists are NOT acceptable for body content.")
        parts.append("- Every subsection needs: bold rule → story/stakes → transcript example.")
        parts.append("- Open the section with a 2–3 paragraph narrative SCENE, not a summary.")
        parts.append("- Transitions between subsections are natural sentences, never labels.")
        parts.append("- Maximum 1–2 callouts per subsection. Use blockquote format.")
        parts.append("- No fabricated case citations. If uncertain, describe the scenario generically.")
        parts.append("- This is a book for VOICE WRITERS. No steno machines. No CSR credentials.")
        parts.append("- The output must read like a published book chapter, not a training manual.")

        if additional_context:
            parts.append("")
            parts.append(additional_context.strip())

        return "\n".join(parts)

    def draft_section(
        self,
        section: dict,
        research_content: str = "",
        additional_context: str = "",
        source_material: str = "",
        chapter_dir: Path | None = None,
        prompt_name: str = "writing-prompt.md",
    ) -> str:
        if chapter_dir is None:
            raise ValueError("chapter_dir is required for saving prompts.")
        prompt = self._build_draft_prompt(
            section, research_content, additional_context, source_material
        )
        self.exporter.save_prompt(chapter_dir, prompt_name, prompt)

        client = Anthropic(api_key=self.config.anthropic_api_key)
        model = self.config.claude_model

        # Scale max_tokens to section size (roughly 1.3 tokens per word + overhead)
        word_target = section.get("word_target", 5000)
        max_tokens = min(max(int(word_target * 1.5), 8000), 32000)

        def _call():
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
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
                return self._draft_with_batches(
                    section, research_content, additional_context, source_material, chapter_dir
                )
            raise

    def _draft_with_batches(
        self,
        section: dict,
        research_content: str,
        additional_context: str,
        source_material: str,
        chapter_dir: Path,
    ) -> str:
        subsections = section.get("subsections", [])
        chunks = [subsections[i : i + 3] for i in range(0, len(subsections), 3)]
        outputs = []
        for idx, chunk in enumerate(chunks, start=1):
            prompt = self._build_draft_prompt(
                section, research_content, additional_context, source_material, subsections=chunk
            )
            prompt_name = f"writing-prompt-part-{idx}.md"
            self.exporter.save_prompt(chapter_dir, prompt_name, prompt)
            client = Anthropic(api_key=self.config.anthropic_api_key)
            model = self.config.claude_model

            # Per-batch token allocation
            words_per_sub = section.get("word_target", 5000) // max(len(subsections), 1)
            batch_words = words_per_sub * len(chunk)
            max_tokens = min(max(int(batch_words * 1.5), 8000), 32000)

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
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
            "Revise this chapter draft into a PUBLICATION-READY book chapter.\n\n"
            "YOUR TASK: Take the current draft and produce a final version that reads like a "
            "professionally authored reference book. Apply all feedback from the expansion review, "
            "fact-check report, and quality review.\n\n"
            "CRITICAL REVISION PRIORITIES (in order):\n\n"
            "1. PROSE QUALITY: Every section must flow as authored prose. Convert any remaining "
            "bullet lists into flowing paragraphs. Add narrative transitions. Ensure every "
            "subsection tells a story, not just states rules.\n\n"
            "2. REMOVE ALL SCAFFOLDING: Delete every instance of 'Layer 1 — The Rule:', "
            "'Layer 2 — Why It Matters:', 'Layer 3 — Transcript Example:', 'Bridge:', "
            "and '[CALLOUT: ...]' markers. Replace with natural prose and blockquote callouts.\n\n"
            "3. FIX OPENINGS: If any 'From the Record' opening is a one-line summary, "
            "rewrite it as a 2–3 paragraph narrative scene with setting, tension, and stakes.\n\n"
            "4. CORRECT FACTS: Apply all corrections from the fact-check report. Remove or "
            "replace any FABRICATED or INCORRECT items. Keep all VERIFIED items.\n\n"
            "5. INCORPORATE EXPANSIONS: Add the best content suggestions from the expansion "
            "review — additional transcript examples, deeper stakes, stronger stories.\n\n"
            "6. CALLOUT DISCIPLINE: Maximum 1–2 per subsection. Never stack them. Always "
            "2+ paragraphs of prose between callouts. Use blockquote format.\n\n"
            "7. TERMINOLOGY: 'voice writer' (not stenomask reporter), 'digital reporter' "
            "(not electronic reporter), 'speech recognition engine' (not voice recognition), "
            "'impartiality' (not fairity). Remove any steno machine references.\n\n"
            "8. COMPLETENESS: Ensure the section opens with a From the Record story, ends "
            "with From the Record: Real-World Examples, and includes 2–3 Practice Challenges.\n\n"
            "---\n\n"
            "CURRENT DRAFT:\n"
            f"{draft}\n\n"
            "---\n\n"
            "EXPANSION SUGGESTIONS (incorporate the best ones):\n"
            f"{expansion_notes}\n\n"
            "---\n\n"
            "FACT-CHECK REPORT (fix all INCORRECT and FABRICATED items):\n"
            f"{fact_report}\n\n"
            "---\n\n"
            "QUALITY REVIEW (address all issues, especially critical ones):\n"
            f"{review_report}\n\n"
            "---\n\n"
            "AUTHOR NOTES:\n"
            f"{human_notes or 'No additional notes.'}\n\n"
            "---\n\n"
            "OUTPUT: The complete revised chapter as clean Markdown. It must read like a "
            "published book — not a manual, not an academic paper, not a government report. "
            "A voice writer should want to read this cover to cover."
        )
        self.exporter.save_prompt(chapter_dir, prompt_name, prompt)

        client = Anthropic(api_key=self.config.anthropic_api_key)
        model = self.config.claude_model

        word_target = section.get("word_target", 5000)
        max_tokens = min(max(int(word_target * 1.5), 8000), 32000)

        def _call():
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
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
                return self._revise_with_batches(
                    section, draft, expansion_notes, fact_report, review_report, human_notes, chapter_dir
                )
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
                "Revise this single subsection into publication-ready prose.\n\n"
                "RULES: Write flowing prose (no bullet lists). Remove all scaffolding labels. "
                "Fix any fact-check issues. Ensure rule → stakes → transcript example rhythm "
                "is present but invisible. Maximum 1–2 callouts as blockquotes. "
                "Voice writer terminology only. Must read like a published book.\n\n"
                f"SUBSECTION:\n{subsection}\n\n"
                f"EXPANSION NOTES:\n{expansion_notes}\n\n"
                f"FACT-CHECK:\n{fact_report}\n\n"
                f"REVIEW:\n{review_report}\n\n"
                f"AUTHOR NOTES:\n{human_notes or 'None.'}\n\n"
                "OUTPUT: Revised subsection as clean Markdown."
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
