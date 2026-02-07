import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

REQUIRED_KEYS = {
    "ANTHROPIC_API_KEY": {
        "url": "https://console.anthropic.com/",
        "use": "Claude API for drafting and revision steps.",
    },
    "OPENAI_API_KEY": {
        "url": "https://platform.openai.com/api-keys",
        "use": "ChatGPT API for expansion and fact-check steps.",
    },
    "GOOGLE_API_KEY": {
        "url": "https://aistudio.google.com/apikey",
        "use": "Gemini API for research and review steps.",
    },
}


@dataclass
class Config:
    anthropic_api_key: str
    openai_api_key: str
    google_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"
    gemini_model: str = "gemini-2.0-flash"
    output_dir: str = "./chapters"
    log_level: str = "INFO"

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)


def _missing_key_panel(key: str) -> Panel:
    info = REQUIRED_KEYS[key]
    body = (
        f"Missing key: {key}\n"
        f"Where to get it: {info['url']}\n"
        f"Used for: {info['use']}"
    )
    return Panel(body, title="API Key Required", style="red")


def load_config() -> Config:
    load_dotenv()
    console = Console()

    missing = []
    for key in REQUIRED_KEYS:
        if not os.getenv(key):
            missing.append(key)

    if missing:
        for key in missing:
            console.print(_missing_key_panel(key))
        raise SystemExit(1)

    return Config(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        output_dir=os.getenv("OUTPUT_DIR", "./chapters"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def get_log_path(logs_dir: Path) -> Path:
    date_stamp = datetime.utcnow().strftime("%Y-%m-%d")
    return logs_dir / f"bookforge-{date_stamp}.log"


def ensure_log_dir(logs_dir: Path) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir
