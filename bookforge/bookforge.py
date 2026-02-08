import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
import shutil
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from config import load_config, ensure_log_dir, get_log_path
from pipeline.orchestrator import Pipeline
from pipeline.status_tracker import StatusTracker
from pipeline.cost_tracker import CostTracker
from exporters.book_exporter import BookExporter


PROJECT_ROOT = Path(__file__).resolve().parent


def _init_dirs() -> None:
    for folder in [
        "chapters",
        "exports",
        "graphics",
        "source-files",
        "governance",
        "logs",
    ]:
        (PROJECT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def _check_env(console: Console) -> bool:
    env_path = PROJECT_ROOT / ".env"
    example_path = PROJECT_ROOT / ".env.example"
    if not env_path.exists():
        if example_path.exists():
            env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        console.print(
            Panel(
                f"Missing .env file. A template was created at {env_path}.\n"
                "Add your API keys, then re-run: bookforge init",
                title="Setup Required",
                style="yellow",
            )
        )
        return False
    return True


def _test_apis(console: Console, config) -> None:
    console.print("[blue]Testing API connections...[/blue]")
    # Anthropic
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=config.anthropic_api_key)
        client.messages.create(
            model=config.claude_model,
            max_tokens=8,
            system="You are a test.",
            messages=[{"role": "user", "content": "Reply with OK."}],
        )
        console.print("[green] Claude connection OK[/green]")
    except Exception as exc:
        console.print(Panel(f"Claude test failed: {exc}", style="red"))

    # OpenAI
    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key)
        client.chat.completions.create(
            model=config.openai_model,
            messages=[{"role": "user", "content": "Reply with OK."}],
            max_tokens=8,
        )
        console.print("[green] OpenAI connection OK[/green]")
    except Exception as exc:
        console.print(Panel(f"OpenAI test failed: {exc}", style="red"))

    # Gemini
    try:
        try:
            from google import genai
            client = genai.Client(api_key=config.google_api_key)
            client.models.generate_content(model=config.gemini_model, contents="Reply with OK.")
        except Exception:
            import google.generativeai as genai
            genai.configure(api_key=config.google_api_key)
            model = genai.GenerativeModel(config.gemini_model)
            model.generate_content("Reply with OK.")
        console.print("[green] Gemini connection OK[/green]")
    except Exception as exc:
        console.print(Panel(f"Gemini test failed: {exc}", style="red"))


@click.group()
def cli():
    """BookForge v2 CLI."""
    pass


@cli.command()
def init():
    """Initialize project folders and validate setup."""
    console = Console()
    _init_dirs()
    if not _check_env(console):
        raise SystemExit(1)
    config = load_config()
    _test_apis(console, config)

    if shutil.which("pandoc"):
        console.print("[green] Pandoc found[/green]")
    else:
        console.print(Panel("Pandoc not found. Install Pandoc and add to PATH.", style="red"))

    console.print(Panel("Initialization complete.", style="green"))


@cli.command()
@click.argument("section_number", type=int)
@click.option("--from", "start_from", type=int, default=0, help="Resume from step (0-8).")
@click.option("--only", "only_step", type=int, default=None, help="Run only a single step (0-8).")
@click.option("--context", "additional_context", type=str, default="", help="Additional instructions for this session.")
@click.option("--force", is_flag=True, help="Re-run all steps even if files exist.")
def write(section_number: int, start_from: int, only_step: int | None, additional_context: str, force: bool):
    """Run the full pipeline for a section."""
    console = Console()
    config = load_config()
    ensure_log_dir(PROJECT_ROOT / "logs")
    log_path = get_log_path(PROJECT_ROOT / "logs")
    pipeline = Pipeline(config, PROJECT_ROOT, log_path)
    pipeline.run_full(section_number, additional_context, start_from, force, only_step)


@cli.command()
@click.argument("section_number", type=int)
def approve(section_number: int):
    """Approve a section and move revised draft to final."""
    config = load_config()
    ensure_log_dir(PROJECT_ROOT / "logs")
    log_path = get_log_path(PROJECT_ROOT / "logs")
    pipeline = Pipeline(config, PROJECT_ROOT, log_path)
    pipeline.approve(section_number)


@cli.command()
def status():
    """Display pipeline status for all sections."""
    console = Console()
    tracker = StatusTracker(PROJECT_ROOT)
    cost_tracker = CostTracker(PROJECT_ROOT / "logs")
    data = tracker.get_all_statuses()
    toc = json.loads((PROJECT_ROOT / "config" / "toc.json").read_text(encoding="utf-8"))

    table = Table(title="BookForge Status", box=box.SIMPLE, show_lines=False)
    table.add_column("#", width=2)
    table.add_column("Title", width=18)
    table.add_column("Order", width=5)
    table.add_column("Status", width=10)
    table.add_column("Words", width=6)
    table.add_column("Grade", width=5)
    table.add_column("Score", width=5)
    table.add_column("Cost", width=6)

    for section in sorted(toc["sections"], key=lambda s: s["build_order"]):
        entry = data.get(str(section["number"]), {})
        title = section["title"][:18]
        cost = cost_tracker.get_section_cost(section["number"])
        table.add_row(
            str(section["number"]),
            title,
            str(section["build_order"]),
            entry.get("status", "Not Started")[:10],
            str(entry.get("word_count", "-")),
            str(entry.get("readability_grade", "-"))[:5],
            str(entry.get("review_score", "-"))[:5],
            f"${cost:.2f}",
        )

    completed, total = tracker.get_progress(len(toc["sections"]))
    percent = int((completed / total) * 100) if total else 0
    console.print(table)
    console.print(f"Progress: {percent}% ({completed}/{total})")


@cli.command()
def list():
    """Display build order with section details."""
    console = Console()
    toc = json.loads((PROJECT_ROOT / "config" / "toc.json").read_text(encoding="utf-8"))
    tracker = StatusTracker(PROJECT_ROOT)
    statuses = tracker.get_all_statuses()
    table = Table(title="Build Order", box=box.SIMPLE)
    table.add_column("Order", width=5)
    table.add_column("#", width=2)
    table.add_column("Title", width=30)
    table.add_column("Status", width=12)
    for section in sorted(toc["sections"], key=lambda s: s["build_order"]):
        entry = statuses.get(str(section["number"]), {})
        table.add_row(
            str(section["build_order"]),
            str(section["number"]),
            section["title"],
            entry.get("status", "Not Started")[:12],
        )
    console.print(table)


@cli.command()
@click.argument("section_number", type=int)
def open(section_number: int):
    """Print the full path to the section folder."""
    config = load_config()
    ensure_log_dir(PROJECT_ROOT / "logs")
    log_path = get_log_path(PROJECT_ROOT / "logs")
    pipeline = Pipeline(config, PROJECT_ROOT, log_path)
    section = pipeline.get_section(section_number)
    path = pipeline.get_chapter_dir(section)
    Console().print(f"{path}")
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


@cli.command()
@click.argument("format", type=str)
def export(format: str):
    """Export final chapters to EPUB, PDF, DOCX, HTML, or a static site."""
    console = Console()
    exporter = BookExporter(PROJECT_ROOT)
    try:
        if format == "epub":
            output = exporter.export_epub()
        elif format == "pdf":
            output = exporter.export_pdf()
        elif format == "docx":
            output = exporter.export_docx()
        elif format == "html":
            output = exporter.export_html()
        elif format == "site":
            output = exporter.export_site()
        elif format == "all":
            outputs = [
                exporter.export_epub(),
                exporter.export_pdf(),
                exporter.export_docx(),
                exporter.export_html(),
                exporter.export_site(),
            ]
            console.print("[green]Exports complete:[/green]")
            for item in outputs:
                console.print(f"[dim]{item}[/dim]")
            return
        else:
            raise click.BadParameter("Format must be epub, pdf, docx, html, site, or all.")
        console.print(f"[green]Export complete:[/green] [dim]{output}[/dim]")
    except Exception as exc:
        console.print(Panel(f"Export failed: {exc}", style="red"))


@cli.command()
def cost():
    """Display API costs per section and total."""
    console = Console()
    tracker = CostTracker(PROJECT_ROOT / "logs")
    table = Table(title="API Costs", box=box.SIMPLE)
    table.add_column("Section", width=7)
    table.add_column("Cost", width=10)
    for row in tracker.get_cost_table():
        table.add_row(str(row["section"]), f"${row['cost']:.2f}")
    total = tracker.get_total_cost()
    console.print(table)
    console.print(f"Total cost: ${total:.2f}")


if __name__ == "__main__":
    cli()
