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
    image_mode: str = "prompts"
    image_model: str = "gpt-image-1.5"
    image_size: str = "1024x1024"
    image_quality: str = "medium"
    image_background: str = "auto"
    image_format: str = "png"

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
    # Load .env from the bookforge directory so it works regardless of cwd
    _config_dir = Path(__file__).resolve().parent
    # Prefer .env values to avoid stale shell env keys during local runs.
    # For production/CI, set the env vars directly or omit the .env file.
    load_dotenv(_config_dir / ".env", override=True)
    console = Console()

    missing = []
    for key in REQUIRED_KEYS:
        if not (os.getenv(key) or "").strip():
            missing.append(key)

    if missing:
        for key in missing:
            console.print(_missing_key_panel(key))
        raise SystemExit(1)

    def _get(key: str, default: str = "") -> str:
        return (os.getenv(key) or default).strip()

    return Config(
        anthropic_api_key=_get("ANTHROPIC_API_KEY"),
        openai_api_key=_get("OPENAI_API_KEY"),
        google_api_key=_get("GOOGLE_API_KEY"),
        claude_model=_get("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        openai_model=_get("OPENAI_MODEL", "gpt-4o"),
        gemini_model=_get("GEMINI_MODEL", "gemini-2.0-flash"),
        output_dir=_get("OUTPUT_DIR", "./chapters"),
        log_level=_get("LOG_LEVEL", "INFO"),
        image_mode=_get("IMAGE_MODE", "prompts"),
        image_model=_get("IMAGE_MODEL", "gpt-image-1.5"),
        image_size=_get("IMAGE_SIZE", "1024x1024"),
        image_quality=_get("IMAGE_QUALITY", "medium"),
        image_background=_get("IMAGE_BACKGROUND", "auto"),
        image_format=_get("IMAGE_FORMAT", "png"),
    )


def get_log_path(logs_dir: Path) -> Path:
    date_stamp = datetime.utcnow().strftime("%Y-%m-%d")
    return logs_dir / f"bookforge-{date_stamp}.log"


def ensure_log_dir(logs_dir: Path) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir
