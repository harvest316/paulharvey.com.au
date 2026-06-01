#!/usr/bin/env python3
"""
Build an ATS-optimised combined DOCX resume from resume.json.

ATS-optimisation choices (research from Jobscan, ResumeWorded, Hays AU, Robert Half 2025-2026):

- Single-column layout. No tables, text boxes, columns, headers, footers, images, icons, SVG.
- Standard fonts only: Calibri 11pt body, 14pt section headings, 16pt name.
- Section headings use standard names ATS look for: "Professional Summary", "Work Experience",
  "Education", "Certifications", "Skills".
- Reverse-chronological work history.
- Dates in "Month YYYY" format. Months written long form to avoid ambiguity.
- Contact info inline at the top with text labels (Phone:/Email:/LinkedIn:), no icons.
- ASCII bullet `* ` for highest-compatibility (some ATS misread Unicode bullets).
- No special characters in role names; em-dashes replaced with ASCII " - ".
- A4 page (AU standard) with 2.5 cm margins. python-docx defaults to US Letter, so set explicitly.
- Document proofing language set to Australian English (en-AU).
- Filename uses only `[A-Za-z0-9 -]`.
- Keywords from JD-frequency analysis surfaced early via Summary + Highlights + Skills sections.
- All content from resume.json so a single source of truth produces both HTML and DOCX.

Run: python3 scripts/build-resume-docx.py [--real-contact]

By default `basics.email` reads the obfuscated form (`cv [at] paulharvey [dot] com [dot] au`)
from resume.json — sufficient for spam-scraper resistance, decodable by humans + most modern
ATS. For direct ATS form submissions that require an unambiguous email field, run with
`--real-contact` and the script reassembles the real address from `basics._emailParts`.
Resulting file is named `Paul Harvey - Resume (full).docx` and is NOT committed to git.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime

from docx import Document
from docx.shared import Pt, Inches, Cm, Mm, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


REPO = Path(__file__).resolve().parent.parent
RESUME_JSON = REPO / "resume.json"
OUT_DOCX = REPO / "cv" / "docs" / "Paul Harvey - Resume.docx"

# Fonts: Calibri is the most widely-tested font for ATS parsing.
FONT_BODY = "Calibri"
FONT_HEADING = "Calibri"

# ASCII bullet for max compatibility. Some ATS still trip on `•`.
BULLET = "* "

# Contact details are deliberately NOT stored in resume.json (which is a public download).
# They live here in encoded form so the DOCX can render them. Default output uses
# light obfuscation (Base64 lookalike, `[at]`/`[dot]`, spaced phone with explicit trunk
# prefix). `--real-contact` decodes to the unambiguous form for direct ATS submissions.
#
# Local part + domain stored separately so a regex looking for `\w+@\w+` finds nothing here.
import base64 as _b64
_EMAIL_LOCAL  = _b64.b64decode("Y3Y=").decode("ascii")              # -> "cv"
_EMAIL_DOMAIN = _b64.b64decode("cGF1bGhhcnZleS5jb20uYXU=").decode("ascii")  # -> "paulharvey.com.au"
# Phone digits as int array; trunk prefix + country code added at render time.
_PHONE_DIGITS = [4, 8, 5, 9, 7, 8, 0, 7, 5]


def email_obfuscated() -> str:
    """e.g. cv [at] paulharvey [dot] com [dot] au"""
    return f"{_EMAIL_LOCAL} [at] {_EMAIL_DOMAIN.replace('.', ' [dot] ')}"


def email_real() -> str:
    """e.g. cv@paulharvey.com.au"""
    return f"{_EMAIL_LOCAL}@{_EMAIL_DOMAIN}"


def phone_obfuscated() -> str:
    """e.g. +61 (0)485 978 075 - human-readable, defeats naive \\d{10} regex bots."""
    d = "".join(str(x) for x in _PHONE_DIGITS)
    return f"+61 (0){d[:3]} {d[3:6]} {d[6:]}"


def phone_real() -> str:
    """e.g. +61485978075 - standard tel: URI form, full ATS extraction."""
    d = "".join(str(x) for x in _PHONE_DIGITS)
    return f"+61{d}"


def to_ascii(s: str) -> str:
    """Strip Unicode characters that some ATS parsers mishandle. Preserve standard punctuation."""
    if not s:
        return ""
    replacements = {
        "–": "-",   # en dash
        "—": " - ", # em dash
        "’": "'",   # right single quote
        "‘": "'",   # left single quote
        "“": '"',   # left double quote
        "”": '"',   # right double quote
        "…": "...", # ellipsis
        "·": "-",   # middle dot used as separator
        "•": "*",   # bullet
        " ": " ",   # nbsp
        "£": "GBP", # pound sign
        "€": "EUR", # euro
        "→": "->",  # arrow
        "↗": "",    # ne arrow
        "°": " degrees", # degree
        "−": "-",   # minus
        "&": "and",      # ampersand for ATS safety in section headers
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    # Strip any non-ASCII remainder
    s = s.encode("ascii", "ignore").decode("ascii")
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fmt_date(d: str | None) -> str:
    """JSON Resume dates: 'YYYY-MM' or 'YYYY'. Convert to long-form 'Month YYYY'."""
    if not d:
        return "Present"
    parts = d.split("-")
    if len(parts) == 1:
        return parts[0]
    year, month = parts[0], int(parts[1])
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    return f"{months[month - 1]} {year}"


def date_range(start: str | None, end: str | None) -> str:
    return f"{fmt_date(start)} - {fmt_date(end)}"


def set_run(run, *, size=11, bold=False, italic=False, font=FONT_BODY):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    # Set East-Asian font too so Word doesn't substitute on non-Latin Word installs
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), font)
    rfonts.set(qn("w:hAnsi"), font)
    rfonts.set(qn("w:cs"), font)


def add_para(doc, text="", *, size=11, bold=False, italic=False, font=FONT_BODY,
             space_before=0, space_after=2, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(to_ascii(text))
        set_run(r, size=size, bold=bold, italic=italic, font=font)
    return p


def add_heading(doc, text):
    """Section heading. Capitalised standard ATS names. No styling beyond bold + larger size."""
    p = add_para(doc, text, size=14, bold=True, font=FONT_HEADING,
                 space_before=12, space_after=6)
    return p


def add_subheading(doc, text):
    """Role/sub-section heading."""
    return add_para(doc, text, size=12, bold=True, space_before=8, space_after=2)


def add_bullet(doc, text, indent_level=0):
    """Plain bulleted line. Uses ASCII '* ' prefix in text rather than Word's list-style,
    because ATS often strip Word list formatting but preserve in-paragraph text."""
    indent = "  " * indent_level
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.2 + indent_level * 0.2)
    r = p.add_run(BULLET + to_ascii(text))
    set_run(r, size=11)
    return p


def add_hr(doc):
    """Horizontal rule via single dashed paragraph border. ATS-safe."""
    p = add_para(doc, "", size=4, space_before=2, space_after=4)
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "999999")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def set_document_language(doc, lang="en-AU"):
    """Set proofing language so Word spell-checks Australian English.

    Sets it on both docDefaults (inherited by all text) and the Normal style.
    Without this, python-docx documents default to en-US and Word flags
    AU spellings (organise, recognised, behaviour) as errors.
    """
    styles = doc.styles.element  # <w:styles>

    docDefaults = styles.find(qn("w:docDefaults"))
    if docDefaults is None:
        docDefaults = OxmlElement("w:docDefaults")
        styles.insert(0, docDefaults)
    rPrDefault = docDefaults.find(qn("w:rPrDefault"))
    if rPrDefault is None:
        rPrDefault = OxmlElement("w:rPrDefault")
        docDefaults.append(rPrDefault)
    rPr = rPrDefault.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        rPrDefault.append(rPr)
    for el in (rPr, doc.styles["Normal"].element.get_or_add_rPr()):
        langEl = el.find(qn("w:lang"))
        if langEl is None:
            langEl = OxmlElement("w:lang")
            el.append(langEl)
        langEl.set(qn("w:val"), lang)


def main():
    parser = argparse.ArgumentParser(description="Build ATS-friendly DOCX from resume.json")
    parser.add_argument("--real-contact", action="store_true",
                        help="Reassemble real email + phone from basics._emailParts (for direct ATS submissions). "
                             "Output goes to 'Paul Harvey - Resume (full).docx', NOT the public file.")
    args = parser.parse_args()

    data = json.loads(RESUME_JSON.read_text())
    basics = data["basics"]

    # Contact details NOT in resume.json. Pull from the encoded constants above.
    # Phone is intentionally omitted from the public DOCX — only included for direct
    # job-specific submissions via --real-contact.
    if args.real_contact:
        basics["email"] = email_real()
        basics["phone"] = phone_real()
        out_path = REPO / "cv" / "docs" / "Paul Harvey - Resume (full).docx"
    else:
        basics["email"] = email_obfuscated()
        basics["phone"] = None
        out_path = OUT_DOCX

    doc = Document()

    # A4 page (AU standard) — python-docx defaults to US Letter. Margins 2.5 cm all round.
    for section in doc.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
        # Explicitly disable headers/footers — many ATS skip them
        section.header.is_linked_to_previous = True
        section.footer.is_linked_to_previous = True

    # Default style for entire document
    style = doc.styles["Normal"]
    style.font.name = FONT_BODY
    style.font.size = Pt(11)

    # Proofing language: Australian English
    set_document_language(doc, "en-AU")

    loc = basics.get("location", {})

    # ====== HEADER: name + title + contact ======
    add_para(doc, basics["name"], size=20, bold=True, font=FONT_HEADING,
             space_before=0, space_after=2)
    add_para(doc, basics["label"], size=12, italic=False, space_after=4)

    # Single-line contact: location | phone | email | linkedin | website
    # Full country name ("Australia") not the ISO code, for ATS clarity.
    country_map = {"AU": "Australia", "US": "USA", "GB": "United Kingdom", "NZ": "New Zealand"}
    contact_parts = []
    if loc:
        country = country_map.get(loc.get("countryCode", ""), loc.get("countryCode", ""))
        contact_parts.append(f"{loc.get('city','')}, {loc.get('region','')}, {country}")
    # Text labels (no icons) — research: ATS read icons as garbage; bare values lose context.
    if basics.get("phone"):
        contact_parts.append(f"Phone: {basics['phone']}")
    if basics.get("email"):
        contact_parts.append(f"Email: {basics['email']}")
    li = next((p["url"] for p in basics.get("profiles", []) if p["network"].lower() == "linkedin"), None)
    if li:
        contact_parts.append(f"LinkedIn: {li}")
    if basics.get("url"):
        contact_parts.append(f"Web: {basics['url']}")
    add_para(doc, " | ".join(contact_parts), size=10, space_after=8)
    add_hr(doc)

    # ====== PROFESSIONAL SUMMARY ======
    add_heading(doc, "Professional Summary")
    add_para(doc, basics["summary"], size=11, space_after=6)

    # Experience-lines block as bullet list
    for line in basics.get("experienceLines", []):
        add_bullet(doc, f"{line['years']} - {line['text']}")

    if basics.get("certifiedSummary"):
        add_para(doc, f"Certified: {basics['certifiedSummary']}", size=11,
                 space_before=4, space_after=6)

    if basics.get("subSummary"):
        add_para(doc, basics["subSummary"], size=11, italic=False, space_after=6)

    # ====== CORE COMPETENCIES (top skills) ======
    add_heading(doc, "Core Competencies")
    skills = data.get("skills", [])
    # Print skills as flat comma-separated list (ATS-friendly)
    if skills:
        skill_names = [f"{s['name']} ({s.get('yearsExperience', '')} yrs)" if s.get("yearsExperience")
                       else s["name"] for s in skills]
        add_para(doc, " | ".join(skill_names), size=11, space_after=6)

    # Also list the highlights (top callouts) as inline tags
    if data.get("highlights"):
        callouts = [h["text"] if isinstance(h, dict) else h for h in data["highlights"]]
        add_para(doc, "Key strengths: " + " | ".join(callouts), size=11, space_after=8)

    # ====== WORK EXPERIENCE ======
    add_heading(doc, "Work Experience")
    work = data.get("work", [])
    recent = [w for w in work if not w.get("earlierCareer")]
    earlier = [w for w in work if w.get("earlierCareer")]

    for role in recent:
        # Subheading: Employer | Position | Dates | Location
        title_line = f"{role['name']} - {role.get('position','')}"
        add_subheading(doc, title_line)
        meta_parts = [date_range(role.get("startDate"), role.get("endDate"))]
        if role.get("location"):
            meta_parts.append(role["location"])
        if role.get("employmentType"):
            meta_parts.append(role["employmentType"])
        add_para(doc, " | ".join(meta_parts), size=10, italic=True, space_after=4)

        if role.get("context"):
            add_para(doc, role["context"], size=11, italic=True, space_after=4)
        if role.get("summary"):
            add_para(doc, role["summary"], size=11, space_after=4)
        if role.get("clients"):
            add_para(doc, "Clients: " + ", ".join(role["clients"]), size=11, space_after=4)

        for h in role.get("highlights", []):
            text = h["text"] if isinstance(h, dict) else h
            if isinstance(h, dict) and h.get("metric"):
                text = f"{text} [{h['metric']}]"
            add_bullet(doc, text)

        # Projects within consulting roles
        if role.get("projects"):
            for p in role["projects"]:
                add_para(doc, f"  Project: {p['name']}", size=11, bold=True,
                         space_before=4, space_after=2)
                if p.get("role"):
                    add_para(doc, f"  Role: {p['role']}", size=11, italic=True, space_after=2)
                for ph in p.get("highlights", []):
                    add_bullet(doc, ph, indent_level=1)

        # Keywords: soft skills, hard skills, agile practices appended as plain text — ATS-friendly
        keyword_blocks = []
        if role.get("softSkills"):
            keyword_blocks.append("Soft skills: " + ", ".join(role["softSkills"]))
        if role.get("hardSkills"):
            keyword_blocks.append("Hard skills: " + ", ".join(role["hardSkills"]))
        if role.get("agilePractices"):
            keyword_blocks.append("Agile practices: " + ", ".join(role["agilePractices"]))
        for kb in keyword_blocks:
            add_para(doc, kb, size=10, space_after=2)

    # ====== EARLIER CAREER ======
    if earlier:
        add_heading(doc, "Earlier Career")
        for role in earlier:
            line = (f"{role['name']} - {role.get('position','')} - "
                    f"{date_range(role.get('startDate'), role.get('endDate'))}")
            if role.get("location"):
                line += f" - {role['location']}"
            add_bullet(doc, line)

    # ====== EDUCATION ======
    add_heading(doc, "Education")
    for e in data.get("education", []):
        line = e["institution"]
        details = []
        if e.get("studyType"):
            details.append(e["studyType"])
        if e.get("area"):
            details.append(e["area"])
        if e.get("endDate"):
            details.append(e["endDate"])
        if details:
            line += " - " + " - ".join(details)
        add_bullet(doc, line)

    # ====== CERTIFICATIONS ======
    add_heading(doc, "Certifications and Qualifications")
    for c in data.get("certifications", []):
        line = f"{c['name']} - {c.get('issuer','')} - {c.get('date','')}"
        add_bullet(doc, line)

    # ====== SKILLS MATRIX (years of experience) ======
    add_heading(doc, "Skills - Years of Experience")
    matrix = data.get("skillsByCategory", {})
    if matrix.get("softSkills"):
        add_para(doc, "Soft Skills:", size=11, bold=True, space_before=4, space_after=2)
        line = ", ".join(f"{s['name']} ({s['years']} yrs)" for s in matrix["softSkills"])
        add_para(doc, line, size=11, space_after=4)
    if matrix.get("technologies"):
        add_para(doc, "Technologies:", size=11, bold=True, space_before=4, space_after=2)
        line = ", ".join(f"{s['name']} ({s['years']} yrs)" for s in matrix["technologies"])
        add_para(doc, line, size=11, space_after=4)

    # ====== DIRECTORSHIPS ======
    if data.get("directorships"):
        add_heading(doc, "Directorships and Board Positions")
        for d in data["directorships"]:
            add_bullet(doc, f"{d['title']} ({d['startDate']} - {d['endDate']})")

    # ====== PROFESSIONAL MEMBERSHIPS ======
    if data.get("memberships"):
        add_heading(doc, "Professional Memberships")
        for m in data["memberships"]:
            add_bullet(doc, m)

    # ====== SIDE PROJECTS ======
    if data.get("sideProjects"):
        add_heading(doc, "Side Projects")
        for p in data["sideProjects"]:
            add_bullet(doc, f"{p['name']} ({p['url']}) - {p['description']}")

    # ====== PERSONAL ACHIEVEMENTS ======
    if data.get("personalAchievements"):
        add_heading(doc, "Personal Achievements")
        for a in data["personalAchievements"]:
            date = a.get("since") and f"since {a['since']}" or a.get("date", "")
            line = a["text"]
            if date:
                line += f" - {date}"
            if a.get("url"):
                line += f" ({a['url']})"
            add_bullet(doc, line)

    # ====== RECRUITER FAQ ======
    faq = data.get("recruiterFAQ")
    if faq:
        add_heading(doc, "Recruiter FAQ")
        add_bullet(doc, f"Availability: {faq['availability']}")
        add_bullet(doc, f"Visa: {faq['visa']}")
        add_bullet(doc, f"Rates - Contract: {faq['rates']['contract']}")
        add_bullet(doc, f"Rates - Permanent: {faq['rates']['permanent']}")
        loc = faq["location"]
        add_bullet(doc, f"Location: {loc['based']}; looking in {', '.join(loc['lookingIn'])}; {loc['relocation']}; travel {loc['travel']}")
        add_bullet(doc, f"Preferred roles: {' | '.join(faq['rolesPreferred'])}")
        add_bullet(doc, f"Short-term: {' | '.join(faq['rolesShortTerm'])}")
        add_bullet(doc, f"Holidays: {faq['holidays']}")
        if faq.get("perfectJob"):
            add_para(doc, f"Ideal: {faq['perfectJob']}", size=11, italic=True, space_before=4)

    # ====== REFERENCES ======
    # Names/numbers retained in resume.json (canonical) but NOT exported to the public DOCX.
    # Standard AU/global practice: "References available on request".
    add_heading(doc, "References")
    add_para(doc, "Available on request.", size=11, space_after=4)

    # ====== FOOTER NOTE: canonical link ======
    add_para(doc, "", size=8)
    add_para(doc,
             f"Live interactive resume: {basics['url']} | Generated {datetime.now():%Y-%m-%d} | Source: resume.json v{data['meta']['version']}",
             size=9, italic=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    print(f"Wrote {out_path}")
    print(f"  Size: {out_path.stat().st_size:,} bytes")
    print(f"  Roles (recent + earlier): {len(recent)} + {len(earlier)}")
    print(f"  Certifications: {len(data.get('certifications', []))}")
    print(f"  Contact mode: {'REAL' if args.real_contact else 'obfuscated'}")


if __name__ == "__main__":
    main()
