"""Tests for resume_blocks: contact encoding, formatting helpers, block model."""

from __future__ import annotations

import pytest


# ---- Contact constants ----

# Expected contact values are DERIVED from the module's own encoded constants —
# never written as plaintext literals here, so this tracked test file introduces
# no scrapeable email/phone (same discipline as resume_blocks keeping them encoded).
def _expected_email_real(m):
    return f"{m._EMAIL_LOCAL}@{m._EMAIL_DOMAIN}"


def _expected_email_obf(m):
    return f"{m._EMAIL_LOCAL} [at] {m._EMAIL_DOMAIN.replace('.', ' [dot] ')}"


def _expected_phone_real(m):
    return "+61" + "".join(str(x) for x in m._PHONE_DIGITS)


def _expected_phone_obf(m):
    d = "".join(str(x) for x in m._PHONE_DIGITS)
    return f"+61 (0){d[:3]} {d[3:6]} {d[6:]}"


def test_email_obfuscated(blocks_mod):
    out = blocks_mod.email_obfuscated()
    assert out == _expected_email_obf(blocks_mod)
    assert "[at]" in out and "[dot]" in out and "@" not in out


def test_email_real(blocks_mod):
    out = blocks_mod.email_real()
    assert out == _expected_email_real(blocks_mod)
    assert out.count("@") == 1


def test_phone_obfuscated(blocks_mod):
    out = blocks_mod.phone_obfuscated()
    assert out == _expected_phone_obf(blocks_mod)
    assert " " in out  # spaced form defeats naive \d{10} bots


def test_phone_real(blocks_mod):
    out = blocks_mod.phone_real()
    assert out == _expected_phone_real(blocks_mod)
    assert out.startswith("+61") and " " not in out


def test_resolve_contact_real(blocks_mod):
    email, phone = blocks_mod.resolve_contact(True)
    assert email == _expected_email_real(blocks_mod)
    assert phone == _expected_phone_real(blocks_mod)


def test_resolve_contact_obfuscated(blocks_mod):
    email, phone = blocks_mod.resolve_contact(False)
    assert "[at]" in email
    assert phone is None


# ---- to_ascii ----

def test_to_ascii_empty(blocks_mod):
    assert blocks_mod.to_ascii("") == ""
    assert blocks_mod.to_ascii(None) == ""


def test_to_ascii_replacements(blocks_mod):
    src = "en–dash em—dash ’curly‘ “quotes” …dots · £10 €5 a→b ↗ 90° −1 a&b"
    out = blocks_mod.to_ascii(src)
    assert "–" not in out and "—" not in out
    assert "GBP10" in out
    assert "EUR5" in out
    assert "->" in out
    assert "degrees" in out
    assert "and" in out
    # non-mapped unicode is dropped by ascii-ignore
    assert "↗" not in out


def test_to_ascii_collapses_whitespace(blocks_mod):
    assert blocks_mod.to_ascii("  a\t\n  b  ") == "a b"


# ---- fmt_date / date_range ----

def test_fmt_date_none_is_present(blocks_mod):
    assert blocks_mod.fmt_date(None) == "Present"
    assert blocks_mod.fmt_date("") == "Present"


def test_fmt_date_year_only(blocks_mod):
    assert blocks_mod.fmt_date("2021") == "2021"


def test_fmt_date_year_month(blocks_mod):
    assert blocks_mod.fmt_date("2021-03") == "March 2021"
    assert blocks_mod.fmt_date("2021-12") == "December 2021"


def test_date_range(blocks_mod):
    assert blocks_mod.date_range("2020-01", "2021-06") == "January 2020 - June 2021"
    assert blocks_mod.date_range("2020-01", None) == "January 2020 - Present"


# ---- block constructors ----

def test_block_constructors(blocks_mod):
    assert blocks_mod._h("X") == {"t": "heading", "text": "X"}
    assert blocks_mod._sub("X") == {"t": "sub", "text": "X"}
    assert blocks_mod._hr() == {"t": "hr"}
    assert blocks_mod._sp() == {"t": "spacer", "size": 8}
    assert blocks_mod._sp(4) == {"t": "spacer", "size": 4}
    p = blocks_mod._p("X", size=12, bold=True, italic=True, sb=2, sa=3)
    assert p == {"t": "para", "text": "X", "size": 12, "bold": True,
                 "italic": True, "sb": 2, "sa": 3}
    b0 = blocks_mod._b("Y")
    assert b0 == {"t": "bullet", "text": "Y", "level": 0}
    b1 = blocks_mod._b("Y", level=1)
    assert b1["level"] == 1


# ---- build_blocks ----

def _texts(blocks):
    return [b.get("text", "") for b in blocks]


def test_build_blocks_full(full_data, blocks_mod):
    blocks = blocks_mod.build_blocks(full_data, real_contact=True)
    types = {b["t"] for b in blocks}
    assert {"heading", "sub", "para", "bullet", "hr"} <= types

    headings = [b["text"] for b in blocks if b["t"] == "heading"]
    for expected in ["Professional Summary", "Core Competencies", "Work Experience",
                     "Earlier Career", "Education", "Certifications and Qualifications",
                     "Skills - Years of Experience", "Directorships and Board Positions",
                     "Professional Memberships", "Side Projects", "Personal Achievements",
                     "Recruiter FAQ", "References"]:
        assert expected in headings

    joined = "\n".join(_texts(blocks))
    # real contact rendered (derived from module constants, not plaintext literals)
    assert f"Phone: {_expected_phone_real(blocks_mod)}" in joined
    assert f"Email: {_expected_email_real(blocks_mod)}" in joined
    assert "LinkedIn: https://linkedin.com/in/test" in joined
    assert "Web: https://example.com" in joined
    # location with mapped country
    assert "Sydney, NSW, Australia" in joined
    # skills with and without years
    assert "Architecture (15 yrs)" in joined
    assert "Leadership" in joined
    # highlights dict + string
    assert "Dict highlight" in joined
    assert "String highlight" in joined
    # metric appended
    assert "Metric highlight [+30%]" in joined
    # project role + nested highlight
    assert "Project: Project X" in joined
    assert "Role: Lead" in joined
    # keyword line
    assert "Soft skills: Comms" in joined
    assert "Hard skills: Python" in joined
    assert "Agile: Scrum" in joined
    # earlier career lines (with + without location)
    assert "OldCorp" in joined and "Melbourne" in joined
    # education with + without details
    assert "Uni - BSc - CompSci - 2008" in joined
    assert "Bare Institution" in joined
    # certifications with + without meta
    assert "Cert A (Issuer 2020)" in joined
    assert "Cert B" in joined
    # skills matrix
    assert "Technologies: Python (12 yrs)" in joined
    # directorship / membership / side project
    assert "Director (2018 - 2020)" in joined
    assert "ACS Member" in joined
    assert "Proj (https://p.example) - desc" in joined
    # personal achievements: since / date / none + url
    assert "Marathon - since 2015 (https://m.example)" in joined
    assert "Award - 2019" in joined
    assert "No date achievement" in joined
    # recruiter FAQ
    assert "Availability: Immediate" in joined
    assert "Ideal: Building things." in joined
    # references always
    assert "Available on request." in joined


def test_build_blocks_min(min_data, blocks_mod):
    blocks = blocks_mod.build_blocks(min_data, real_contact=False)
    headings = [b["text"] for b in blocks if b["t"] == "heading"]
    # absent sections must NOT appear
    for absent in ["Earlier Career", "Directorships and Board Positions",
                   "Professional Memberships", "Side Projects",
                   "Personal Achievements", "Recruiter FAQ"]:
        assert absent not in headings
    # core sections still render
    for present in ["Professional Summary", "Core Competencies", "Work Experience",
                    "Education", "References"]:
        assert present in headings
    joined = "\n".join(_texts(blocks))
    # obfuscated contact, no phone
    assert "[at]" in joined
    assert "Phone:" not in joined
    # no skills line, no location
    assert "Sydney" not in joined


def test_build_blocks_unknown_country(full_data, blocks_mod):
    full_data["basics"]["location"]["countryCode"] = "XX"
    blocks = blocks_mod.build_blocks(full_data)
    joined = "\n".join(_texts(blocks))
    # falls back to the raw code when not in COUNTRY_MAP
    assert "Sydney, NSW, XX" in joined


def test_build_blocks_faq_without_perfect_job(full_data, blocks_mod):
    del full_data["recruiterFAQ"]["perfectJob"]
    blocks = blocks_mod.build_blocks(full_data)
    joined = "\n".join(_texts(blocks))
    assert "Availability: Immediate" in joined
    assert "Ideal:" not in joined


def test_build_blocks_real_resume(real_data, blocks_mod):
    """The actual resume.json must build without error in both contact modes."""
    obf = blocks_mod.build_blocks(real_data, real_contact=False)
    real = blocks_mod.build_blocks(real_data, real_contact=True)
    assert len(obf) > 20
    assert len(real) >= len(obf)  # phone line adds at least nothing-or-more
    # every block has a valid discriminator
    valid = {"heading", "sub", "para", "bullet", "hr", "spacer"}
    assert all(b["t"] in valid for b in obf)
