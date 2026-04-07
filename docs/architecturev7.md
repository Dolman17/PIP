# PIP CRM — Architecture (Updated for Live Workspace Home + Manage Employee Reporting + API-Ready Next Phase)

## Status
This document reflects the current stable architecture after:
- Phase 1D blueprint extraction
- Phase 1E service extraction and `app.py` cleanup
- Employee Relations Phase ER-1 through ER-4.2
- Manage Employee lifecycle module implementation
- first Manage Employee reporting view going live
- workspace home / module selection upgrade to a data-driven operational home
- admin blueprint redirect cleanup for user management

The app now runs in a **stable hybrid blueprint + service architecture**:
- `app.py` is the bootstrap, compatibility, and dashboard shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- SQLAlchemy models are defined in `pip_app/models.py`
- `models.py` remains a compatibility re-export layer
- templates remain primarily in `templates/`, with grouped feature folders in active use

This is intentionally **not yet a full app-factory refactor**.

The next planned expansion is now:

# Open API readiness

This means the architecture should be prepared for versioned API endpoints while preserving all existing server-rendered UI behaviour.

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
│  ├─ manage_employee.py
│  ├─ pip.py
│  ├─ probation.py
│  ├─ sickness.py
│  └─ employee_relations.py
├─ services/
│  ├─ ai_utils.py
│  ├─ auth_utils.py
│  ├─ dashboard_utils.py
│  ├─ document_utils.py
│  ├─ employee_lifecycle_service.py
│  ├─ employee_relations_constants.py
│  ├─ import_utils.py
│  ├─ sickness_metrics.py
│  ├─ storage_utils.py
│  ├─ taxonomy.py
│  ├─ time_utils.py
│  └─ timeline_utils.py
├─ models.py
└─ __init__.py

models.py
forms.py
templates/
├─ employee_relations/
├─ manage_employee/
├─ ...
uploads/
migrations/
wsgi.py
```

---

## Current architectural pattern

## 1. Application shell (`app.py`)
`app.py` remains intentionally small and owns only central concerns:
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

### `app.py` now additionally owns/wires
- registration of `employee_relations_bp`
- registration of `manage_employee_bp`
- active-module switching for `/employee-relations/*`
- active-module switching for `/manage-employees/*`
- legacy endpoint aliases where needed for template compatibility

### `app.py` still does not own
The following responsibilities remain outside the app shell:
- OpenAI client setup
- timezone/date helpers
- review date auto-calculation
- dashboard aggregation helpers
- document merge/render/conversion helpers
- timeline logging helper
- import parsing helpers
- file storage/version helpers
- employee lifecycle state transition helpers
- superuser decorator helper
- sickness trigger calculations
- Employee Relations route logic

---

## 2. Blueprint layer
Routes are grouped by feature area.

### `auth_bp`
Authentication:
- login
- logout

### `main_bp`
App entry / workspace home.

Now live inside `main_bp`:
- fullscreen workspace home render
- live KPI aggregation for module cards
- recent activity aggregation for homepage panels
- role-aware homepage data (including ER counts for superusers)

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

Recent stability fix:
- blueprint-safe redirects now point to `admin.manage_users`

### `employees_bp`
Employee workflows:
- employee list/detail
- add/edit employee
- quick-add employee
- employee import validate/commit flow

### `manage_employee_bp`
Employee lifecycle / personnel-file workflows:
- manage employee list
- active / leaver / all filtering
- scoped employee search
- employee lifecycle detail view
- structured mark-as-leaver flow
- reactivate flow
- first lifecycle reporting view

Reporting route now live:
- `/manage-employees/reporting`

Current reporting architecture in this blueprint:
- scoped employee base query
- service filtering
- date filtering
- turnover calculation
- monthly aggregation
- reason aggregation
- service aggregation

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

### `employee_relations_bp`
Employee Relations workflows:
- ER dashboard
- ER case list/detail/create/edit
- ER meetings add flow
- ER attachment upload/download flow
- ER policy text add/link flow
- ER AI advice generation flow
- ER document create/edit/finalise/download flow
- ER timeline logging through ER-specific timeline model
- ER AI-aware document draft composition

---

## 3. Services layer
The services folder remains the canonical shared-helper layer.

### Key current service modules
- `ai_utils.py`
- `auth_utils.py`
- `dashboard_utils.py`
- `document_utils.py`
- `employee_lifecycle_service.py`
- `employee_relations_constants.py`
- `import_utils.py`
- `sickness_metrics.py`
- `storage_utils.py`
- `time_utils.py`
- `timeline_utils.py`

### Notable live architectural role
`employee_lifecycle_service.py` is now the canonical location for employee lifecycle transitions:
- status label helper
- mark employee as leaver
- reactivate employee
- validation and cleaning rules
- preservation of historic leave metadata on reactivation

---

## 4. Data model layer
Primary models currently in architectural scope include:
- `User`
- `Employee`
- `PIPRecord`
- `PIPActionItem`
- `TimelineEvent`
- `ProbationRecord`
- `ProbationReview`
- `ProbationPlan`
- `DraftPIP`
- `DraftProbation`
- `ImportJob`
- `DocumentFile`
- `SicknessCase`
- `SicknessMeeting`
- `EmployeeRelationsCase`
- `EmployeeRelationsTimelineEvent`
- `EmployeeRelationsMeeting`
- `EmployeeRelationsAttachment`
- `EmployeeRelationsPolicyText`
- `EmployeeRelationsAIAdvice`
- `EmployeeRelationsDocument`

### Employee model architecture now includes lifecycle reporting fields
- `employment_status`
- `is_leaver`
- `leaving_date`
- `leaving_reason_category`
- `leaving_reason_detail`
- `leaving_notes`
- `marked_as_leaver_at`
- `marked_as_leaver_by`
- `reactivated_at`
- `reactivated_by`

These fields now support both UI lifecycle workflows and the first reporting view.

---

## 5. Template architecture
Templates continue to use server-rendered Jinja.

### Current grouped template areas in active use
- `templates/manage_employee/`
- `templates/employee_relations/`
- probation-related templates
- sickness-related templates
- admin templates
- global shell templates

### Current shell/layout state
`base.html` now provides:
- sidebar app shell for logged-in users
- fullscreen-compatible layout mode
- active module display
- grouped sidebar navigation
- manage employee nav entries across modules
- visible reporting pill on manage employee nav entry
- flash messages with auto-dismiss
- CSRF meta token support
- global `fetchWithCsrf` helper

### Workspace home template state
The former simple module picker has become a production-style workspace home:
- hero section
- KPI cards
- module cards
- quick access links
- recent activity panels
- role-aware visibility

---

## 6. Current routing conventions
The system is increasingly blueprint-namespaced.

Examples:
- `main.home`
- `admin.manage_users`
- `manage_employee.index`
- `manage_employee.reporting`
- `employee_relations.dashboard`

### Architectural rule now reinforced
When adding or editing routes in blueprints:
- always use blueprint-qualified endpoint names in `url_for(...)`
- do not assume bare endpoint names will resolve correctly

---

## 7. Current stability notes
Known stable after recent fixes:
- manage employee lifecycle flows
- manage employee reporting route
- workspace home render
- admin user create/edit/delete redirect flow
- models cleanup after accidental paste contamination

Key lesson reinforced:
- full pasteovers must be applied cleanly to the correct file
- accidental cross-file paste contamination can break syntax across the app

---

## 8. Next architecture phase — Open API readiness
The next phase should be additive and low-risk.

### Recommended architecture shape
Add a new versioned API layer without disturbing current UI blueprints.

Recommended future structure:

```text
pip_app/
├─ api/
│  ├─ __init__.py
│  ├─ auth.py
│  ├─ serializers.py
│  ├─ responses.py
│  └─ v1/
│     ├─ __init__.py
│     ├─ employees.py
│     ├─ reporting.py
│     ├─ pips.py
│     ├─ probations.py
│     ├─ sickness.py
│     └─ employee_relations.py
```

### Recommended first architectural goals
- create `/api/v1/` blueprint registration
- define common JSON response contract
- define serializer layer separate from templates
- add token or API key authentication for API routes
- begin with read-only endpoints only
- keep permissions aligned to existing role model
- preserve existing UI blueprints intact

### Recommended first API domains
1. employees
2. manage employee reporting summaries
3. PIP records (read-only)
4. probation records (read-only)
5. sickness cases (read-only)
6. Employee Relations cases (restricted)

### Architectural rule for next phase
- API endpoints should not reuse HTML template responses
- serializers/responses should be explicit and structured
- the UI and API layers should remain separate even if they share service helpers

---

## 9. Out of scope for immediate next phase
Not part of the first API-readiness step unless explicitly chosen:
- full public API launch
- write-capable external integrations
- OAuth provider integration
- webhook/event bus architecture
- complete app-factory rewrite
- frontend rewrite into SPA

---

## 10. Current priority summary
1. Keep existing blueprint and route contracts stable
2. Preserve working UI behaviour
3. Add API-readiness as a parallel architectural layer
4. Start with versioned read-only endpoints
5. Design the API foundation so OpenAPI documentation can be added cleanly later
