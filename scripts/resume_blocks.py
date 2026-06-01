#!/usr/bin/env python3
"""Shared resume model: read resume.json, emit an ordered, format-agnostic block list.

Both the DOCX builder (build-resume-docx.py) and the PDF builder
(build-resume-pdf.py) consume build_blocks() so a single source of truth drives
every output format. The role-targeted generator (see docs/resume-generation.md)
will reuse the same blocks after selecting/reordering content per JD.

A "block" is a plain dict with a "t" (type) discriminator:
  {"t": "heading", "text": str}                         section heading (standard ATS name)
  {"t": "sub",     "text": str}                          role / sub-section heading
  {"t": "para",    "text": str, "size", "bold",          paragraph
                   "italic", "sb", "sa"}                  (sb/sa = space before/after, pt)
  {"t": "bullet",  "text": str, "level": int}            bulleted line
  {"t": "hr"}                                            horizontal rule
  {"t": "spacer",  "size": int}                          blank vertical gap

Contact details (email/phone) are NOT stored in resume.json (a public download).
They live here in encoded form. Default output uses light obfuscation; real_contact
decodes to the unambiguous form for direct ATS submissions.
"""

from __future__ import annotations

import base64 as _b64
import re

# ---- Contact constants (encoded; never plain in source so \w+@\w+ regex finds nothing) ----
_EMAIL_LOCAL = _b64.b64decode("Y3Y=").decode("ascii")                       # -> "cv"
_EMAIL_DOMAIN = _b64.b64decode("cGF1bGhhcnZleS5jb20uYXU=").decode("ascii")  # -> "paulharvey.com.au"
_PHONE_DIGITS = [4, 8, 5, 9, 7, 8, 0, 7, 5]

COUNTRY_MAP = {"AU": "Australia", "US": "USA", "GB": "United Kingdom", "NZ": "New Zealand"}


def email_obfuscated() -> str:
    """e.g. cv [at] paulharvey [dot] com [dot] au"""
    return f"{_EMAIL_LOCAL} [at] {_EMAIL_DOMAIN.replace('.', ' [dot] ')}"


def email_real() -> str:
    """e.g. cv@paulharvey.com.au"""
    return f"{_EMAIL_LOCAL}@{_EMAIL_DOMAIN}"


def phone_obfuscated() -> str:
    """e.g. +61 (0)485 978 075 — human-readable, defeats naive \\d{10} regex bots."""
    d = "".join(str(x) for x in _PHONE_DIGITS)
    return f"+61 (0){d[:3]} {d[3:6]} {d[6:]}"


def phone_real() -> str:
    """e.g. +61485978075 — standard tel: URI form, full ATS extraction."""
    d = "".join(str(x) for x in _PHONE_DIGITS)
    return f"+61{d}"


def to_ascii(s: str) -> str:
    """Strip Unicode characters that some ATS DOCX parsers mishandle. Preserve standard
    punctuation. (Used by the DOCX renderer; the PDF renderer keeps Unicode + HTML-escapes.)"""
    if not s:
        return ""
    replacements = {
        "–": "-", "—": " - ", "’": "'", "‘": "'", "“": '"', "”": '"',
        "…": "...", "·": "-", " ": " ", "£": "GBP", "€": "EUR",
        "→": "->", "↗": "", "°": " degrees", "−": "-", "&": "and",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = s.encode("ascii", "ignore").decode("ascii")
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


# ---- Block constructors ----

def _h(text):
    return {"t": "heading", "text": text}


def _sub(text):
    return {"t": "sub", "text": text}


def _p(text, *, size=11, bold=False, italic=False, sb=0, sa=2):
    return {"t": "para", "text": text, "size": size, "bold": bold, "italic": italic, "sb": sb, "sa": sa}


def _b(text, *, level=0):
    return {"t": "bullet", "text": text, "level": level}


def _hr():
    return {"t": "hr"}


def _sp(size=8):
    return {"t": "spacer", "size": size}


def resolve_contact(real_contact: bool):
    """Return (email, phone). Phone is omitted (None) from the public document."""
    if real_contact:
        return email_real(), phone_real()
    return email_obfuscated(), None


def build_blocks(data: dict, *, real_contact: bool = False) -> list[dict]:
    """Assemble the full ordered block list for the combined ATS resume.

    Format-agnostic: renderers map block types to DOCX paragraphs or HTML tags.
    The footer note (with a build timestamp) is appended by each builder, not here,
    so build_blocks stays deterministic.
    """
    basics = data["basics"]
    email, phone = resolve_contact(real_contact)
    loc = basics.get("location", {})
    blocks: list[dict] = []

    # ====== HEADER: name + title + contact ======
    blocks.append(_p(basics["name"], size=20, bold=True, sb=0, sa=2))
    blocks.append(_p(basics["label"], size=12, sa=4))

    contact_parts = []
    if loc:
        country = COUNTRY_MAP.get(loc.get("countryCode", ""), loc.get("countryCode", ""))
        contact_parts.append(f"{loc.get('city','')}, {loc.get('region','')}, {country}")
    # Text labels (no icons) — research: ATS read icons as garbage; bare values lose context.
    if phone:
        contact_parts.append(f"Phone: {phone}")
    if email:
        contact_parts.append(f"Email: {email}")
    li = next((p["url"] for p in basics.get("profiles", []) if p["network"].lower() == "linkedin"), None)
    if li:
        contact_parts.append(f"LinkedIn: {li}")
    if basics.get("url"):
        contact_parts.append(f"Web: {basics['url']}")
    blocks.append(_p(" | ".join(contact_parts), size=10, sa=8))
    blocks.append(_hr())

    # ====== PROFESSIONAL SUMMARY ======
    blocks.append(_h("Professional Summary"))
    blocks.append(_p(basics["summary"], size=11, sa=6))
    for line in basics.get("experienceLines", []):
        blocks.append(_b(f"{line['years']} - {line['text']}"))
    if basics.get("certifiedSummary"):
        blocks.append(_p(f"Certified: {basics['certifiedSummary']}", size=11, sb=4, sa=6))
    if basics.get("subSummary"):
        blocks.append(_p(basics["subSummary"], size=11, sa=6))

    # ====== CORE COMPETENCIES ======
    blocks.append(_h("Core Competencies"))
    skills = data.get("skills", [])
    if skills:
        skill_names = [f"{s['name']} ({s.get('yearsExperience', '')} yrs)" if s.get("yearsExperience")
                       else s["name"] for s in skills]
        blocks.append(_p(" | ".join(skill_names), size=11, sa=6))
    if data.get("highlights"):
        callouts = [h["text"] if isinstance(h, dict) else h for h in data["highlights"]]
        blocks.append(_p("Key strengths: " + " | ".join(callouts), size=11, sa=8))

    # ====== WORK EXPERIENCE ======
    blocks.append(_h("Work Experience"))
    work = data.get("work", [])
    recent = [w for w in work if not w.get("earlierCareer")]
    earlier = [w for w in work if w.get("earlierCareer")]

    for role in recent:
        blocks.append(_sub(f"{role['name']} - {role.get('position','')}"))
        meta_parts = [date_range(role.get("startDate"), role.get("endDate"))]
        if role.get("location"):
            meta_parts.append(role["location"])
        if role.get("employmentType"):
            meta_parts.append(role["employmentType"])
        blocks.append(_p(" | ".join(meta_parts), size=10, italic=True, sa=4))

        if role.get("context"):
            blocks.append(_p(role["context"], size=11, italic=True, sa=4))
        if role.get("summary"):
            blocks.append(_p(role["summary"], size=11, sa=4))
        if role.get("clients"):
            blocks.append(_p("Clients: " + ", ".join(role["clients"]), size=11, sa=4))

        for h in role.get("highlights", []):
            text = h["text"] if isinstance(h, dict) else h
            if isinstance(h, dict) and h.get("metric"):
                text = f"{text} [{h['metric']}]"
            blocks.append(_b(text))

        if role.get("projects"):
            for p in role["projects"]:
                blocks.append(_p(f"  Project: {p['name']}", size=11, bold=True, sb=4, sa=2))
                if p.get("role"):
                    blocks.append(_p(f"  Role: {p['role']}", size=11, italic=True, sa=2))
                for ph in p.get("highlights", []):
                    blocks.append(_b(ph, level=1))

        # Keyword blocks appended as plain text — ATS-friendly
        if role.get("softSkills"):
            blocks.append(_p("Soft skills: " + ", ".join(role["softSkills"]), size=10, sa=2))
        if role.get("hardSkills"):
            blocks.append(_p("Hard skills: " + ", ".join(role["hardSkills"]), size=10, sa=2))
        if role.get("agilePractices"):
            blocks.append(_p("Agile practices: " + ", ".join(role["agilePractices"]), size=10, sa=2))

    # ====== EARLIER CAREER ======
    if earlier:
        blocks.append(_h("Earlier Career"))
        for role in earlier:
            line = (f"{role['name']} - {role.get('position','')} - "
                    f"{date_range(role.get('startDate'), role.get('endDate'))}")
            if role.get("location"):
                line += f" - {role['location']}"
            blocks.append(_b(line))

    # ====== EDUCATION ======
    blocks.append(_h("Education"))
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
        blocks.append(_b(line))

    # ====== CERTIFICATIONS ======
    blocks.append(_h("Certifications and Qualifications"))
    for c in data.get("certifications", []):
        blocks.append(_b(f"{c['name']} - {c.get('issuer','')} - {c.get('date','')}"))

    # ====== SKILLS MATRIX ======
    blocks.append(_h("Skills - Years of Experience"))
    matrix = data.get("skillsByCategory", {})
    if matrix.get("softSkills"):
        blocks.append(_p("Soft Skills:", size=11, bold=True, sb=4, sa=2))
        blocks.append(_p(", ".join(f"{s['name']} ({s['years']} yrs)" for s in matrix["softSkills"]), size=11, sa=4))
    if matrix.get("technologies"):
        blocks.append(_p("Technologies:", size=11, bold=True, sb=4, sa=2))
        blocks.append(_p(", ".join(f"{s['name']} ({s['years']} yrs)" for s in matrix["technologies"]), size=11, sa=4))

    # ====== DIRECTORSHIPS ======
    if data.get("directorships"):
        blocks.append(_h("Directorships and Board Positions"))
        for d in data["directorships"]:
            blocks.append(_b(f"{d['title']} ({d['startDate']} - {d['endDate']})"))

    # ====== PROFESSIONAL MEMBERSHIPS ======
    if data.get("memberships"):
        blocks.append(_h("Professional Memberships"))
        for m in data["memberships"]:
            blocks.append(_b(m))

    # ====== SIDE PROJECTS ======
    if data.get("sideProjects"):
        blocks.append(_h("Side Projects"))
        for p in data["sideProjects"]:
            blocks.append(_b(f"{p['name']} ({p['url']}) - {p['description']}"))

    # ====== PERSONAL ACHIEVEMENTS ======
    if data.get("personalAchievements"):
        blocks.append(_h("Personal Achievements"))
        for a in data["personalAchievements"]:
            date = a.get("since") and f"since {a['since']}" or a.get("date", "")
            line = a["text"]
            if date:
                line += f" - {date}"
            if a.get("url"):
                line += f" ({a['url']})"
            blocks.append(_b(line))

    # ====== RECRUITER FAQ ======
    faq = data.get("recruiterFAQ")
    if faq:
        blocks.append(_h("Recruiter FAQ"))
        blocks.append(_b(f"Availability: {faq['availability']}"))
        blocks.append(_b(f"Visa: {faq['visa']}"))
        blocks.append(_b(f"Rates - Contract: {faq['rates']['contract']}"))
        blocks.append(_b(f"Rates - Permanent: {faq['rates']['permanent']}"))
        floc = faq["location"]
        blocks.append(_b(f"Location: {floc['based']}; looking in {', '.join(floc['lookingIn'])}; "
                         f"{floc['relocation']}; travel {floc['travel']}"))
        blocks.append(_b(f"Preferred roles: {' | '.join(faq['rolesPreferred'])}"))
        blocks.append(_b(f"Short-term: {' | '.join(faq['rolesShortTerm'])}"))
        blocks.append(_b(f"Holidays: {faq['holidays']}"))
        if faq.get("perfectJob"):
            blocks.append(_p(f"Ideal: {faq['perfectJob']}", size=11, italic=True, sb=4))

    # ====== REFERENCES ======
    blocks.append(_h("References"))
    blocks.append(_p("Available on request.", size=11, sa=4))

    return blocks
