# Resume Generation Workflow

The canonical resume lives in [`/resume.json`](../resume.json) at the repo root, using the [JSON Resume schema](https://jsonresume.org/schema/) with Paul-specific extensions.

## Files

| Path | Purpose |
|------|---------|
| `/resume.json` | Single source of truth. Superset of every role-targeted variant. |
| `/index.html` | Renders `resume.json` client-side into the public site. |
| `/cv/docs/Paul Harvey - Resume.{pdf,docx}` | Master resume, **generated from `resume.json`** — not hand-edited. |
| `/scripts/resume_blocks.py` | Shared format-agnostic block model both builders consume. |
| `/scripts/build-resume-pdf.py` | Builds the A4 PDF (weasyprint) from `resume.json`. |
| `/scripts/build-resume-docx.py` | Builds the ATS DOCX (python-docx) from `resume.json`. |
| `/scripts/deploy.sh` | Builds both artifacts from `resume.json` + deploys (replaces `sync-resumes.sh`). |
| `/scripts/generate-resume.mjs` | *(future)* Builds a role-targeted PDF/DOCX from `resume.json` + a JD. |

## Schema extensions

The site renderer + future generator look for these non-standard fields on top of the JSON Resume v1.0.0 spec:

- `basics.tagline`, `basics.subSummary` — secondary copy for hero + summary.
- `highlights[]` — top-of-fold callouts shown as chips on the hero.
- `stats[]` — big-number row on the home page.
- `work[].tags`, `work[].highlights[].tags` — taxonomy keys for filtering / scoring against a JD.
- `work[].highlights[].metric` — pull-quote callout (e.g. `"+210% efficiency"`).
- `work[].positionFlexible` + `positionDefault` + `positionAliases[]` — for roles where Paul effectively chose his own title (self-employed periods and Charles Marcus). The generator picks the alias closest to the target JD title.
- `work[].earlierCareer: true` — collapse this role under the "Earlier Career" disclosure (pre-2008 roles).
- `work[].softSkills[]`, `work[].hardSkills[]`, `work[].agilePractices[]` — verbatim from source resumes; rendered inline.
- `work[].projects[]` — sub-engagements within consulting roles.
- `skills[]` — JSON-Resume-spec compatible top skills, tagged.
- `skillsByCategory.softSkills[]`, `skillsByCategory.technologies[]` — the years-of-experience matrix.
- `directorships[]`, `memberships[]`, `sideProjects[]`, `personalAchievements[]` — additional sections.
- `meta.paul.tagVocabulary[]` — closed list of allowed `tags` values.

## Tag vocabulary

Locked from JD frequency analysis of 20 senior Sydney IT roles (May 2026):

```
architecture · cloud · ai-llm · integration · erp · microsoft · security-compliance ·
data-analytics · networking-infra · presales · crm · devops · financial-services ·
ecommerce · leadership · offshore-teams · stakeholder · transformation ·
cost-optimisation · knowledge-mgmt · mobile
```

When adding a new highlight or skill, pick from this list. To add a new tag, update `meta.paul.tagVocabulary` and document the rationale.

## Generating a role-targeted resume

Until `generate-resume.mjs` is built, the workflow is:

1. **Receive JD** — paste / save the job description.
2. **Score against tags** — identify the top 5–8 tags in the JD (cloud, ai-llm, ecommerce, etc).
3. **Select position aliases** — for each `positionFlexible: true` role, pick the alias closest to the target JD title.
4. **Filter highlights** — keep the top 3–5 highlights per role whose `tags` overlap the JD tags. Drop the rest.
5. **Filter skills** — surface only the matching `skills[]` entries in the summary block; full matrix stays as an appendix or web link.
6. **Render** — to a 2-page DOCX/PDF, header carrying `paulharvey.com.au` as the canonical URL.
7. **Write cover letter** — 300–350 words, 3–4 paragraphs, complementary to (not duplicating) the resume.

See [resume best practices research](#) referenced in commit history for the source of these targets.

## Updating the canonical resume

1. Edit `resume.json`.
2. Bump `meta.version` and `meta.lastModified`.
3. Test locally: `npx http-server .` then open `localhost:8080`. The site fetches `resume.json` and renders all sections.
4. Commit. Deploy runs through normal Cloudflare Pages CI.

## Resume downloads (PDF + DOCX)

The master resume at `/cv/docs/` is **generated from `resume.json`** (the single source of truth) — no longer authored externally or synced from SyncThing. Build + deploy with:

```
./scripts/deploy.sh
```

It builds the public PDF + DOCX (deterministic — footer from `meta.lastModified`), commits them only if changed, then deploys a clean staging dir. Safety: only git-tracked `cv/docs` files are staged, and anything matching `*(full)*` / `.env` / `*.py` aborts the deploy (a real-contact `(full)` DOCX leaked once via a `*.docx` glob). Cloudflare Pages is **not** git-connected — a push does not deploy; run this script.

## Subdomain behaviour

`cv.paulharvey.com.au` is preserved for legacy links:

- `cv.paulharvey.com.au/docs/<file>.docx` → redirects to `paulharvey.com.au/cv/docs/<file>.docx`
- `cv.paulharvey.com.au/` (or any other path) → redirects to `paulharvey.com.au/#downloads`
- Main domain `/cv` and `/cv/` → redirect to `/#downloads` (the standalone CV page was removed in favour of the unified resume on the home page).

Worker implementation: [`/_worker.js`](../_worker.js).
