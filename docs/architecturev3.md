# PIP CRM — Architecture (Updated After Employee Relations Document Phase)

## Status
This document reflects the current stable architecture after:
- Phase 1D blueprint extraction
- Phase 1E service extraction and `app.py` cleanup
- Employee Relations Phase ER-1 foundation
- Employee Relations Phase ER-2 meetings and attachments
- Employee Relations Phase ER-3 documents

The app now runs in a **stable hybrid blueprint + service architecture**:
- `app.py` is the bootstrap, compatibility, and dashboard shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- SQLAlchemy models are defined in `pip_app/models.py`
- `models.py` remains a compatibility re-export layer
- templates remain primarily in `templates/`, with feature grouping now in active use for Employee Relations

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
│  ├─ sickness.py
│  └─ employee_relations.py
├─ services/
│  ├─ ai_utils.py
│  ├─ auth_utils.py
│  ├─ dashboard_utils.py
│  ├─ document_utils.py
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
- active-module switching for `/employee-relations/*`
- Employee Relations legacy endpoint aliases where needed for template compatibility

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

### `employee_relations_bp`
Employee Relations workflows:
- ER dashboard
- ER case list/detail/create/edit
- ER meetings add flow
- ER attachment upload/download flow
- ER document create/edit/finalise/download flow
- ER timeline logging through ER-specific timeline model

---

## 3. Services layer
The services folder remains the canonical shared-helper layer.

## Canonical service modules

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

### `employee_relations_constants.py`
Canonical constant definitions for the Employee Relations module:
- case types
- statuses
- stages
- priority levels
- disciplinary categories
- grievance categories
- disciplinary sanctions
- grievance outcomes
- meeting types
- attachment categories
- ER document types

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
Duplicate modules removed in earlier cleanup remain removed:
- `sickness_utils.py`
- `timeline.py`

---

## 4. Data / dependency boundaries

### Current dependency pattern
- blueprints import from `models.py`, `forms.py`, and `pip_app/services/*`
- services import from `models.py` or `pip_app.models` where needed
- `app.py` imports blueprints and services
- templates call endpoints through compatibility-aware `url_for`

### Important current rule
Existing route URLs and endpoint names are treated as stable contracts.
The legacy endpoint alias map in `app.py` remains load-bearing and should not be removed casually.

---

## 5. Model layout
The current canonical model file is:
- `pip_app/models.py`

The root-level compatibility layer remains:
- `models.py`

### Current core entities
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
- `EmployeeRelationsDocument`

---

## 6. Employee Relations architecture
The Employee Relations module is now a live feature area.

### Access model
- superuser only
- module tile and sidebar access controlled in UI
- route protection enforced in the ER blueprint

### ER-specific data model strategy
ER uses its own isolated model set rather than reusing PIP-specific timeline/document tables.
This was chosen deliberately to avoid tight coupling and reduce break risk.

### ER models
#### `EmployeeRelationsCase`
Stores:
- core ER case metadata
- disciplinary-specific fields
- grievance-specific fields
- investigation fields
- appeal fields
- ownership/assigned-role fields
- key milestone dates
- confidential notes

#### `EmployeeRelationsTimelineEvent`
Stores ER-specific timeline history for:
- case creation
- case updates
- stage/status changes
- meeting creation
- attachment upload
- document draft/finalisation events

#### `EmployeeRelationsMeeting`
Stores structured meeting records:
- meeting type
- datetime
- location
- attendees
- notes
- adjournment notes
- outcome summary

#### `EmployeeRelationsAttachment`
Stores case-level file uploads:
- original filename
- stored filename/path
- category
- notes
- uploader/timestamp

#### `EmployeeRelationsDocument`
Stores ER document records:
- document type
- title
- draft/final status
- version
- HTML content
- finalised DOCX path and filename
- created/updated metadata

### ER route/file storage approach
Uploads are stored under Employee Relations-specific directories beneath the existing uploads area.
This reuses the existing filesystem pattern while keeping ER files isolated from PIP document records.

---

## 7. Request/feature flows

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

## Employee Relations flow
1. ER case created
2. Timeline starts immediately
3. Meetings can be added
4. Attachments can be uploaded/downloaded
5. ER documents can be drafted, edited, finalised, and downloaded
6. Case stays as the single record of truth, including appeal fields on the same case

---

## 8. Compatibility layer
A legacy endpoint alias map remains in `app.py`.

Purpose:
- preserve older template references
- avoid route breakage during refactor
- support gradual cleanup rather than forced renaming
- extend safely as new module routes are added

This should only be reduced in a dedicated future cleanup phase.

---

## 9. Strengths of the current architecture
- `app.py` is materially smaller and safer than the previous monolith
- shared logic is centralised in services
- feature routing is separated by module
- route behaviour was preserved during refactor
- Employee Relations has been added without forcing a full structural rewrite
- ER uses isolated models for timeline, attachments, meetings, and documents
- document flow is reusable without tightly binding ER to PIP document tables

---

## 10. Remaining architectural debt
These are known but non-blocking:

### 1. Hybrid shell remains
The app still starts from a live `app.py` instead of a full factory architecture.

### 2. Model centralisation
Models remain in a single canonical module rather than being split by feature package.

### 3. Templates are mixed
The template layer is only partially grouped by feature. Employee Relations now uses its own subfolder, but the rest of the app is still mixed.

### 4. Compatibility aliases remain
Useful now, but still technical debt for a later cleanup phase.

### 5. ER AI not yet implemented
The next planned ER phase is policy-aware AI advice.

---

## 11. Recommended next architectural direction
Do not perform another major refactor immediately.

Recommended order:
1. continue feature development
2. keep cleanup incremental and localised
3. build Employee Relations AI next
4. revisit deeper architectural refactor only if explicitly approved later

This is the correct architecture baseline after the Employee Relations document phase.
