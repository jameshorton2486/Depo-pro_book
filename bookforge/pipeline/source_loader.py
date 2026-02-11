"""Source material loader for BookForge.

Extracts usable content from the source-files/ directory and makes it
available to the writing pipeline. This bridges the gap between the
existing research/outline content and the chapter drafting step.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document


# Map keywords in subsection titles to relevant source content topics
_TOPIC_KEYWORDS = {
    "terminal": ["period", "question mark", "exclamation", "end marks"],
    "connective": ["comma", "semicolon", "colon", "oxford"],
    "dash": ["dash", "hyphen", "em dash", "en dash", "parenthetical"],
    "hyphen": ["hyphen", "compound", "modifier"],
    "apostrophe": ["apostrophe", "possessive", "contraction"],
    "quotation": ["quotation", "quote", "direct speech"],
    "symbol": ["bracket", "ellips", "slash", "forensic"],
    "parenthetical": ["parenthetical", "notation", "non-verbal", "action"],
    "interrupt": ["interrupt", "incomplete", "crosstalk", "overlap"],
    "filler": ["filler", "hesitation", "non-lexical", "utterance", "um", "uh"],
    "inaudible": ["inaudible", "unintelligible", "overlap"],
    "ethics": ["ethic", "impartial", "neutral", "guardian"],
    "voice writer": ["voice writ", "stenomask", "digital reporter", "identity"],
    "certification": ["certif", "NVRA", "AAERT", "CVR", "CER", "credential"],
    "speaker": ["speaker", "multi-speaker", "colloquy", "Q&A"],
    "exhibit": ["exhibit", "citation", "annotation", "bluebook"],
    "foreign": ["foreign", "interpret", "multilingual", "translation"],
    "page": ["page", "line number", "margin", "spacing", "format"],
    "proofread": ["proofread", "three-pass", "error", "quality"],
    "homophone": ["homophone", "their", "there", "moot", "mute"],
    "redact": ["redact", "attorney", "revision", "dispute"],
    "CAT": ["CAT", "software", "Eclipse", "CaseCATalyst", "Dragon"],
    "speech recognition": ["speech recognition", "voice brief", "Dragon"],
    "hardware": ["hardware", "microphone", "stenomask", "equipment"],
    "remote": ["remote", "virtual", "zoom", "video", "platform"],
    "scoping": ["scoping", "scopist", "real-time", "collaboration"],
    "vocal health": ["vocal", "health", "ergonomic", "exercise", "SOVT"],
    "AI": ["AI", "artificial intelligence", "future", "hybrid"],
    "business": ["business", "1099", "contractor", "billing", "practice"],
    "contract": ["contract", "agency", "billing", "rate"],
    "capitalization": ["capital", "proper noun", "entity"],
    "number": ["number", "date", "monetary", "amount"],
    "medical": ["medical", "terminol", "legal terminol"],
    "latin": ["latin", "mispronounce", "legal phrase"],
    "jurisdiction": ["jurisdiction", "state", "federal", "California", "Texas"],
}


def _extract_text_from_docx(path: Path) -> list[str]:
    """Extract non-empty paragraph text from a .docx file."""
    try:
        doc = Document(str(path))
        return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    except Exception:
        # If the file is actually plain text with a .docx extension
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return [line.strip() for line in text.split("\n") if line.strip()]
        except Exception:
            return []


def _extract_text_from_txt(path: Path) -> list[str]:
    """Extract non-empty lines from a text file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return [line.strip() for line in text.split("\n") if line.strip()]
    except Exception:
        return []


def _is_relevant(paragraph: str, keywords: list[str]) -> bool:
    """Check if a paragraph is relevant to a set of keywords."""
    lower = paragraph.lower()
    return any(kw.lower() in lower for kw in keywords)


def _clean_paragraph(text: str) -> str:
    """Remove known junk patterns from extracted text."""
    # Remove steno/CSR references (we rewrite for voice writers)
    text = re.sub(r"\bCSR\b", "reporter", text)
    text = re.sub(r"\bstenograph\w*\b", "voice writing", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsteno machine\w*\b", "speech recognition engine", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsteno\b", "voice", text, flags=re.IGNORECASE)
    return text.strip()


def _gather_keywords_for_section(section: dict) -> list[str]:
    """Build a list of search keywords from a section's metadata."""
    keywords = []
    title_lower = section.get("title", "").lower()
    subtitle_lower = section.get("subtitle", "").lower()

    for topic_key, topic_keywords in _TOPIC_KEYWORDS.items():
        if topic_key in title_lower or topic_key in subtitle_lower:
            keywords.extend(topic_keywords)

    for sub in section.get("subsections", []):
        sub_lower = sub.lower()
        for topic_key, topic_keywords in _TOPIC_KEYWORDS.items():
            if topic_key in sub_lower:
                keywords.extend(topic_keywords)

    # Add words from the title itself
    for word in re.findall(r"\b\w{4,}\b", title_lower):
        if word not in {"this", "that", "with", "from", "your", "section"}:
            keywords.append(word)

    for element in section.get("specific_elements", []):
        # Extract case names, rule references, etc.
        keywords.extend(re.findall(r"[A-Z][a-z]+(?:\s+v\.\s+[A-Z][a-z]+)?", element))
        keywords.extend(re.findall(r"FRE \d+", element))
        keywords.extend(re.findall(r"FRCP \d+", element))

    return list(set(keywords))


class SourceLoader:
    """Loads and filters source material for the writing pipeline."""

    def __init__(self, project_root: Path):
        self.source_dir = project_root / "source-files"
        self._all_paragraphs: list[tuple[str, str]] | None = None  # (source_file, text)

    def _load_all(self) -> list[tuple[str, str]]:
        """Load all source paragraphs once, lazily."""
        if self._all_paragraphs is not None:
            return self._all_paragraphs

        self._all_paragraphs = []
        if not self.source_dir.exists():
            return self._all_paragraphs

        for path in sorted(self.source_dir.iterdir()):
            if path.suffix == ".docx":
                paragraphs = _extract_text_from_docx(path)
            elif path.suffix in (".txt", ".md"):
                paragraphs = _extract_text_from_txt(path)
            else:
                continue

            for para in paragraphs:
                if len(para) > 20:  # Skip very short fragments
                    self._all_paragraphs.append((path.name, para))

        return self._all_paragraphs

    def get_source_material(self, section: dict, max_chars: int = 12000) -> str:
        """Extract source material relevant to a specific section.

        Returns a formatted string of relevant excerpts that can be
        injected into the writing prompt as reference material.
        """
        all_paras = self._load_all()
        if not all_paras:
            return ""

        keywords = _gather_keywords_for_section(section)
        if not keywords:
            return ""

        relevant = []
        seen = set()
        for source_file, para in all_paras:
            if _is_relevant(para, keywords):
                cleaned = _clean_paragraph(para)
                # Deduplicate near-identical content
                sig = cleaned[:80].lower()
                if sig not in seen and len(cleaned) > 30:
                    seen.add(sig)
                    relevant.append((source_file, cleaned))

        if not relevant:
            return ""

        # Build the source material block
        output_parts = [
            "SOURCE MATERIAL (use as reference — rewrite in book voice, do not copy verbatim):",
            "The following excerpts are from existing drafts and research. Extract accurate technical",
            "information, case references, and rule citations. Discard any formatting, bullet lists,",
            "or steno-specific references. Rewrite everything to match the Style Bible voice.",
            "",
        ]

        total_chars = 0
        current_source = ""
        for source_file, para in relevant:
            if total_chars + len(para) > max_chars:
                break
            if source_file != current_source:
                output_parts.append(f"\n--- From: {source_file} ---")
                current_source = source_file
            output_parts.append(para)
            total_chars += len(para)

        return "\n".join(output_parts)
