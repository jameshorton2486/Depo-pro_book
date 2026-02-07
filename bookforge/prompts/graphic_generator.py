import re
from datetime import datetime


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return text.strip("-") or "item"


def generate_graphic_tasks(markdown_text: str, section_number: int) -> tuple[str, str]:
    markers = re.findall(r"\[(DIAGRAM|TABLE|TRANSCRIPT MOCKUP):\s*(.+?)\]", markdown_text)
    prompts = []
    tasks = []

    seq = 1
    for marker_type, desc in markers:
        desc_clean = desc.strip()
        slug = _slugify(desc_clean)[:40]
        if marker_type == "DIAGRAM":
            g_type = "FIG"
            tool = "Lucidchart"
            detail = f"Create a labeled diagram: {desc_clean}. Use clean lines and clear typography."
        elif marker_type == "TABLE":
            g_type = "TBL"
            tool = "Canva"
            detail = f"Create a formatted table image: {desc_clean}. Use readable column headers and legal-style typography."
        else:
            g_type = "TRN"
            tool = "Canva"
            detail = (
                "Create a transcript mockup in Courier 10-pitch, 25 lines, line numbers, "
                "Q/A indentation (Q 5 spaces, text 10 spaces)."
            )

        graphic_id = f"{g_type}-{section_number:02d}-{seq:02d}-{slug}"
        tasks.append((graphic_id, g_type, desc_clean, tool, "Todo"))
        prompts.append(f"## {graphic_id}\n{detail}")
        seq += 1

    header_elements = {
        1: "scales of justice and microphone",
        2: "legal document with magnifying glass",
        3: "period, comma, dash on legal document",
        4: "speech bubbles overlapping",
        5: "dictionary page with legal terms",
        6: "formatted transcript page blueprint",
        7: "magnifying glass over transcript",
        8: "microphone, laptop, headset",
        9: "video conference with courtroom",
        10: "briefcase with contract",
        11: "laptop with searchable database",
    }
    element = header_elements.get(section_number, "legal writing tools")
    header_prompt = (
        "Professional legal book chapter header, minimalist design, "
        "deep teal and slate gray, "
        f"{element}, clean background, editorial style, high resolution --ar 3:1 --v 6.1"
    )

    prompts.insert(0, "# Chapter Header\n" + header_prompt)

    graphic_prompts_md = "\n\n".join(prompts) + "\n"

    table_lines = [
        "| ID | Type | Description | Tool | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for graphic_id, g_type, desc_clean, tool, status in tasks:
        table_lines.append(f"| {graphic_id} | {g_type} | {desc_clean} | {tool} | {status} |")

    graphic_tasks_md = "\n".join(table_lines) + "\n"
    return graphic_prompts_md, graphic_tasks_md
