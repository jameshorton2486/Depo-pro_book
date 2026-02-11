# BookForge v2 → v3 Upgrade Package
## "Make It Read Like a Book" Mega Prompt + Pipeline Fixes

**Date:** February 11, 2026
**Purpose:** Fix all content quality issues so BookForge produces publication-ready book chapters

---

## What This Upgrade Fixes

### Problem → Solution Map

| Problem | Root Cause | File Changed | Fix |
|---------|-----------|-------------|-----|
| Output reads like a training manual | Master Writing Prompt didn't enforce prose-first writing strongly enough | `governance/Master_Writing_Prompt.md` | v3.0 mega prompt with explicit anti-manual rules, author identity, and prose requirements |
| Source material not used | No mechanism to load .docx source files into the pipeline | `pipeline/source_loader.py` (NEW) | Extracts relevant content from source-files/ and injects it into the writing prompt |
| Bullet lists everywhere | Writer prompt didn't prohibit lists as body content | `prompts/master_writer.py` | Fallback prompt now explicitly bans bullet lists as body content |
| Scaffolding labels in output | Writer produced them; revision tried to fix them (too late) | `governance/Master_Writing_Prompt.md` | v3.0 prevents them at the source — the writer prompt now says "if these appear, you have failed" |
| Expander prompt too generic | Just said "Expand this chapter" with no section context | `prompts/expander.py` | Now evaluates scene quality, prose flow, stakes depth, and flags manual-style writing |
| Reviewer didn't catch manual-style writing | Narrative quality was 1 of 7 equal criteria | `prompts/reviewer.py` | "Does it read like a book?" is now weighted 3× — most important criterion |
| Token limit too low for long sections | Hard-coded at 16,000 for all sections | `agents/writer.py` | Dynamic scaling: max_tokens = min(word_target × 1.5, 32000) |
| Steno references in output | Source material + prompts didn't enforce voice-writer focus | All prompt files | Every prompt now explicitly prohibits steno references |
| Fabricated citations in output | No guard against AI-fabricated cases | `governance/Master_Writing_Prompt.md` | Explicit rule: "If uncertain, describe generically — never fabricate" |
| Style Bible outdated | Didn't cover prose-first rule or content integrity | `config/style_bible.md` | v4.0 adds prose style, audience focus, and content integrity sections |

---

## Installation Steps

### Step 1: Backup Your Current Files

```powershell
cd C:\Users\james\Depo-pro_book\bookforge
mkdir backup-v2
copy governance\Master_Writing_Prompt.md backup-v2\
copy prompts\master_writer.py backup-v2\
copy prompts\expander.py backup-v2\
copy prompts\reviewer.py backup-v2\
copy agents\writer.py backup-v2\
copy config\style_bible.md backup-v2\
copy pipeline\orchestrator.py backup-v2\
```

### Step 2: Install New Files

Copy these files from the upgrade package to your bookforge directory:

```
REPLACE these files (overwrite the existing versions):
  governance/Master_Writing_Prompt.md  ← v3.0 mega prompt
  prompts/master_writer.py             ← updated prompt loader
  prompts/expander.py                  ← updated expansion prompt
  prompts/reviewer.py                  ← updated review prompt (weighted scoring)
  agents/writer.py                     ← source material + dynamic tokens
  config/style_bible.md                ← v4.0 style bible

ADD this new file:
  pipeline/source_loader.py            ← source material extraction engine
```

### Step 3: Patch the Orchestrator

Open `pipeline/orchestrator.py` and make these 3 changes:

**Change 1:** Add import at the top, after the other imports:
```python
from pipeline.source_loader import SourceLoader
```

**Change 2:** Add source loader initialization in `Pipeline.__init__`, after the image_generator line:
```python
self.source_loader = SourceLoader(project_root)
```

**Change 3:** Replace the "Step 1: Draft" block in `run_full` with:
```python
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
```

### Step 4: Install python-docx (if not already installed)

The source loader requires python-docx to read your .docx source files:

```powershell
pip install python-docx
```

### Step 5: Test the Pipeline

Run a single section to verify everything works:

```powershell
python bookforge.py write 3 --force
```

This will:
1. Research Section 3 (Punctuation Mechanics)
2. Load relevant source material from your .docx files automatically
3. Draft the chapter using the v3.0 mega prompt
4. Expand with the updated expander
5. Fact-check with ChatGPT
6. Review with the weighted scoring system
7. Revise with all feedback incorporated
8. Analyze readability

---

## What Changed in the Mega Prompt (v2.0 → v3.0)

The Master Writing Prompt is the single most important file in your pipeline. Here is what changed and why:

### Added: Author Identity Section
The AI now has a specific persona — a veteran voice writer with 15 years of experience. This prevents the generic "committee report" voice that was plaguing the output. When the AI knows WHO it is, it writes with conviction.

### Added: "This Is a Published Book" Enforcement
The v2.0 prompt said this is a book. The v3.0 prompt explains what that MEANS:
- Prose paragraphs are the default (not bullet lists)
- Stories teach better than checklists
- Transitions are invisible
- The reader is smart but building skills

### Added: Explicit Anti-Failure Rules
The prompt now contains a hard line: "If any of [the scaffolding strings] appear in your output, you have failed." This is more effective than asking nicely.

### Added: Source Material Incorporation Instructions
New section tells the AI how to handle source material: extract facts, rewrite in book voice, fix terminology. This enables the source loader without confusing the writer.

### Added: Content Integrity Rules
No fabricated citations. No invented statistics. No fictional named individuals. If uncertain, describe generically.

### Strengthened: Callout Discipline
Added "callouts are seasoning, not the main course" metaphor. Listed all allowed callout types (Pro Tip, Common Pitfall, Voice Brief Hack, Court Reality, Quick Reference).

### Strengthened: What to Avoid List
Added 8 new prohibitions including bullet lists as body content, meta-commentary openings, "Let's look at an example" filler, fabricated content, and committee/manual/academic writing styles.

---

## How Source Material Loading Works

The new `source_loader.py` does the following:

1. **Scans** all files in `source-files/` (.docx and .txt)
2. **Extracts** text paragraphs from each file
3. **Matches** paragraphs to the current section using keyword analysis from the TOC metadata
4. **Cleans** the content — replacing steno terminology with voice-writer terms
5. **Deduplicates** near-identical passages
6. **Caps** output at 12,000 characters to avoid exceeding context limits
7. **Injects** the result into the writing prompt with clear instructions to rewrite (not copy)

Your existing source files — EBook Good.docx, eBook Mastering Legal Transcription.docx, and the ChatGPT book — will be automatically mined for relevant technical content. The AI will extract the accurate facts and rewrite everything in the book's voice.

---

## Expected Results After Upgrade

### Before (v2.0 output)
- Bullet-point lists for body content
- "Layer 1 — The Rule:" visible in text
- One-line "From the Record" summaries
- Stacked callout boxes
- Generic voice with no personality
- Steno machine references
- Training manual formatting

### After (v3.0 output)
- Flowing prose paragraphs
- Invisible 3-layer structure
- 2–3 paragraph narrative scene openings
- 1–2 callouts per subsection, properly spaced
- Authoritative mentor voice with courtroom experience
- Voice-writer focused throughout
- Reads like a published reference book

---

## Recommended .env Model Configuration

For best book-quality output, consider upgrading your Claude model:

```
CLAUDE_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.0-flash
```

If budget allows, `claude-sonnet-4-20250514` or higher will produce better narrative prose.
The writing and revision steps benefit most from a stronger model.

---

*BookForge Upgrade Package — February 2026*
*Prepared for: Mastering Legal Transcription project*
