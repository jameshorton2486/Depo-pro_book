import re
from datetime import datetime


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return text.strip("-") or "item"


def generate_graphic_tasks(markdown_text: str, section_number: int) -> tuple[str, str, list[dict]]:
    markers = re.findall(r"\[(DIAGRAM|TABLE|TRANSCRIPT MOCKUP):\s*(.+?)\]", markdown_text)
    prompts = []
    tasks = []
    manifest = []

    seq = 1
    for marker_type, desc in markers:
        desc_clean = desc.strip()
        slug = _slugify(desc_clean)[:40]
        style = (
            "Consistent templated style with subtle illustrations. "
            "Clean grid, vector-style line art with minimal shading, "
            "deep teal and slate gray with warm ivory background, "
            "editorial legal aesthetic, clear labels and icons."
        )
        if marker_type == "DIAGRAM":
            g_type = "FIG"
            tool = "Lucidchart"
            detail = f"Create a labeled diagram: {desc_clean}. Use clean lines and clear typography. {style}"
        elif marker_type == "TABLE":
            g_type = "TBL"
            tool = "Canva"
            detail = f"Create a formatted table image: {desc_clean}. Use readable column headers and legal-style typography. {style}"
        else:
            g_type = "TRN"
            tool = "Canva"
            detail = (
                "Create a transcript mockup in Courier 10-pitch, 25 lines, line numbers, "
                "Q/A indentation (Q 5 spaces, text 10 spaces). "
                f"{style}"
            )

        graphic_id = f"{g_type}-{section_number:02d}-{seq:02d}-{slug}"
        file_name = f"{graphic_id}.png"
        tasks.append((graphic_id, g_type, desc_clean, tool, file_name, "Todo"))
        prompts.append(f"## {graphic_id}\n{detail}")
        manifest.append(
            {
                "id": graphic_id,
                "type": g_type,
                "description": desc_clean,
                "tool": tool,
                "file": file_name,
                "prompt": detail,
                "section": section_number,
            }
        )
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
        "Professional legal book chapter header in a consistent templated style, "
        "minimalist grid, vector line art with subtle illustration fills, "
        "deep teal and slate gray on warm ivory background, "
        f"{element}, clean background, editorial legal style, high resolution, wide banner composition."
    )

    header_id = f"HDR-{section_number:02d}-00-chapter-header"
    header_file = f"{header_id}.png"
    prompts.insert(0, "# Chapter Header\n" + header_prompt)
    tasks.insert(0, (header_id, "HDR", "Chapter header illustration", "Canva", header_file, "Todo"))
    manifest.insert(
        0,
        {
            "id": header_id,
            "type": "HDR",
            "description": "Chapter header illustration",
            "tool": "Canva",
            "file": header_file,
            "prompt": header_prompt,
            "section": section_number,
        },
    )

    graphic_prompts_md = "\n\n".join(prompts) + "\n"

    table_lines = [
        "| ID | Type | Description | Tool | File | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for graphic_id, g_type, desc_clean, tool, file_name, status in tasks:
        table_lines.append(f"| {graphic_id} | {g_type} | {desc_clean} | {tool} | {file_name} | {status} |")

    graphic_tasks_md = "\n".join(table_lines) + "\n"
    return graphic_prompts_md, graphic_tasks_md, manifest
