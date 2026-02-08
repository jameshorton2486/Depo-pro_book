# CODEX_CONTEXT.md — BookForge v2 Project Briefing

Full project briefing for Codex. Follow Section 6 in priority order.

---

## 1. Project overview

**BookForge v2** is a Python CLI that automates an 8-step, multi-AI pipeline for writing a professional court reporting reference book. It coordinates:

- **Anthropic Claude** — research, drafting, expansion
- **OpenAI GPT-4o** — fact-checking (with optional web search)
- **Google Gemini** — review

Outputs: prompts and outputs saved for audit; Midjourney/Canva-style graphic prompts; exports to EPUB, PDF, DOCX, HTML, Kindle, paperback, Google Docs, and website via Pandoc and WeasyPrint.

**Location:** `C:\Users\james\Depo-pro_book\bookforge\`

---

## 2. Architecture

- **bookforge.py** — CLI entry (Click). Commands: `init`, `write`, `approve`, `status`, `list`, `open`, `cost`, `export`.
- **config.py** — Loads `.env`, provides API keys and model names.
- **pipeline/orchestrator.py** — Runs the 8-step pipeline per section; respects `--only` and `--from`.
- **agents/** — Researcher, Writer, Expander, Checker, Reviewer, Readability, GraphicPrompter. Each uses a base pattern: load config, call API with retry, log cost, save outputs.
- **exporters/** — BookExporter (epub, pdf, docx, html, kindle, paperback, gdoc, website), MarkdownExporter, DocxExporter (gdoc).
- **Cost tracker** — Logs token usage and cost per section/model.

---

## 3. Key decisions

- **Python 3.13** — Use `C:\Users\james\AppData\Local\Programs\Python\Python313\python.exe` when PATH is not set.
- **sys.path** — `bookforge.py` inserts its parent directory at the top so imports work from any CWD.
- **Windows open** — `open` command uses `os.startfile(path)` on Windows, `open` on macOS, `xdg-open` on Linux.
- **Gemini reviewer** — Uses `system_instruction=REVIEWER_PROMPT` and user prompt for `generate_content`.
- **Checker** — Tries OpenAI with `web_search` tool first; on failure, warns and falls back to model-only fact-check.

---

## 4. Directory layout

```
bookforge/
  .env, .env.example
  bookforge.py, config.py, requirements.txt
  config/          (style_bible.md, toc.json)
  governance/      (TOC, style bible, audit, roadmap, prompts)
  source-files/    (source DOCX)
  chapters/        (per-section: research, drafts, reports, prompts, graphics, final)
  exports/         (epub, pdf, docx, html, kindle, paperback, gdoc, website)
  logs/
  agents/, pipeline/, exporters/, prompts/
```

---

## 5. TOC and build order

Sections are defined in `config/toc.json` with a `build_order` field. Section numbers and build order can differ. Pipeline runs in build_order; CLI refers to sections by section number (e.g. `write 3` = section number 3). Section 3 is first in build order (Punctuation & Mechanics).

---

## 6. Four fixes (implement in this order)

### Fix 1 — Centralize retry/backoff in base_agent.py

- Add or use a **base_agent** module that provides a single `_call_with_retry(fn, max_retries=3)` (or similar) with exponential backoff.
- Have Researcher, Writer, Expander, Checker, Reviewer, Readability agents use this shared helper instead of each implementing its own retry logic.
- Ensures consistent behavior and easier tuning.

### Fix 2 — CostTracker unknown model fallback

- In **pipeline/cost_tracker.py**, when the model name is unknown (not in the price map), do not crash. Use a safe fallback (e.g. a default price or 0) and optionally log a warning so cost reports still run.

### Fix 3 — Unify status and list commands

- **status** and **list** should show consistent section data (build order, section number, title, status).
- Prefer a single source of truth (e.g. StatusTracker or toc + files on disk). Both commands should show the same status values and ordering (e.g. by build_order).

### Fix 4 — Add --only flag to write command

- **bookforge write &lt;section_number&gt; --only &lt;step&gt;** runs only step `step` (0–8) for that section.
- Step indices: 0=research, 1=draft, 2=expand, 3=fact-check, 4=review, 5=revision, 6=readability, 7=approve (if applicable), 8=graphics.
- Pipeline must skip all other steps and run only the requested one; prerequisites (e.g. “draft exists”) should still be checked and give a clear error if missing.

---

## 7. Verification

After implementing the four fixes:

1. `python bookforge.py --help` — CLI loads.
2. `python bookforge.py write --help` — Shows `--only` option.
3. `python bookforge.py init` — Runs without error (API keys may still fail in sandbox).
4. `python bookforge.py status` and `python bookforge.py list` — Show aligned section list and status.

---

*End of CODEX_CONTEXT.md*
