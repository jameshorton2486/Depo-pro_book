# ORCHESTRATOR PATCH — Apply these changes to pipeline/orchestrator.py
# This file shows the exact modifications needed. Apply with str_replace or manually.

# ──────────────────────────────────────────────────────
# CHANGE 1: Add import at the top of orchestrator.py
# After the existing imports, add:
# ──────────────────────────────────────────────────────

# ADD THIS LINE after "from pipeline.cost_tracker import CostTracker":
# from pipeline.source_loader import SourceLoader


# ──────────────────────────────────────────────────────
# CHANGE 2: Add source loader initialization in __init__
# ──────────────────────────────────────────────────────

# In the Pipeline.__init__ method, after:
#     self.image_generator = ImageGenerator(config, self.exporter, self.cost, log_path)
# ADD:
#     self.source_loader = SourceLoader(project_root)


# ──────────────────────────────────────────────────────
# CHANGE 3: Wire source material into the draft step
# ──────────────────────────────────────────────────────

# In the run_full method, replace the ENTIRE "# Step 1: Draft" block with:

"""
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
"""
