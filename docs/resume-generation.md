# Resume + Cover-Letter Generation — Spec

Status: **dormant as of Sep 2026** — Paul is employed (Fusion5) and not seeking work, so the
JD-tailoring generator in §10 is not live backlog. The rules below stay valid as the contract if
it is ever picked up again; do not treat §10 as queued work.

This doc is both the best-practice reference and the generator contract. The rules here ARE
the generator's algorithm and the test oracle.

Acronyms: **JD** = job description · **CL** = cover letter · **KSC** = key selection criteria.

---

## 1. One-sentence scope

Given a JD (pasted text or URL), produce a role-tailored resume PDF and a tailored cover letter,
grounded only in verified facts, output to the gitignored `out/` folder.

## 2. Inputs

- **JD**: pasted raw text OR a URL (Seek/LinkedIn/company careers page). URL path fetches +
  extracts; brittle sites fall back to "paste the text".
- **Canonical source of truth**: `resume.json` (never invented content).
- Optional: explicit overrides (target title, must-have keywords) if the JD signal is weak.

## 3. Outputs (all to `out/<company>-<role>/`)

| Artefact | Format | Notes |
|----------|--------|-------|
| Tailored resume | **PDF (default)** | A4, ATS-clean. DOCX fallback when posting explicitly asks for Word. |
| Cover letter | PDF (+ DOCX fallback) | Narrative fit, company hook, addressee if known. |
| KSC statement | PDF | **Only** for AU formal postings with stated selection criteria (gov/uni/big-corp), STAR format. |
| Run manifest | `manifest.json` | Chosen title, JD keywords met/unmet, every company claim + source URL, rephrasings flagged. For Paul's review before sending. |

### Filename convention
Candidate name **leads** every artefact (recruiter/ATS files it by who, not by what):

```
out/<Company>-<Role>/
  Paul Harvey - Resume - <Company>.pdf
  Paul Harvey - Cover Letter - <Company>.pdf
  Paul Harvey - KSC - <Company>.pdf        # deferred, formal AU postings only
  manifest.json
```

- Role lives in the folder; Company in the filename (keeps names short, still self-identifying).
- Sanitise `<Company>`/`<Role>` to `[A-Za-z0-9 -]` (same rule the DOCX builder already uses).
- DOCX fallback variants reuse the same stem with `.docx`.

`out/` is gitignored (personal, per-application). Nothing here is committed.

### Site downloads section
The canonical (non-tailored) master resume is offered on the website as **PDF** going forward
(currently DOCX only). Add the PDF to the downloads section; keep DOCX as a secondary link.

## 4. Output format ruleset (research-backed)

### ATS (Workday / Greenhouse / Lever, 2026)
- Single-column, reverse-chronological. No nested tables / layout tables / text boxes / images / icons.
- System font (Calibri/Arial/Helvetica) 10–12pt body; larger name + headings.
- Standard section headers: "Professional Summary", "Work Experience", "Education", "Skills",
  "Certifications". No creative headings for core sections.
- Dates `Month YYYY` (or `MM/YYYY`). Long-form months preferred.
- Contact as text with labels (Phone: / Email: / LinkedIn:) — no icons (parsed as garbage).
- Spell acronyms on first use: "Search Engine Optimisation (SEO)".
- Mirror JD's **exact** terminology for keywords; place keywords in the top third.
- Text-selectable PDF parses as cleanly as DOCX and preserves layout → PDF default.

### Australian market
- A4, 2.5 cm margins. **Australian English** (organise, recognised, behaviour, optimise).
  Set document language to en-AU.
- 2 pp standard; **3 pp acceptable** for 15+ yr senior — every section must add demonstrable value.
- One-line context blurb for unfamiliar employers.
- No photo / DOB / marital status.
- Quantify achievements.

Sources: ResumeAdapter ATS-2026, Jobscan, Greenhouse parser guide, Refhub AU-2026, CrispResume AU-length.

## 5. Pipeline

```
JD (text|url)
  → [extract]      title, seniority, must-have keywords, criteria (if any), company name
  → [match/score]  JD keywords ↔ resume.json tags/skills → select + order highlights per role
  → [title pick]   choose from positionAliases (honest bounds only)
  → [trim]         enforce length budget; collapse earlierCareer
  → [company research] (CL only) values/news/benefits/addressee — each fact carries a source URL
  → [render]       resume PDF (HTML+print CSS → chromium page.pdf), CL, optional KSC
  → [verify]       accuracy cross-checks (§7) — BLOCKS output on failure
  → [manifest]     write review summary
```

PDF engine: **Chromium headless via Playwright `page.pdf()`** (already installed) rendering an
ATS print template. CSS owns A4/margins/single-column. Same `resume.json` feeds the existing
DOCX builder for the fallback path.

## 6. Per-JD company research (CL personalisation)

Goal: one genuine, specific hook so the CL reads as "did the homework" — not stuffing.

Pull (each with a captured source URL):
- **Values / mission** — About / careers page.
- **Recent news** — press / blog / announcement.
- **Distinctive benefits** — careers page / Glassdoor.
- **Addressee** — hiring manager / team lead name, only via corroborated source.

Rules:
- Use **one** strong hook, woven naturally. Never list facts back at them.
- Every company claim MUST trace to a source URL fetched in this run (see §7 verify).
- Addressee: use a named person **only if confidence is high and corroborated by ≥1 source**.
  Otherwise "Dear Hiring Manager" / "Dear <Team> Team". Never guess a name into the letter.
- No flattery that can't be sourced. No invented "I admire your X".

## 7. Accuracy cross-checks (the honesty gate) — BLOCKING

Output is withheld if any check fails. Two principles: **provenance** (every fact traces to a
source) and **faithfulness** (rephrasing adds no new claim).

### Resume (CV)
1. **Provenance** — every employer, title, date, certification, and **number/metric** in the
   output must exist in `resume.json`. Metrics only from `highlights[].metric`. Any
   date/number/employer/cert not in source → FAIL.
2. **Title legality** — chosen title ∈ {`position`, `positionDefault`, `positionAliases`} for
   that role. Else FAIL.
3. **Faithful rephrase** — if a highlight is reworded to mirror JD language, a faithfulness pass
   confirms the reworded line is entailed by the source highlight (no new capability claimed).
4. **Keyword honesty** — only surface JD keywords that genuinely match existing tags/skills.
   Unmet must-haves are **reported in the manifest as gaps**, never faked into the resume.

### Cover letter (CL)
5. **Paul-claims** — every claim about Paul traces to `resume.json` (provenance, as above).
6. **Company-claims** — every claim about the company traces to a source URL fetched this run;
   a verifier re-reads the URL to confirm the claim. Unverifiable → drop the sentence.
7. **Addressee** — named person only if §6 confidence rule passes.

### Both
8. **AU-English + spell lint.** 9. **Number lint** — no number appears unless present in a source.
10. **Manifest review** — keywords met/unmet, every company claim+source, chosen title, flagged
    rephrasings. Paul reviews before sending.

Heavy option (opt-in): run §7.3 / §7.6 as a multi-agent adversarial verify (N skeptics per
claim) instead of a single faithfulness pass.

## 8. Published-master build — DONE (foundation phase)

Both formats render from `scripts/resume_blocks.py::build_blocks()` (one source of truth).

- [x] **Page size A4** + 2.5 cm margins (DOCX was US Letter).
- [x] **Document language en-AU** (`w:lang` on docDefaults + Normal).
- [x] **Contact labels** — "Phone:/Email:/LinkedIn:/Web:".
- [x] **PDF master** via weasyprint (`build-resume-pdf.py`): A4, single-column, text-selectable,
      10pt Liberation Sans (Calibri/Carlito silently fall back to bulky DejaVu — lead the stack
      with the installed Liberation Sans). DOCX stays 11pt Calibri.
- [x] **Condense in place** — certs as one inline list (was 35 bullets), per-role keyword block
      merged to one line, skills-matrix label folded inline, tighter spacing. PDF 11pp → **8pp**,
      all content retained.
- [x] **Site downloads** — PDF primary, DOCX secondary ("Word version if your ATS prefers it").
- [x] **Deployed + verified** on production (apex serves `application/pdf`, 200).
- Build env: gitignored `.venv` (python-docx, weasyprint, pypdf — PEP 668 blocks global pip).
- Contact modes: default = obfuscated email / no phone (public, committed); `--real-contact` =
  real email + phone → `(full).pdf`/`(full).docx`, gitignored.
- Deploy: `scripts/deploy.sh` builds PDF + DOCX from `resume.json` → stamps `data-version` into
  `index.html` → commits changed artifacts → `wrangler pages deploy public/`. Creds from the
  gitignored repo-root `.env`. (No staging dir and no secret-grep any more: `public/` IS the
  deploy root, so only served files are ever in scope.)
  resume.json is the single source of truth (SyncThing direction dropped). `_worker.js` hard-404s
  any `(full)` path with `no-store`. (Both guards added after a real-contact DOCX leaked 2026-06-01.)
- Acronym first-use expansion — still a content-level TODO for the JD-targeted generator.

## 9. Open build-time decisions

1. ~~PDF engine~~ — **RESOLVED: weasyprint** (pure-Python, native @page, no browser/node).
2. CL length/tone template — 3-para vs criteria-mapped. (Decide against the first real JD.)
3. KSC mode — **deferred** until first formal AU posting that needs it. Resume + CL first.

## 10. Next phase — the generator (build against the first real JD)

Foundation (§8) is done. The generator core is unbuilt:
JD (paste text/URL) → extract → match/score vs tags → select+order highlights → pick title from
aliases → trim → (CL) company research → render tailored PDF + CL via the shared block model →
accuracy gate (§7) → manifest. Build it driven by a real JD so the matching/verify logic is tested
on real input, not invented cases.
