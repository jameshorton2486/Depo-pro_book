# BookForge v2

BookForge is a Python command-line application that automates an 8-step, multi-AI pipeline for writing a professional court reporting reference book. It coordinates Anthropic Claude, OpenAI GPT-4o, and Google Gemini to research, draft, expand, fact-check, review, revise, and analyze chapters, while saving every prompt and output for auditability. It also generates Midjourney/Canva graphics prompts and exports the final manuscript to EPUB, PDF, DOCX, and HTML via Pandoc.

## Prerequisites

- Python 3.10+
- Pandoc installed and on PATH
- xelatex installed (for PDF export)
- API keys for Anthropic, OpenAI, and Google Gemini

## Quick Start

1. Install dependencies:

```bash
cd bookforge
pip install -r requirements.txt
```

2. Create `.env`:

```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Initialize:

```bash
python bookforge.py init
```

## Write Your First Chapter

```bash
python bookforge.py write 3
```

## The 8-Step Pipeline

1. Research (Gemini)
2. Draft (Claude)
3. Expand (ChatGPT)
4. Fact-check (ChatGPT)
5. Review (Gemini)
6. Revise (Claude)
7. Readability (local)
8. Graphics (local prompt generation)

Master writing rules are loaded from `governance/Master_Writing_Prompt.md` at runtime (with a built-in fallback).

## CLI Commands

```bash
bookforge init
bookforge write 3
bookforge write 3 --from 4
bookforge write 3 --only 2
bookforge write 3 --context "Focus on California MTFS rules"
bookforge write 3 --force
bookforge approve 3
bookforge status
bookforge list
bookforge open 3
bookforge export epub
bookforge export pdf
bookforge export docx
bookforge export html
bookforge export site
bookforge export all
bookforge cost
```

## Per-Chapter Folder Structure

Each chapter is stored in `chapters/XX-slug/` with:

- `prompts/` (saved prompts)
- `research/` (research output)
- `drafts/` (drafts and expansion notes)
- `reports/` (fact-check, review, readability)
- `graphics/` (graphics tasks)
- `final/` (approved chapter)

## Deep Research Workflow

Sections 3, 4, 6, and 8 are flagged for manual Deep Research. If `research/research.md` is missing, the pipeline will prompt you to either:

- Run Gemini Deep Research manually and save to the folder, or
- Press Enter to use automated API research instead

## Export Commands

Exports are compiled from `chapters/XX-slug/final/*.md` using `metadata.yaml`:

- EPUB: `bookforge export epub`
- PDF: `bookforge export pdf`
- DOCX: `bookforge export docx`
- HTML: `bookforge export html`
- Web site: `bookforge export site`
- All: `bookforge export all`

The static site output is written to `exports/site/index.html`.

## Graphics Generation

BookForge always generates graphics prompts and tasks. You can also enable API image generation.

Set in `.env`:

- `IMAGE_MODE=prompts` (default)
- `IMAGE_MODE=api` (generate images via OpenAI)
- `IMAGE_MODE=both` (prompts + API images)

Optional overrides:

- `IMAGE_MODEL=gpt-image-1.5`
- `IMAGE_SIZE=1024x1024`
- `IMAGE_QUALITY=medium`
- `IMAGE_BACKGROUND=auto`
- `IMAGE_FORMAT=png`

## Troubleshooting

- Missing API keys: run `bookforge init` and ensure `.env` is filled out.
- API errors: check `logs/bookforge-YYYY-MM-DD.log` for details and retry.
- Pandoc errors: confirm Pandoc and xelatex are installed and on PATH.
- Missing steps: use `--from` to resume or `--force` to re-run.

## Cost Estimates

BookForge logs per-call usage to `logs/costs.json` and displays totals with `bookforge cost`.

Estimated rates (subject to change):

- Claude Sonnet: $3/M input, $15/M output
- GPT-4o: $2.50/M input, $10/M output
- Gemini Flash: $0.075/M input, $0.30/M output
