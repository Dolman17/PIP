# PIP CRM — Architecture (Post Phase 1E)

## Status
This document reflects the current stable application structure after Phase 1E close-out.

The app is now in a **hybrid blueprint + service architecture**:
- `app.py` is the bootstrap and compatibility shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- templates remain in the root `templates/` folder
- SQLAlchemy models remain available via `models.py`

This is **not yet a full app-factory architecture**. It is a controlled intermediate state designed to reduce risk while improving maintainability.

---

## High-level structure

```text
app.py
├─ Flask app bootstrap
├─ config / extensions init
├─ blueprint registration
├─ CSRF exemptions
├─ context processors
├─ active module switching
├─ legacy endpoint alias shim
└─ app-level dashboard routes

pip_app/
├─ blueprints/
│  ├─ auth.py
│  ├─ main.py
│  ├─ taxonomy.py
│  ├─ admin.py
│  ├─ employees.py
│  ├─ pip.py
│  ├─ probation.py
│  └─ sickness.py
├─ services/
│  ├─ ai_utils.py
│  ├─ auth_utils.py
│  ├─ dashboard_utils.py
│  ├─ document_utils.py
│  ├─ import_utils.py
│  ├─ sickness_metrics.py
│  ├─ storage_utils.py
│  ├─ taxonomy.py
│  ├─ time_utils.py
│  └─ timeline_utils.py
└─ __init__.py

models.py
forms.py
templates/
uploads/
migrations/
```

---

## Runtime architecture

## 1. App shell (`app.py`)
`app.py` now owns only the cross-cutting pieces that are still intentionally central:

- Flask app creation
- config values (`SECRET_KEY`, DB URI, upload folder, CSRF config)
- extension setup (`db`, `migrate`, `login_manager`, `csrf`)
- blueprint registration
- CSRF exemptions for selected AJAX endpoints
- context processors
- active module routing state (`PIP`, `Probation`, `Sickness`)
- legacy endpoint compatibility mapping
- dashboard routes
- `/ping`

### What `app.py` no longer owns
These concerns have been moved out into services:
- OpenAI client setup
- document merge / render helpers
- draft document file storage helpers
- employee import parsing helpers
- timezone/date helper utilities
- sickness trigger calculations
- timeline helper
- dashboard aggregation helpers
- auth guard helper

---

## 2. Blueprints
Routes are now grouped by feature area.

### `auth_bp`
Handles:
- login
- logout

### `main_bp`
Handles:
- landing / module-selection style entry point

### `taxonomy_bp`
Handles:
- taxonomy categories
- predefined tags
- tag suggestions
- action template lookups

### `admin_bp`
Handles:
- admin dashboard
- user management
- database backup
- export

### `employees_bp`
Handles:
- employee detail
- employee list
- add/edit employee
- quick-add employee
- employee import flow

### `pip_bp`
Handles:
- PIP CRUD views
- PIP wizard
- AI advice
- AI action suggestions
- draft save / dismiss / resume
- document drafting / editing / finalising / download

### `probation_bp`
Handles:
- probation wizard and draft flow
- probation detail / edit
- review and plan routes
- probation dashboard
- employee selection for probation

### `sickness_bp`
Handles:
- sickness dashboard
- sickness list
- create/view/update sickness cases
- sickness meetings

---

## 3. Services layer
The service layer contains reusable helper logic extracted from the old single-file app.

### `ai_utils.py`
- exposes OpenAI client

### `auth_utils.py`
- `superuser_required`

### `dashboard_utils.py`
- scoped open-PIP query
- grouped dashboard counts

### `document_utils.py`
- placeholder mapping
- DOCX merge and conditional stripping
- HTML sanitising
- DOCX ↔ HTML conversion
- document path helpers

### `import_utils.py`
- CSV/XLSX parsing
- header normalisation
- date parsing helpers
- employee import constants

### `sickness_metrics.py`
- rolling sickness trigger calculations
- Bradford-style scoring helpers

### `storage_utils.py`
- document version resolution
- file write helper

### `taxonomy.py`
- curated concern tags
- action templates
- taxonomy merge logic

### `time_utils.py`
- London timezone helpers
- `today_local()`
- `now_local()`
- review date auto-calculation

### `timeline_utils.py`
- timeline event logging helper

---

## Request/flow model

## PIP flow
1. Employee chosen
2. PIP created or resumed through wizard
3. Concern data, dates, meeting data, and actions captured
4. Draft may be saved/resumed
5. PIP record created
6. AI support/advice can be generated
7. Documents can be drafted, edited, finalised, and downloaded

## Probation flow
1. Employee chosen
2. Probation record created or resumed from draft
3. Reviews and support plans added
4. Status managed from probation views/dashboard

## Sickness flow
1. Sickness case created for employee
2. Meetings can be logged
3. Dashboard calculates trigger risks and recommended actions
4. Status managed from case/detail views

---

## Compatibility layer
A legacy endpoint alias map remains in `app.py` so older templates and route references continue working after blueprint moves.

This is **intentional and required** in the current architecture.

It should not be removed until:
- templates are fully updated to blueprint-qualified endpoints
- all compatibility aliases are verified unused
- a dedicated cleanup phase is approved

---

## Current architectural strengths

- Much smaller and safer `app.py`
- Shared logic is no longer scattered through route files
- PIP feature area is materially cleaner than the old single-file version
- Employee import and sickness logic are now reusable
- App behaviour has remained stable during refactor
- Route names and URLs were preserved during the migration

---

## Known architectural debt still present

### 1. Hybrid bootstrap remains
The app still uses a single live `app.py` entry point rather than a full factory pattern.

### 2. Duplicate service modules exist
Current duplicates / overlaps:
- `sickness_metrics.py` vs `sickness_utils.py`
- `timeline_utils.py` vs `timeline.py`

Only one canonical module should exist for each concern.

### 3. Root-level `models.py` remains central
Blueprints and services still import from `models.py`. This is fine for now, but it is still part of the old structure.

### 4. Templates remain flat
Templates are still largely in a single `templates/` directory rather than grouped by feature.

### 5. Repo hygiene is still rough
The repo snapshot still contains environment artifacts and historical files that should not live in the main repo.

---

## Recommended next architecture steps

### Short tidy phase
- remove duplicate service modules
- remove unused imports
- clean old files and environment artifacts from repo
- verify all templates use stable endpoints

### Next structural phase
Only if explicitly approved:
- move to full app-factory pattern
- centralise extensions in `pip_app/extensions.py`
- define clearer import boundaries
- optionally split templates by module

---

## Current entry points and deployment shape

### Local development
- run via `py app.py`

### WSGI
- `wsgi.py` exists as deployment entry point

### Database
- SQLite local file: `pip_crm.db`

### Migrations
- Flask-Migrate / Alembic configured

---

## Architecture decision summary

**Current decision:** keep a stable hybrid architecture.

Why:
- lower risk than forcing a full factory rewrite
- preserves working routes and templates
- supports continued feature delivery
- removes the worst `app.py` sprawl without destabilising the app

This is the correct architecture baseline for the app at the end of Phase 1E.
