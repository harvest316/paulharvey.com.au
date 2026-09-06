# paulharvey.com.au — Project Instructions

## Scope isolation (mandatory)

This project contains personal information (resume, contact details, rates, references). Treat it as an isolated context. **Project-local memory only — no cross-project bleed.**

- Do **NOT** read, reference, cite, or carry over context from any other project (`~/code/333Method`, `~/code/mmo-platform`, `~/code/ContactReplyAI`, etc.) when working in this directory.
- Do **NOT** write personal info from this project (Paul's email, phone, rates, holidays, references, day-rate band, recruiter FAQ content) to:
  - `~/.claude/CLAUDE.md` (global, all projects)
  - `~/code/mmo-platform/docs/decisions.md` (cross-project decision register)
  - Any other project's memory directory
  - Subagent prompts that span multiple projects
- The **only** correct place for paulharvey-specific facts is the project-local memory:
  `~/.claude/projects/-home-jason-code-paulharvey-com-au/memory/`
- The DR-NNN decision register convention from global `~/.claude/CLAUDE.md` does **NOT** apply here. paulharvey is a standalone single-purpose artefact.
- Subagent prompts spawned from this project must not cite other projects' filenames, decisions, or patterns.

## What lives where

**`public/` is the deploy root** — wrangler publishes `public/` and nothing else. Every served file lives there; source, tooling and secrets live outside it (so they can never be published).

| Path | Purpose |
|------|---------|
| `public/resume.json` | Canonical JSON Resume schema + Paul-specific extensions. Single source of truth (also served at `/resume.json`). |
| `public/index.html` | Renders `resume.json` client-side. Don't hand-edit role copy here — edit JSON. |
| `public/cv/docs/` | Pre-generated public PDF + DOCX downloads (obfuscated contact). |
| `public/_worker.js` | Cloudflare Pages worker handling cv subdomain + redirects. |
| `public/_headers` / `public/_redirects` | Static config for Cloudflare Pages. |
| `public/images/` | Served images (hero, logos, og). |
| `scripts/` | Build automation (reads `public/resume.json`, writes `public/cv/docs/`). |
| `out/full-contact/` | Private real-contact `(full)` PDF/DOCX (gitignored, OUTSIDE `public/` — never deployed). |

## Editing rules

- All resume content lives in `public/resume.json`. Don't hand-edit role text in `public/index.html`.
- Bump `meta.version` and `meta.lastModified` on every `public/resume.json` edit. Keep the `data-version` attribute on `#resume-data` in `public/index.html` in sync with `meta.version` (deploy.sh re-stamps it, but match it manually too so committed state is correct).
- **No recruiter FAQ.** Removed Sep 2026: Paul is employed (Fusion5) and not seeking work. Do not reinstate a `recruiterFAQ` block in `resume.json` or an FAQ section on the site. The PDF/DOCX emitter in `scripts/resume_blocks.py` still has a guarded `recruiterFAQ` branch, so restoring it later is a JSON edit plus re-adding the site section (see git history at the removal commit).
- **Keep the noscript block in sync by hand.** The `<noscript>` fallback in `public/index.html` is a manual mirror of the work list and summary, not rendered from `resume.json`. Update it whenever the current role or summary changes.
- Side-project descriptions live in `resume.json` under `sideProjects[]`.
- **No referee names in `public/`.** Hidden Sep 2026 alongside the recruiter FAQ. The list is kept at `out/private/referees.json` (gitignored, outside the deploy root); restoring it means pasting the `references` array back into `resume.json`. The PDF/DOCX emitter hardcodes the "References / Available on request" heading, so it needs no change either way.
- Tag every new `highlights[]` entry from the closed vocabulary in `meta.paul.tagVocabulary`.

## Email + PII

Paul's email (`cv@paulharvey.com.au`) is obfuscated client-side via layered JS / Base64 / decoy text. **Do not** add plain `mailto:` links, plain `cv@paulharvey...` strings, or `schema.org` `email` JSON-LD fields to any HTML output. The phone number is similarly protected.

`resume.json` contains the real email + phone because the JSON is a downloadable canonical artefact intentionally consumed by recruiters / ATS. That's fine — it's not scraped by the standard spam harvesters that target HTML.

## Deploy

Two paths, both `wrangler pages deploy public/` (the `public/` scope means there is no staging dir, allowlist, or secret-grep — only served files live in `public/`, so nothing private can be published):

- **Push to `main`** → GitHub Actions (`.github/workflows/deploy.yml`) deploys using the repo's `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` GitHub Actions secrets. Normal path.
- **`scripts/deploy.sh`** → builds the public PDF + DOCX into `public/cv/docs/`, stamps the version into `public/index.html`, commits, then deploys directly using `CLOUDFLARE_*` from the gitignored repo-root `.env` (immediate local deploy without waiting on CI).

`.env` is safe in the repo root again: it sits OUTSIDE `public/`, so wrangler can never publish it. (History: a `(full)` DOCX and the token leaked in mid-2026 when deploys ran from the repo root via globbing; the `public/` scope is the structural fix.) Real-contact `(full)` variants build to `out/full-contact/`, outside `public/`.

## Logos

No employer logos anywhere — text-only employer names. AU Trade Marks Act 1995 s.122(1)(b)–(c) descriptive-use defence covers naming, not logo reuse; Big-4 + big-bank alumni contracts explicitly prohibit logo reuse. Footer carries a non-endorsement disclaimer regardless.
