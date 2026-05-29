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

| Path | Purpose |
|------|---------|
| `resume.json` | Canonical JSON Resume schema + Paul-specific extensions. Single source of truth. |
| `index.html` | Renders `resume.json` client-side. Don't hand-edit role copy here — edit JSON. |
| `cv/docs/` | Pre-generated DOCX downloads (the combined ATS-friendly resume + recruiter FAQ). |
| `scripts/` | Sync + build automation. |
| `_worker.js` | Cloudflare Pages worker handling cv subdomain + redirects. |
| `_headers` / `_redirects` | Static config for Cloudflare Pages. |

## Editing rules

- All resume content lives in `resume.json`. Don't hand-edit role text in `index.html`.
- Bump `meta.version` and `meta.lastModified` on every `resume.json` edit.
- Recruiter FAQ content lives in `resume.json` under `recruiterFAQ`. Site renders from there.
- Side-project descriptions live in `resume.json` under `sideProjects[]`.
- Tag every new `highlights[]` entry from the closed vocabulary in `meta.paul.tagVocabulary`.

## Email + PII

Paul's email (`cv@paulharvey.com.au`) is obfuscated client-side via layered JS / Base64 / decoy text. **Do not** add plain `mailto:` links, plain `cv@paulharvey...` strings, or `schema.org` `email` JSON-LD fields to any HTML output. The phone number is similarly protected.

`resume.json` contains the real email + phone because the JSON is a downloadable canonical artefact intentionally consumed by recruiters / ATS. That's fine — it's not scraped by the standard spam harvesters that target HTML.

## Deploy

Cloudflare Pages auto-deploys from `main`. `scripts/sync-resumes.sh` handles the SyncThing → repo → deploy chain for the DOCX downloads.

## Logos

No employer logos anywhere — text-only employer names. AU Trade Marks Act 1995 s.122(1)(b)–(c) descriptive-use defence covers naming, not logo reuse; Big-4 + big-bank alumni contracts explicitly prohibit logo reuse. Footer carries a non-endorsement disclaimer regardless.
