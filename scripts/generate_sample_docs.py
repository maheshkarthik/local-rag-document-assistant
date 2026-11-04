"""Build the sample PDFs in data/samples/ from the Markdown sources in scripts/sample_docs/.

The sources use a small Markdown subset:

    # Title                 document title (first line)
    > Subtitle              grey line under the title
    ## Heading / ### Sub    section headings
    - item / 1. item        list items
    | a | b |               table rows (the first row is the header)
    <!-- pagebreak -->      start a new page
    **bold**                bold text inside paragraphs and list items

Everything else is a paragraph; consecutive lines are joined.

Usage (fpdf2 is only needed to regenerate, not to run the app):

    pip install fpdf2
    python scripts/generate_sample_docs.py
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "scripts" / "sample_docs"
OUTPUT_DIR = ROOT / "data" / "samples"

# A fixed date keeps regenerated PDFs byte-identical when the sources don't change.
CREATION_DATE = datetime(2026, 11, 1, tzinfo=timezone.utc)
FOOTER = "Sample document for the Document Intelligence Assistant. Free to reuse (CC0)."
PAGE_BREAK = "<!-- pagebreak -->"


class SamplePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f"{FOOTER}    Page {self.page_no()} of {{nb}}", align="C")
        self.set_text_color(0)


def render(markdown: str, output: Path) -> int:
    pdf = SamplePDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_creation_date(CREATION_DATE)
    pdf.add_page()

    lines = markdown.splitlines()
    title = lines[0].removeprefix("# ").strip()
    pdf.set_title(title)
    pdf.set_author("Document Intelligence Assistant sample data")

    paragraph: list[str] = []
    table: list[list[str]] = []

    def flush_paragraph() -> None:
        if paragraph:
            pdf.set_font("Helvetica", "", 10.5)
            pdf.multi_cell(0, 5.5, " ".join(paragraph), markdown=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2.5)
            paragraph.clear()

    def flush_table() -> None:
        if table:
            pdf.set_font("Helvetica", "", 9.5)
            with pdf.table(
                line_height=5.5,
                headings_style=FontFace(emphasis="BOLD", fill_color=(225, 232, 240)),
                text_align="LEFT",
            ) as t:
                for row in table:
                    r = t.row()
                    for cell in row:
                        r.cell(cell)
            pdf.ln(3)
            table.clear()

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("|"):
            flush_paragraph()
            if not re.fullmatch(r"\|[\s:|-]+\|", line):
                table.append([c.strip() for c in line.strip("|").split("|")])
            continue
        flush_table()

        if not line.strip():
            flush_paragraph()
        elif line.strip() == PAGE_BREAK:
            flush_paragraph()
            pdf.add_page()
        elif line.startswith("# "):
            flush_paragraph()
            pdf.set_font("Helvetica", "B", 18)
            pdf.multi_cell(0, 9, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif line.startswith("> "):
            flush_paragraph()
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(90)
            pdf.multi_cell(0, 5.5, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0)
            pdf.ln(3)
        elif line.startswith("## "):
            flush_paragraph()
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 7, line[3:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif line.startswith("### "):
            flush_paragraph()
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, line[4:], new_x="LMARGIN", new_y="NEXT")
        elif m := re.match(r"(- |\d+\. )(.*)", line):
            flush_paragraph()
            marker = "-" if m.group(1) == "- " else m.group(1).strip()
            pdf.set_font("Helvetica", "", 10.5)
            pdf.set_x(pdf.l_margin + 3)
            pdf.cell(6, 5.5, marker)
            pdf.multi_cell(0, 5.5, m.group(2), markdown=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.8)
        else:
            paragraph.append(line.strip())

    flush_paragraph()
    flush_table()
    pdf.output(str(output))
    return pdf.page_no()


def main() -> int:
    sources = sorted(SOURCE_DIR.glob("*.md"))
    if not sources:
        print(f"No sources found in {SOURCE_DIR}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source in sources:
        text = source.read_text(encoding="utf-8")
        try:
            text.encode("latin-1")
        except UnicodeEncodeError as exc:
            bad = text[exc.start : exc.end]
            print(f"{source.name}: unsupported character {bad!r}; the built-in PDF fonts are Latin-1 only", file=sys.stderr)
            return 1
        output = OUTPUT_DIR / f"{source.stem}.pdf"
        pages = render(text, output)
        print(f"{output.relative_to(ROOT)}  ({pages} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
