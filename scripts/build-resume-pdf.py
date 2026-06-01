#!/usr/bin/env python3
"""Build an ATS-optimised A4 PDF resume from resume.json via weasyprint.

Shares the content model with the DOCX builder: both consume
resume_blocks.build_blocks(), so a single source of truth drives every format.
This module owns only the HTML+CSS rendering of those blocks and the PDF print.

ATS / AU format rules (see docs/resume-generation.md):
- Single-column, reverse-chronological, standard section headers.
- A4 page, 2.5 cm margins (CSS @page). System sans font (Calibri/Carlito/Arial).
- Text-selectable PDF (weasyprint emits real text, not images) — parses cleanly
  in Workday/Greenhouse/Lever and preserves layout across devices.
- lang="en-AU" on the document.

Unlike the DOCX path we keep Unicode punctuation (en/em dashes, ·) — it renders
nicely and modern PDF parsers handle it; text is HTML-escaped, not ASCII-stripped.

Run: python3 scripts/build-resume-pdf.py [--real-contact]

Default output: cv/docs/Paul Harvey - Resume.pdf (obfuscated email, no phone) — public,
committed, served on the site. --real-contact -> 'Paul Harvey - Resume (full).pdf'
(real email + phone) which is gitignored and never committed.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resume_blocks import build_blocks  # noqa: E402

from weasyprint import HTML  # noqa: E402


REPO = Path(__file__).resolve().parent.parent
RESUME_JSON = REPO / "resume.json"
OUT_PDF = REPO / "cv" / "docs" / "Paul Harvey - Resume.pdf"

# ATS-clean print stylesheet. Single column, A4, 2.5 cm margins, system sans.
# Carlito is the metric-compatible Calibri substitute commonly present on Linux;
# weasyprint falls back left-to-right via fontconfig.
CSS = """
@page { size: A4; margin: 2.5cm; }
* { box-sizing: border-box; }
/* Liberation Sans (Arial-metric, compact) leads because it is actually installed;
   leading with an absent font (Calibri/Carlito) makes fontconfig substitute the
   bulky DejaVu Sans and never reach the fallbacks. */
body { font-family: "Liberation Sans", Arial, Helvetica, Calibri, sans-serif;
       font-size: 10pt; color: #000; line-height: 1.15; margin: 0; }
h1 { font-size: 18pt; font-weight: bold; margin: 0 0 2pt; }
h2.section { font-size: 12.5pt; font-weight: bold; margin: 9pt 0 3pt;
             border-bottom: 0.5pt solid #ccc; padding-bottom: 1pt; }
h3.role { font-size: 11pt; font-weight: bold; margin: 6pt 0 1pt; }
p { margin: 0 0 1.5pt; }
p.title { font-size: 11pt; margin: 0 0 4pt; }
hr { border: none; border-top: 1pt solid #999; margin: 3pt 0 6pt; }
ul { margin: 0 0 3pt; padding-left: 15pt; }
li { margin: 0 0 1pt; }
li.sub { margin-left: 14pt; }
p.foot { font-size: 9pt; font-style: italic; color: #444; margin-top: 10pt; }
"""


def esc(s: str) -> str:
    return html.escape(s or "")


def para_html(blk: dict) -> str:
    """Render a 'para' block. The name (size>=18) becomes <h1>; the plain 12pt title
    gets a class; everything else carries an inline style derived from the block."""
    text = esc(blk["text"])
    size = blk.get("size", 11)
    if size >= 18:
        return f"<h1>{text}</h1>"
    if size == 12 and not blk.get("bold") and not blk.get("italic"):
        return f'<p class="title">{text}</p>'
    styles = []
    if size != 11:
        styles.append(f"font-size:{size}pt")
    if blk.get("bold"):
        styles.append("font-weight:bold")
    if blk.get("italic"):
        styles.append("font-style:italic")
    style = f' style="{";".join(styles)}"' if styles else ""
    return f"<p{style}>{text}</p>"


def blocks_to_html(blocks: list[dict], footer_text: str) -> str:
    """Convert the block list to a single ATS-clean HTML document. Consecutive
    bullet blocks are grouped into one <ul>."""
    out: list[str] = []
    list_open = False

    def close_list():
        nonlocal list_open
        if list_open:
            out.append("</ul>")
            list_open = False

    for blk in blocks:
        t = blk["t"]
        if t != "bullet":
            close_list()
        if t == "heading":
            out.append(f'<h2 class="section">{esc(blk["text"])}</h2>')
        elif t == "sub":
            out.append(f'<h3 class="role">{esc(blk["text"])}</h3>')
        elif t == "para":
            out.append(para_html(blk))
        elif t == "bullet":
            if not list_open:
                out.append("<ul>")
                list_open = True
            cls = ' class="sub"' if blk.get("level", 0) else ""
            out.append(f'<li{cls}>{esc(blk["text"])}</li>')
        elif t == "hr":
            out.append("<hr>")
        elif t == "spacer":
            out.append('<div style="height:6pt"></div>')
        else:
            raise ValueError(f"Unknown block type: {t!r}")
    close_list()

    if footer_text:
        out.append(f'<p class="foot">{esc(footer_text)}</p>')

    body = "\n".join(out)
    return (
        '<!DOCTYPE html>\n<html lang="en-AU">\n<head>\n<meta charset="utf-8">\n'
        f"<style>{CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Build ATS-friendly A4 PDF from resume.json")
    parser.add_argument("--real-contact", action="store_true",
                        help="Use the real email + phone (for direct ATS submissions). "
                             "Output goes to 'Paul Harvey - Resume (full).pdf', NOT the public file.")
    parser.add_argument("--keep-html", action="store_true",
                        help="Also write the intermediate HTML next to the PDF (debugging).")
    args = parser.parse_args()

    data = json.loads(RESUME_JSON.read_text())
    basics = data["basics"]

    if args.real_contact:
        out_path = REPO / "cv" / "docs" / "Paul Harvey - Resume (full).pdf"
    else:
        out_path = OUT_PDF

    footer_text = (
        f"Live interactive resume: {basics['url']} | Updated {data['meta']['lastModified']} | "
        f"Source: resume.json v{data['meta']['version']}"
    )

    blocks = build_blocks(data, real_contact=args.real_contact)
    doc_html = blocks_to_html(blocks, footer_text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.keep_html:
        out_path.with_suffix(".html").write_text(doc_html, encoding="utf-8")

    HTML(string=doc_html, base_url=str(REPO)).write_pdf(out_path)

    print(f"Wrote {out_path}")
    print(f"  Size: {out_path.stat().st_size:,} bytes")
    print(f"  Blocks rendered: {len(blocks)}")
    print(f"  Contact mode: {'REAL' if args.real_contact else 'obfuscated'}")


if __name__ == "__main__":
    main()
