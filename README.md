# Engineering Document Acceptance

English | [简体中文](README.zh-CN.md)

An engineering-document intelligence audit and statement-generation project built on **[Agnes Harness (AGH)](https://github.com/AgnesAI-Labs/agnes-harness) + Skills**.

Uploaded materials are parsed and checked against configurable document and field lists for completeness / misfiling / conflicts / duplicates. An Agent then drafts a formal *Audit Statement* as a Word document.

> **Demo data is synthetic.** Rules follow publicly available government filing guidance. **No real project content is included.**

Contents

- [1. Project Overview](#1-project-overview)
- [2. Demo Video](#2-demo-video)
- [3. Architecture](#3-architecture)
- [4. Integration Standards](#4-integration-standards)
- [Setup and Run](#setup-and-run)
- [Notes and Boundaries](#notes-and-boundaries)
- [Attribution](#attribution)

---

## 1. Project Overview

### Background

Before construction project acceptance, owners and archive authorities must verify that project files are complete and consistent: check missing items against a configurable checklist, detect files from other projects, cross-document field conflicts and duplicates, and produce a written statement.

Manual review is experience-heavy and slow. Filing catalogs and project types also vary by locality, so a single hard-coded rule set does not travel well.

This project automates that field workflow: checklist matching, field extraction, and conflict detection run as deterministic scripts; statement drafting is handled by Agent Skills—reproducible, configurable, and auditable.

### Core capabilities


| Capability | Skill / module | Description |
| --- | --- | --- |
| Completeness and consistency audit | `engineering-archive-audit` | Checklist matching, draft field extraction, missing / misfiled / conflict / duplicate findings, evidence-linked report |
| Statement generation | `engineering-doc-generator` | `prepare` → Agent drafts body → `build` exports *Engineering Document Audit Statement* `.docx` |
| Web UI | `web/` + `server/` | Upload by project batch, set primary reference, one-click AGH audit, view results, download statement Word |
| Multi-type rules | `rules/*.json` | Housing, road / bridge, municipal pipeline; add or edit profiles as needed |


Three built-in housing demos for capability checks:

- `demo-housing-mixed`: misfiled files, ID / amount conflicts, duplicates, missing formal acceptance and fire materials
- `demo-housing-near-miss`: start-date conflict, missing material tests, unreadable scanned pages
- `demo-housing-complete`: complete materials with consistent fields (clean control pack)

### Highlights

1. **Scripts first**: checklist matching, PDF text-layer field extraction, and draft conflict / missing checks are deterministic; the Agent only uses the brief for review and statement writing—lower token use, faster runs, more stable results.
2. **Configurable rules**: the four-part `rules/*.json` structure can be swapped by region and project type.
3. **Primary-reference anchoring**: identity fields are taken from a primary file such as the construction permit, so cross-file consistency has a clear baseline; the primary file can be set by the user or chosen automatically.
4. **Traceable findings**: each finding carries checklist codes, similar files, rationale, and evidence excerpts, and can be exported as a formal Word statement.
5. **Agnes Harness foundation**: end-to-end AGH + Skills; the web workbench starts Agent sessions via a local API, with replay in AGH Trace / session views.

---

## 2. Demo Video

Demo video: **工程文件核查.mp4**

- Link: [https://pan.baidu.com/s/1X4Yt7zPsa0dvkiozLd251A?pwd=0000](https://pan.baidu.com/s/1X4Yt7zPsa0dvkiozLd251A?pwd=0000)
- Extraction code: `0000`

---

## 3. Architecture

### Overall architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Web workbench (Vite + React, :5173)                         │
│  Upload / primary ref / start audit / results / download Word│
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP /api/*
┌────────────────────────────▼────────────────────────────────┐
│  Local API (Express, :8787)                                  │
│  cases on disk · files · start/cancel AGH · findings / stmt  │
└────────────────────────────┬────────────────────────────────┘
                             │ CLI / session
┌────────────────────────────▼────────────────────────────────┐
│  Agnes Harness Agent (:4177 Web)                             │
│  Read Skills → run scripts → spot-check → draft statement    │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
        ▼                               ▼
 engineering-archive-audit      engineering-doc-generator
 audit_prepare.py               generate.js prepare / build
 rules/*.json                   body.md → .docx
        │                               │
        └──────────► cases/<id>/ ◄──────┘
                     files/  manifest.json  _work/  doc/
```

### Core modules


| Module | Path | Role |
| --- | --- | --- |
| Audit Skill | `.agh/skills/engineering-archive-audit/` | Audit flow; `scripts/audit_prepare.py` writes inventory / classification / fields / findings / audit-report |
| Statement Skill | `.agh/skills/engineering-doc-generator/` | `prepare` builds facts / outline / agent-brief; Agent writes `正文.md`; `build` exports Word |
| Rule profiles | `rules/housing-construction.json`, etc. | Required documents, primary reference, consistency rules (R-001 / R-002 / R-003) |
| Local API | `server/` | Case CRUD, upload, primary reference, AGH audit launch, findings and statement Word |
| Web UI | `web/` | User → project-batch UX; `/api` proxied to 8787 |
| Demos and references | `cases/`, `reference/`, `tools/` | Synthetic packs, public catalog index, generation and fetch scripts |


### Pipeline

1. **Ingest**: enumerate files under `cases/<id>/files/` or an uploaded folder into `_work/inventory.json`.
2. **Classify**: combine filename aliases, title keywords, and rule `category` into `classification.json`.
3. **Primary reference**: user-selected or auto-chosen (e.g. construction permit); if none, stop the formal audit and mark `needs_human_review`.
4. **Field extraction**: page-by-page PDF text layer; cross-file consistency via `global` / `scoped`. OCR for scans can be added later.
5. **Completeness and consistency**: against `required_documents`, emit provided / missing / suspect_duplicate_or_misfiled / needs_human_review per item; misfiled files do not count as provided and are excluded from this-project field conflicts.
6. **Agent statement**: read `audit-brief.md` / findings; the statement Skill produces the formal Word document.

---

## 4. Integration Standards

### Directory conventions


| Path | Convention |
| --- | --- |
| `cases/<id>/manifest.json` | Project metadata, `project_type` / `rules_profile`, primary reference, field anchors |
| `cases/<id>/files/` | User materials (read-only during audit) |
| `cases/<id>/_work/` | Writable outputs from scripts and Agent (findings, reports, body, etc.) |
| `cases/<id>/doc/` | Exported statement `.docx` |
| `.agh/skills/*/rules/*.json` | Archive rule profiles (replaceable on site) |


### Rule profile interface

Each `rules/*.json` **must** include:


| Key | Meaning |
| --- | --- |
| `manifest_fields` | Structured fields for consistency checks (including `consistency`: `global` \| `scoped`) |
| `primary_reference` | Primary reference definition (`code` / `name` / `aliases`) |
| `required_documents` | Required document checklist (completeness matching) |
| `consistency_rules` | At least R-001 (field scope), R-002 (vs manifest), R-003 (cross-file) |


Completeness status machine: `provided` | `missing` | `suspect_duplicate_or_misfiled` | `needs_human_review`.

### Local HTTP API

Default port: `8787`. The frontend proxies `/api` here via Vite.


| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Health check and AGH config summary |
| `GET` | `/api/config` | AGH CLI / Web origin / workspace path |
| `POST` | `/api/cases` | Create project batch (identity required) |
| `GET/PATCH` | `/api/cases/:id`… | Read / update manifest and primary reference |
| `GET/POST/DELETE` | `/api/cases/:id/files`… | List, upload, rename, move, delete |
| `POST` | `/api/cases/:id/audit` | Start AGH audit session |
| `GET` | `/api/cases/:id/audit/status` | Audit process status |
| `POST` | `/api/cases/:id/audit/cancel` | Cancel audit |
| `GET` | `/api/cases/:id/findings` | Structured results (with AGH session link) |
| `GET` | `/api/cases/:id/audit-detail` | Fields / consensus / evidence detail |
| `GET` | `/api/cases/:id/statement` | Statement generation status |
| `GET` | `/api/cases/:id/statement/download` | Download `.docx` |


Upload limits (default): ≤ 80MB per file, ≤ 200 files per request. Paths are relative to `cases/<id>/files/`.

### Deterministic script CLI

Paths below are relative to `engineering-document-acceptance/` (the AGH workspace):

```bash
# Audit prepare (EDA workspace root)
python .agh/skills/engineering-archive-audit/scripts/audit_prepare.py --case cases/demo-housing-mixed

# Statement (in the statement Skill directory)
cd .agh/skills/engineering-doc-generator
node scripts/generate.js prepare --case ../../../cases/demo-housing-mixed
# After the Agent writes cases/.../_work/正文.md:
node scripts/generate.js build --case ../../../cases/demo-housing-mixed
```

### Technical standards and references

- Ministry of Housing and Urban-Rural Development *Code for Archiving Construction Project Documents* and related local filing catalogs / guides / blank forms inform the rule profiles; **a given project is governed by the currently loaded JSON checklist**.
- Synthetic demo layouts follow public permit / contract model texts / GB 50300 appendix forms (see `reference/*/SOURCES.txt`).
- Formal administrative acceptance is defined by competent authorities; this project assists audit and record-keeping and does not replace official acceptance decisions.

---

## Setup and Run

### Install

Project code lives under `engineering-document-acceptance/`; AGH source is the sibling `agnes-harness/` directory in this monorepo.

1. Prerequisites: Node.js, Python 3.
2. Build the local AGH CLI (in the `agnes-harness` directory):

```bash
pnpm install --frozen-lockfile
pnpm --filter @agnes/cli build:local
```

3. Install EDA dependencies (from the monorepo root):

```bash
pip install pymupdf
cd engineering-document-acceptance/.agh/skills/engineering-doc-generator && npm install
cd ../../../server && npm install
cd ../web && npm install
```

Or run monorepo-root `.\setup.ps1` to build AGH and install EDA dependencies in one step. Monorepo layout notes live in [`docs/README.md`](docs/README.md).

### One-shot start

```powershell
# From the monorepo root
.\start.ps1
# Or: cd engineering-document-acceptance; .\start-dev.ps1
```

Open the URL printed in the terminal (usually `http://127.0.0.1:5173`). This starts the API (8787), frontend (5173), and AGH Web (4177).

### Step-by-step start

```bash
# 1) API
cd engineering-document-acceptance/server && npm run dev

# 2) Frontend
cd engineering-document-acceptance/web && npm run dev

# 3) AGH (workspace must be the EDA directory)
node agnes-harness/packages/cli/dist/local/agnes.mjs serve --cwd <absolute-path-to-engineering-document-acceptance>
```

### Connect and use

1. Add the `engineering-document-acceptance` directory as an AGH **workspace** (`--cwd` points there, same as when the API starts AGH).
2. In Skills management, refresh and enable:
  - `engineering-archive-audit`
  - `engineering-doc-generator`
3. Start a session using `TEST_PROMPT.txt` under the case, or a task like:

```text
Please use engineering-archive-audit on cases/demo-housing-mixed for completeness and consistency checking of completion materials;
prefer scripts for steps the scripts can do; do not read every PDF end-to-end.

After the audit, use engineering-doc-generator to produce the *Completion Materials Audit Statement* and export Word.

Cover: missing items, misfiled files, field conflicts, and duplicates.
```

You can also click **Audit** in the web workbench: the API starts a local AGH CLI session, and the UI can open the AGH web page to follow progress.

### Demo PDFs

If `engineering-document-acceptance/cases/*/files/` is missing, generate locally:

```bash
cd engineering-document-acceptance
python tools/generate_demo_case.py
python tools/generate_near_miss_case.py
python tools/generate_complete_case.py
python tools/fetch_public_pdfs.py
```

---

## Notes and Boundaries

- This repo is an AGH Skill demo and local audit workbench; it is **not** the Agnes Harness source itself.
- Filing requirements vary by region, project type, and owner; use replaceable JSON rules.
- Script draft findings are for Agent review and polishing; official administrative acceptance follows competent authorities.
- **Do not commit**: model API keys, passwords, `.env`, real project archives, ID numbers / phone numbers, or other personal data. Demo data in this repo is synthetic.

---

## Attribution

- **Runtime**: [Agnes Harness](https://github.com/AgnesAI-Labs/agnes-harness) (Apache-2.0)
- **Public reference PDFs / filing catalogs**: copyright remains with the original publishers; URLs and use notes are in `reference/**/SOURCES.txt`. Not required in git by default; fetch with `tools/fetch_*.py`.
- **Synthetic demo PDFs**: layouts follow public blank forms and model texts; content is fictional and free for reproduction experiments.
- **Demo / learning use**: keep third-party attribution and license notices when reusing or redistributing.

## License

For demonstration and learning. Public reference files remain copyright of their publishers; synthetic data may be used freely for reproduction experiments.
