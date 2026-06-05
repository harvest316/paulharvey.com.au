"""Tests for build-resume-pdf.py: HTML rendering helpers + main()."""

from __future__ import annotations

import pytest


def test_esc(pdf_mod):
    assert pdf_mod.esc(None) == ""
    assert pdf_mod.esc("") == ""
    assert pdf_mod.esc("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_para_html_h1(pdf_mod):
    out = pdf_mod.para_html({"t": "para", "text": "Name", "size": 20})
    assert out == "<h1>Name</h1>"


def test_para_html_title(pdf_mod):
    blk = {"t": "para", "text": "Title", "size": 12, "bold": False, "italic": False}
    assert pdf_mod.para_html(blk) == '<p class="title">Title</p>'


def test_para_html_styled(pdf_mod):
    blk = {"t": "para", "text": "X", "size": 10, "bold": True, "italic": True}
    out = pdf_mod.para_html(blk)
    assert "font-size:10pt" in out
    assert "font-weight:bold" in out
    assert "font-style:italic" in out


def test_para_html_plain(pdf_mod):
    blk = {"t": "para", "text": "X", "size": 11}
    assert pdf_mod.para_html(blk) == "<p>X</p>"


def test_para_html_size12_bold_is_styled_not_title(pdf_mod):
    # size 12 but bold -> not the title branch
    blk = {"t": "para", "text": "X", "size": 12, "bold": True, "italic": False}
    out = pdf_mod.para_html(blk)
    assert 'class="title"' not in out
    assert "font-size:12pt" in out


def test_blocks_to_html_all_types(pdf_mod, blocks_mod):
    blocks = [
        blocks_mod._p("Name", size=20),
        blocks_mod._h("Section"),
        blocks_mod._sub("Role"),
        blocks_mod._p("para", size=11),
        blocks_mod._b("bullet one"),
        blocks_mod._b("bullet two"),       # consecutive -> same <ul>
        blocks_mod._b("nested", level=1),  # li.sub
        blocks_mod._hr(),                  # closes the list
        blocks_mod._b("after hr"),         # opens a new <ul>
        blocks_mod._sp(6),
    ]
    html = pdf_mod.blocks_to_html(blocks, "footer text", author="Jane",
                                  doc_title="Jane - Resume", subject="Dev",
                                  date="2026-06-04")
    assert "<h1>Name</h1>" in html
    assert '<h2 class="section">Section</h2>' in html
    assert '<h3 class="role">Role</h3>' in html
    assert html.count("<ul>") == 2  # one group of bullets, then one after the hr
    assert '<li class="sub">nested</li>' in html
    assert "<hr>" in html
    assert '<div style="height:6pt"></div>' in html
    assert '<p class="foot">footer text</p>' in html
    # head metadata
    assert "<title>Jane - Resume</title>" in html
    assert '<meta name="author" content="Jane">' in html
    assert '<meta name="description" content="Dev">' in html
    assert '<meta name="dcterms.created" content="2026-06-04">' in html
    assert 'lang="en-AU"' in html


def test_blocks_to_html_no_footer_no_meta(pdf_mod, blocks_mod):
    html = pdf_mod.blocks_to_html([blocks_mod._p("x", size=11)], "")
    assert 'class="foot"' not in html
    assert "<title>" not in html
    assert 'name="author"' not in html
    assert 'name="dcterms' not in html


def test_blocks_to_html_unknown_raises(pdf_mod):
    with pytest.raises(ValueError, match="Unknown block type"):
        pdf_mod.blocks_to_html([{"t": "bogus"}], "")


def test_main_default(pdf_mod, monkeypatch, tmp_path, capsys):
    out = tmp_path / "Resume.pdf"
    monkeypatch.setattr(pdf_mod, "OUT_PDF", out)
    monkeypatch.setattr("sys.argv", ["build-resume-pdf.py"])
    pdf_mod.main()
    assert out.exists() and out.stat().st_size > 0
    assert out.read_bytes()[:4] == b"%PDF"
    assert "obfuscated" in capsys.readouterr().out


def test_main_keep_html_and_real_contact(pdf_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(pdf_mod, "REPO", tmp_path)
    monkeypatch.setattr("sys.argv", ["build-resume-pdf.py", "--real-contact", "--keep-html"])
    pdf_mod.main()
    out = tmp_path / "out" / "full-contact" / "Paul Harvey - Resume (full).pdf"
    assert out.exists()
    assert out.with_suffix(".html").exists()
    assert "REAL" in capsys.readouterr().out
