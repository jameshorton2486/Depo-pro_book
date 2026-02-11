from __future__ import annotations

import json
import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.status import Status

from agents.writer import Writer
from agents.expander import Expander
from agents.checker import Checker
from agents.reviewer import Reviewer
from agents.researcher import Researcher
from agents.readability import ReadabilityAnalyzer
from agents.graphic_prompter import GraphicPrompter
from agents.image_generator import ImageGenerator
from exporters.markdown_exporter import MarkdownExporter
from pipeline.status_tracker import StatusTracker
from pipeline.cost_tracker import CostTracker
from pipeline.source_loader import SourceLoader


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "section"


def _strip_front_matter(text: str | None) -> str:
    if not text:
        return ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


class Pipeline:
    def __init__(self, config, project_root: Path, log_path: Path):
        self.config = config
        self.project_root = project_root
        self.console = Console()
        self.exporter = MarkdownExporter(project_root)
        self.status = StatusTracker(project_root)
        self.cost = CostTracker(project_root / "logs")
        self.writer = Writer(config, self.exporter, self.cost, log_path)
        self.expander = Expander(config, self.exporter, self.cost, log_path)
        self.checker = Checker(config, self.exporter, self.cost, log_path)
        self.reviewer = Reviewer(config, self.exporter, self.cost, log_path)
        self.researcher = Researcher(config, self.exporter, self.cost, log_path)
        self.readability = ReadabilityAnalyzer()
        self.graphic_prompter = GraphicPrompter()
        self.image_generator = ImageGenerator(config, self.exporter, self.cost, log_path)
        self.source_loader = SourceLoader(project_root)
        self.toc_path = project_root / "config" / "toc.json"

    def get_section(self, section_number: int) -> dict:
        data = json.loads(self.toc_path.read_text(encoding="utf-8"))
        for section in data["sections"]:
            if section["number"] == section_number:
                return section
        raise ValueError(f"Section {section_number} not found in toc.json")

    def get_chapter_dir(self, section: dict) -> Path:
        return self.project_root / "chapters" / f"{section['number']:02d}-{section['slug']}"

    def ensure_chapter_dirs(self, section: dict) -> None:
        chapter_dir = self.get_chapter_dir(section)
        for sub in ["prompts", "research", "drafts", "reports", "graphics", "final"]:
            (chapter_dir / sub).mkdir(parents=True, exist_ok=True)

    def _panel_header(self, section: dict) -> Panel:
        body = (
            f"Section {section['number']}: {section['title']}\n"
            f"Part: {section['part']}\n"
            f"Target: ~{section['word_target']} words"
        )
        return Panel(body, title="BOOKFORGE v2  Pipeline", style="blue")

    def _skip_or_run(self, path: Path, force: bool) -> bool:
        return path.exists() and not force

    def _should_run(self, step_number: int, start_from: int, only_step: int | None) -> bool:
        if only_step is not None:
            return step_number == only_step
        return start_from <= step_number

    def _require_file(self, path: Path, message: str) -> None:
        if not path.exists():
            raise FileNotFoundError(message)

    def run_full(
        self,
        section_number: int,
        additional_context: str = "",
        start_from: int = 0,
        force: bool = False,
        only_step: int | None = None,
    ) -> None:
        section = self.get_section(section_number)
        chapter_dir = self.get_chapter_dir(section)
        self.ensure_chapter_dirs(section)
        self.console.print(self._panel_header(section))

        research_path = chapter_dir / "research" / "research.md"
        draft_path = chapter_dir / "drafts" / "draft-1-claude.md"
        expansion_path = chapter_dir / "drafts" / "expansion-notes.md"
        fact_path = chapter_dir / "reports" / "fact-check-report.md"
        review_path = chapter_dir / "reports" / "review-report.md"
        revised_path = chapter_dir / "drafts" / "draft-2-revised.md"
        readability_path = chapter_dir / "reports" / "readability-report.md"
        final_path = chapter_dir / "final" / f"{section['number']:02d}-{section['slug']}.md"

        toc_data = json.loads(self.toc_path.read_text(encoding="utf-8"))
        deep_sections = set(toc_data["research_strategy"]["deep_research_sections"])

        # Step 0: Research
        if self._should_run(0, start_from, only_step):
            if section_number in deep_sections:
                if research_path.exists() and not force:
                    self.console.print("[green] Using existing Deep Research file[/green]")
                else:
                    self.console.print("[yellow]Section flagged for Deep Research but no research.md found.[/yellow]")
                    self.console.print(f"[dim]Run Gemini Deep Research manually and save to: {research_path}[/dim]")
                    user_choice = input("Press Enter to use automated API research instead, or Ctrl+C to cancel: ")
                    if user_choice is not None:
                        with Status("Running automated research...", console=self.console):
                            research = self.researcher.research_section(section, chapter_dir)
                        self.exporter.save_file(chapter_dir, "research", "research.md", research, section, "research")
                        self.status.update_step(section_number, 0, section)
            else:
                if self._skip_or_run(research_path, force):
                    self.console.print("[yellow] Skipping research (file exists)[/yellow]")
                else:
                    with Status("Running research...", console=self.console):
                        research = self.researcher.research_section(section, chapter_dir)
                    self.exporter.save_file(chapter_dir, "research", "research.md", research, section, "research")
                    self.status.update_step(section_number, 0, section)

        # Step 1: Draft
        if self._should_run(1, start_from, only_step):
            if self._skip_or_run(draft_path, force):
                self.console.print("[yellow] Skipping draft (file exists)[/yellow]")
            else:
                research_content = _strip_front_matter(self.exporter.load_file(chapter_dir, "research", "research.md"))
                # Load relevant source material from existing files
                source_material = self.source_loader.get_source_material(section)
                if source_material:
                    self.console.print(f"[green] Loaded source material ({len(source_material)} chars)[/green]")
                with Status("Drafting chapter...", console=self.console):
                    draft = self.writer.draft_section(
                        section, research_content, additional_context,
                        source_material=source_material,
                        chapter_dir=chapter_dir,
                    )
                self.exporter.save_file(chapter_dir, "drafts", "draft-1-claude.md", draft, section, "draft")
                self.status.update_step(section_number, 1, section)

        # Step 2: Expand
        if self._should_run(2, start_from, only_step):
            if only_step is not None:
                self._require_file(
                    draft_path,
                    f"Missing draft for expansion. Run: bookforge write {section_number} --only 1",
                )
            if self._skip_or_run(expansion_path, force):
                self.console.print("[yellow] Skipping expansion (file exists)[/yellow]")
            else:
                draft = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "draft-1-claude.md"))
                with Status("Expanding content...", console=self.console):
                    expanded = self.expander.expand_section(section, draft, chapter_dir)
                self.exporter.save_file(chapter_dir, "drafts", "expansion-notes.md", expanded, section, "expand")
                self.status.update_step(section_number, 2, section)

        # Step 3: Fact-check
        if self._should_run(3, start_from, only_step):
            if only_step is not None:
                self._require_file(
                    draft_path,
                    f"Missing draft for fact-check. Run: bookforge write {section_number} --only 1",
                )
                self._require_file(
                    expansion_path,
                    f"Missing expansion notes for fact-check. Run: bookforge write {section_number} --only 2",
                )
            if self._skip_or_run(fact_path, force):
                self.console.print("[yellow] Skipping fact-check (file exists)[/yellow]")
            else:
                draft = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "draft-1-claude.md"))
                expansion = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "expansion-notes.md"))
                with Status("Fact-checking...", console=self.console):
                    report = self.checker.check_section(section, draft, expansion, chapter_dir)
                self.exporter.save_file(chapter_dir, "reports", "fact-check-report.md", report, section, "fact_check")
                self.status.update_step(section_number, 3, section)

        # Step 4: Review
        if self._should_run(4, start_from, only_step):
            if only_step is not None:
                self._require_file(
                    draft_path,
                    f"Missing draft for review. Run: bookforge write {section_number} --only 1",
                )
            if self._skip_or_run(review_path, force):
                self.console.print("[yellow] Skipping review (file exists)[/yellow]")
            else:
                draft = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "draft-1-claude.md"))
                with Status("Reviewing quality...", console=self.console):
                    review = self.reviewer.review_section(section, draft, chapter_dir)
                self.exporter.save_file(chapter_dir, "reports", "review-report.md", review, section, "review")
                self.status.update_step(section_number, 4, section)

        # Step 5: Revise
        if self._should_run(5, start_from, only_step):
            if only_step is not None:
                self._require_file(
                    draft_path,
                    f"Missing draft for revision. Run: bookforge write {section_number} --only 1",
                )
                self._require_file(
                    expansion_path,
                    f"Missing expansion notes for revision. Run: bookforge write {section_number} --only 2",
                )
                self._require_file(
                    fact_path,
                    f"Missing fact-check report for revision. Run: bookforge write {section_number} --only 3",
                )
                self._require_file(
                    review_path,
                    f"Missing review report for revision. Run: bookforge write {section_number} --only 4",
                )
            if self._skip_or_run(revised_path, force):
                self.console.print("[yellow] Skipping revision (file exists)[/yellow]")
            else:
                draft = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "draft-1-claude.md"))
                expansion = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "expansion-notes.md"))
                facts = _strip_front_matter(self.exporter.load_file(chapter_dir, "reports", "fact-check-report.md"))
                review = _strip_front_matter(self.exporter.load_file(chapter_dir, "reports", "review-report.md"))
                human_notes = _strip_front_matter(self.exporter.load_file(chapter_dir, "reports", "human-notes.md"))
                with Status("Revising chapter...", console=self.console):
                    revised = self.writer.revise_section(section, draft, expansion, facts, review, human_notes, chapter_dir)
                self.exporter.save_file(chapter_dir, "drafts", "draft-2-revised.md", revised, section, "revise")
                self.status.update_step(section_number, 5, section)

        # Step 6: Readability
        if self._should_run(6, start_from, only_step):
            if only_step is not None:
                self._require_file(
                    revised_path,
                    f"Missing revised draft for readability. Run: bookforge write {section_number} --only 5",
                )
            if self._skip_or_run(readability_path, force):
                self.console.print("[yellow] Skipping readability (file exists)[/yellow]")
            else:
                revised = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "draft-2-revised.md"))
                with Status("Analyzing readability...", console=self.console):
                    report = self.readability.analyze_readability(revised, section)
                self.exporter.save_file(chapter_dir, "reports", "readability-report.md", report, section, "readability")
                self.status.update_step(section_number, 6, section)

        # Step 7: Human review
        if self._should_run(7, start_from, only_step):
            panel = Panel(
                "Human review required.\n"
                f"Read: {chapter_dir / 'drafts' / 'draft-2-revised.md'}\n"
                f"Reports: {chapter_dir / 'reports'}\n"
                f"To approve: bookforge approve {section_number}\n"
                f"To revise: Add notes to {chapter_dir / 'reports' / 'human-notes.md'}\n"
                f"then run: bookforge write {section_number} --from 5",
                title="Human Review",
                style="yellow",
            )
            self.console.print(panel)

        # Step 8: Graphics
        if self._should_run(8, start_from, only_step):
            if only_step is not None:
                if not revised_path.exists() and not final_path.exists():
                    raise FileNotFoundError(
                        f"Missing revised or final draft for graphics. Run: bookforge write {section_number} --only 5"
                    )
            graphics_prompts_path = chapter_dir / "prompts" / "graphic-prompts.md"
            graphics_tasks_path = chapter_dir / "graphics" / "graphics-tasks.md"
            if self._skip_or_run(graphics_tasks_path, force):
                self.console.print("[yellow] Skipping graphics (file exists)[/yellow]")
            else:
                source_text = _strip_front_matter(
                    self.exporter.load_file(chapter_dir, "final", f"{section['number']:02d}-{section['slug']}.md")
                    or self.exporter.load_file(chapter_dir, "drafts", "draft-2-revised.md")
                )
                if not source_text:
                    self.console.print("[red]No draft available for graphics step.[/red]")
                else:
                    with Status("Generating graphic prompts...", console=self.console):
                        prompts_md, tasks_md, manifest = self.graphic_prompter.generate_graphic_tasks(source_text, section)
                    graphics_prompts_path = self.exporter.save_file(
                        chapter_dir, "prompts", "graphic-prompts.md", prompts_md, section, "graphics_prompts"
                    )
                    graphics_tasks_path = self.exporter.save_file(
                        chapter_dir, "graphics", "graphics-tasks.md", tasks_md, section, "graphics_tasks"
                    )
                    manifest_path = chapter_dir / "graphics" / "manifest.json"
                    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                    self.console.print(f"[green] Graphics prompts saved[/green] [dim]{graphics_prompts_path}[/dim]")
                    self.console.print(f"[green] Graphics tasks saved[/green] [dim]{graphics_tasks_path}[/dim]")
                    self.console.print(f"[green] Graphics manifest saved[/green] [dim]{manifest_path}[/dim]")
                    image_mode = (self.config.image_mode or "prompts").lower().strip()
                    if image_mode in {"api", "both"}:
                        with Status("Generating images via API...", console=self.console):
                            created = self.image_generator.generate_images(manifest, chapter_dir)
                        if created:
                            self.console.print(f"[green] Images generated:[/green] {len(created)}")
                    self.status.update_step(section_number, 8, section)

        # Summary
        revised_text = _strip_front_matter(self.exporter.load_file(chapter_dir, "drafts", "draft-2-revised.md"))
        word_count = len(revised_text.split()) if revised_text else 0
        fact_report = self.exporter.load_file(chapter_dir, "reports", "fact-check-report.md") or ""
        fact_issues = len(re.findall(r"\b(INCORRECT|FABRICATED|OUTDATED)\b", fact_report))
        review_report = self.exporter.load_file(chapter_dir, "reports", "review-report.md") or ""
        review_match = re.search(r"Overall Score:\s*([0-9.]+)", review_report)
        review_score = float(review_match.group(1)) if review_match else 0.0
        readability_report = self.exporter.load_file(chapter_dir, "reports", "readability-report.md") or ""
        grade_match = re.search(r"Flesch-Kincaid Grade:\s*([0-9.]+)", readability_report)
        grade = float(grade_match.group(1)) if grade_match else 0.0

        self.status.update_metrics(section_number, word_count, grade, review_score)
        total_cost = self.cost.get_section_cost(section_number)

        summary = Panel(
            f"Draft: {word_count} words\n"
            f"Fact issues: {fact_issues}\n"
            f"Review score: {review_score}/10\n"
            f"Readability: Grade {grade}\n"
            f"API cost: ${total_cost:.2f}",
            title=f"PIPELINE COMPLETE: Section {section_number}",
            style="green",
        )
        self.console.print(summary)

    def approve(self, section_number: int) -> None:
        section = self.get_section(section_number)
        chapter_dir = self.get_chapter_dir(section)
        source = chapter_dir / "drafts" / "draft-2-revised.md"
        target = chapter_dir / "final" / f"{section['number']:02d}-{section['slug']}.md"
        if not source.exists():
            raise FileNotFoundError("Revised draft not found. Run the pipeline first.")
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        self.status.set_approved(section_number, section)
        self.console.print(f"[green]Approved section {section_number}. Saved to[/green] [dim]{target}[/dim]")
