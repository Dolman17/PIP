# PIP CRM — Architecture (Finalised After Phase 1E Cleanup)

## Status
This document reflects the current stable architecture after:
- Phase 1D blueprint extraction
- Phase 1E service extraction and `app.py` cleanup
- short cleanup pass to remove duplicate helper modules and repo noise

The app now runs in a **stable hybrid blueprint + service architecture**:
- `app.py` is the bootstrap, compatibility, and dashboard shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- models remain centralised in `models.py`
- templates remain primarily in the root `templates/` directory

This is intentionally **not yet a full app-factory refactor**.

---

## High-level structure

```text
app.py
├─ Flask bootstrap and config
├─ extension initialisation
├─ blueprint registration
├─ CSRF exemptions
├─ context processors
├─ active module switching
├─ legacy endpoint compatibility map
├─ dashboard routes
└─ health route

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
wsgi.py
```

---

## Current architectural pattern

## 1. Application shell (`app.py`)
`app.py` is now intentionally small and owns only central concerns:

- Flask app creation
- environment/config loading
- DB / migration / login / CSRF initialisation
- blueprint registration
- context processors
- CSRF exemptions for selected AJAX routes
- active module session switching
- legacy endpoint alias compatibility
- app-level dashboard routes
- `/ping`

### `app.py` no longer owns
The following responsibilities were moved into services:
- OpenAI client setup
- timezone/date helpers
- review date auto-calculation
- dashboard aggregation helpers
- document merge/render/conversion helpers
- timeline logging helper
- import parsing helpers
- file storage/version helpers
- superuser decorator helper
- sickness trigger calculations

---

## 2. Blueprint layer
Routes are grouped by feature area.

### `auth_bp`
Authentication:
- login
- logout

### `main_bp`
App entry / module selection style pages.

### `taxonomy_bp`
Taxonomy support APIs:
- categories
- predefined tags
- suggestions
- action templates

### `admin_bp`
Admin tools:
- admin dashboard
- user management
- backup
- export

### `employees_bp`
Employee workflows:
- employee list/detail
- add/edit employee
- quick-add employee
- employee import validate/commit flow

### `pip_bp`
PIP workflows:
- PIP list/detail/edit/create
- PIP wizard
- AI advice
- AI action suggestion endpoint
- draft save/dismiss/resume
- PIP document create/edit/finalise/download

### `probation_bp`
Probation workflows:
- create/edit/detail
- probation dashboard
- reviews and plans
- draft flow

### `sickness_bp`
Sickness workflows:
- sickness dashboard
- list/detail/create/update
- meetings
- trigger monitoring

---

## 3. Services layer
The services folder is now the canonical shared-helper layer.

## Canonical service modules
After cleanup, the canonical service files are:

### `ai_utils.py`
- exposes OpenAI client

### `auth_utils.py`
- `superuser_required`

### `dashboard_utils.py`
- scoped open PIP query
- grouped count helpers

### `document_utils.py`
- placeholder mapping
- DOCX merge helpers
- conditional content stripping
- DOCX ↔ HTML conversion
- sanitisation
- document path helpers

### `import_utils.py`
- CSV/XLSX readers
- date parsing
- header normalisation
- employee import constants

### `sickness_metrics.py`
- sickness trigger scoring logic
- rolling absence calculations
- Bradford-style helper logic

### `storage_utils.py`
- document version lookup
- file save helper

### `taxonomy.py`
- curated taxonomy/tag/action support

### `time_utils.py`
- London timezone helpers
- `now_utc`
- `now_local`
- `today_local`
- `auto_review_date`

### `timeline_utils.py`
- timeline event logging helper

### Cleanup completed
Duplicate modules were removed during close-out:
- `sickness_utils.py` removed
- `timeline.py` removed

---

## Data / dependency boundaries

### Current dependency pattern
- blueprints import from `models.py`, `forms.py`, and `pip_app/services/*`
- services import from `models.py` where needed
- `app.py` imports blueprints and services
- templates call endpoints through compatibility-aware `url_for`

### Important current rule
Existing route URLs and endpoint names are treated as stable contracts.
The legacy endpoint alias map in `app.py` remains load-bearing and should not be removed casually.

---

## Request/feature flows

## PIP flow
1. Employee selected
2. Wizard or direct creation used
3. Concerns, dates, meeting data, and actions captured
4. Draft may be saved/resumed
5. PIP created
6. AI guidance can be generated
7. Documents can be drafted, edited, finalised, and downloaded

## Probation flow
1. Employee selected
2. Probation record created or resumed
3. Reviews and plans added
4. Status updated from probation views

## Sickness flow
1. Sickness case created
2. Meetings logged
3. Dashboard evaluates absence triggers
4. Status managed through case/detail views

---

## Compatibility layer
A legacy endpoint alias map remains in `app.py`.

Purpose:
- preserve older template references
- avoid route breakage during refactor
- support gradual cleanup rather than forced renaming

This should only be reduced in a dedicated future cleanup phase.

---

## Strengths of the current architecture
- `app.py` is materially smaller and safer
- shared logic is centralised in services
- feature routing is separated by module
- route behaviour was preserved during refactor
- document flow is no longer tied to large helper blocks in `app.py`
- employee import and sickness calculations are reusable

---

## Remaining architectural debt
These are known but non-blocking:

### 1. Hybrid shell remains
The app still starts from a live `app.py` instead of a full factory architecture.

### 2. Central `models.py`
Models are still defined in a single root module.

### 3. Templates are mostly flat
Templates are not yet consistently grouped by feature/module.

### 4. Compatibility aliases remain
Useful now, but still technical debt for a later cleanup phase.

### 5. Repo hygiene should stay enforced
Environment folders, DB files, backup copies, and local artifacts should remain excluded from source control.

---

## Recommended next architectural direction
Do not do another big refactor immediately.

Recommended order:
1. feature development
2. small incremental cleanup only when needed
3. full factory/extension split only if explicitly approved later

This is the correct architecture baseline at the end of Phase 1E cleanup.
