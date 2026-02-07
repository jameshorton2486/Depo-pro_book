from __future__ import annotations

import re
from datetime import datetime

import textstat


class ReadabilityAnalyzer:
    def analyze_readability(self, text: str, section: dict) -> str:
        report = []
        report.append(f"# Readability Report - Section {section['number']}\n")

        fk_grade = textstat.flesch_kincaid_grade(text)
        fk_ease = textstat.flesch_reading_ease(text)
        report.append(f"- Flesch-Kincaid Grade: {fk_grade:.2f}")
        report.append(f"- Flesch Reading Ease: {fk_ease:.2f}\n")

        sentences = re.split(r"(?<=[.!?])\s+", text)
        long_sentences = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 25:
                snippet = " ".join(words[:10])
                long_sentences.append(f"- {snippet}... ({len(words)} words)")
        report.append("## Sentence Length Violations")
        report.extend(long_sentences or ["- None"]) 
        report.append("")

        passive_patterns = [r"\bwas\s+\w+ed\b", r"\bwere\s+\w+ed\b", r"\bis\s+being\s+\w+ed\b", r"\bshould\s+be\s+\w+ed\b"]
        passive_hits = []
        for pattern in passive_patterns:
            passive_hits.extend(re.findall(pattern, text, flags=re.IGNORECASE))
        report.append("## Passive Voice")
        if passive_hits:
            for hit in passive_hits:
                report.append(f"- {hit}")
        else:
            report.append("- None")
        report.append("")

        prohibited = {
            "stenomask reporter": "voice writer",
            "electronic reporter": "digital reporter",
            "voice recognition": "speech recognition engine",
            "reporting software": "CAT software",
            "word-for-word": "verbatim",
        }
        report.append("## Terminology Violations")
        violations = []
        for bad, good in prohibited.items():
            for match in re.finditer(re.escape(bad), text, flags=re.IGNORECASE):
                line = text[max(0, match.start() - 40) : match.end() + 40].replace("\n", " ")
                violations.append(f"- '{bad}' -> use '{good}' | ...{line}...")
        report.extend(violations or ["- None"])
        report.append("")

        report.append("## 3-Layer Compliance")
        subsections = re.split(r"\n### ", text)
        if len(subsections) > 1:
            for subsection in subsections[1:]:
                title_line = subsection.splitlines()[0]
                block = subsection
                has_rule = "**" in block
                has_why = len(block.split()) > 100
                has_code = "```" in block
                missing = []
                if not has_rule:
                    missing.append("Rule")
                if not has_why:
                    missing.append("Why It Matters")
                if not has_code:
                    missing.append("Transcript Example")
                if missing:
                    report.append(f"- {title_line}: missing {', '.join(missing)}")
        else:
            report.append("- No subsections detected")
        report.append("")

        report.append("## Callout Density")
        callout_hits = ["[CALLOUT:", "> **Pro Tip**", "> **Common Pitfall**", "> **Voice Brief Hack**"]
        if len(subsections) > 1:
            for subsection in subsections[1:]:
                title_line = subsection.splitlines()[0]
                if not any(marker in subsection for marker in callout_hits):
                    report.append(f"- {title_line}: no callouts found")
        else:
            report.append("- No subsections detected")
        report.append("")

        report.append("## Word Count")
        report.append(f"- Total words: {len(text.split())}")
        report.append("")

        return "\n".join(report)
