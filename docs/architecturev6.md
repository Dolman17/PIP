# PIP CRM — Architecture (Updated for Live Manage Employee Module + First Reporting View)

## Status
This document reflects the current stable architecture after:
- Phase 1D blueprint extraction
- Phase 1E service extraction and `app.py` cleanup
- Employee Relations Phase ER-1 foundation
- Employee Relations Phase ER-2 meetings and attachments
- Employee Relations Phase ER-3 documents
- Employee Relations Phase ER-4 structured AI advice
- Employee Relations Phase ER-4.1 AI-aware document draft prefills
- Employee Relations Phase ER-4.2 exact document-type-specific ER draft prefills
- Manage Employee lifecycle module implementation

The app now runs in a **stable hybrid blueprint + service architecture**:
- `app.py` is the bootstrap, compatibility, and dashboard shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- SQLAlchemy models are defined in `pip_app/models.py`
- `models.py` remains a compatibility re-export layer
- templates remain primarily in `templates/`, with feature grouping now in active use for Employee Relations and Manage Employee

This is intentionally **not yet a full app-factory refactor**.

This update also records the next planned functional expansion: the **first reporting view** for the Manage Employee module using the lifecycle data now already present on `Employee`.

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

### `manage_employee_bp`
Employee lifecycle / personnel-file workflows:
- manage employee list
- active / leaver / all filtering
- scoped employee search
- employee lifecycle detail view
- structured mark-as-leaver flow
- reactivate flow

Planned next additive route area:
- first reporting view for lifecycle-based employee reporting

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

## Canonical service modules

### `ai_utils.py`
Now owns both the OpenAI client and ER AI composition helpers.

Current responsibilities include:
- expose OpenAI client
- build ER AI system/user prompts
- request strict JSON output for ER advice
- parse ER AI response into structured fields
- render readable ER AI advice text for timeline mirroring

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

### `employee_lifecycle_service.py`
Current responsibilities:
- employee status label helper
- mark employee as leaver
- reactivate employee
- input cleaning and validation for lifecycle state changes
- preservation of historic leave metadata on reactivation
- structured return payloads from lifecycle actions for future audit/reporting use

This is now the canonical service area for employee lifecycle state transitions.

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
- `EmployeeRelationsPolicyText`
- `EmployeeRelationsAIAdvice`
- `EmployeeRelationsDocument`

### Employee lifecycle model direction now live
`Employee` now carries additive lifecycle fields used by the Manage Employee module:
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

Current architectural approach:
- lifecycle state is stored directly on `Employee`
- no separate lifecycle audit model exists yet
- history is preserved by retaining leave metadata even after reactivation
- downstream modules use these fields to block new record creation for leavers

---

## 6. Manage Employee architecture
The Manage Employee module is now a live feature area.

### Purpose
Create a dedicated employee-lifecycle / personnel-file style layer without overloading the original lightweight `employees_bp` CRUD area.

### Current route strategy
Manage Employee is separated from the legacy employee CRUD routes.

Current routes:
- `/manage-employees`
- `/manage-employees/<employee_id>`
- `/manage-employees/<employee_id>/mark-leaver`
- `/manage-employees/<employee_id>/reactivate`

### Current behaviour
- active / leaver / all filtering
- scoped employee visibility for lower admin users
- lifecycle detail display
- structured mark-as-leaver transition
- structured reactivate transition
- no delete/archive shortcut approach

### Downstream integration now present
Leaver state is respected in:
- PIP creation flows
- Probation creation flows
- Sickness creation flows
- Employee Relations case creation flows

This is a key architectural milestone because employee lifecycle state is now a shared, load-bearing business rule rather than only a display concept.

### Planned next additive capability
A reporting view under `manage_employee_bp` that will:
- aggregate employee lifecycle data from `Employee`
- remain additive and low risk
- avoid new model introduction unless explicitly approved later

---

## 7. Employee Relations architecture
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
- policy text add/link events
- AI advice generation mirror events
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

#### `EmployeeRelationsPolicyText`
Stores policy text records for a case:
- title
- source filename
- linked attachment reference
- raw text
- cleaned text
- active flag
- created/updated metadata

#### `EmployeeRelationsAIAdvice`
Stores structured ER AI guidance:
- linked case
- optional linked policy text
- overall risk view
- immediate next steps
- investigation questions
- hearing questions
- outcome/sanction guidance
- fairness/process checks
- suggested wording
- missing information
- raw response
- model name
- creator/timestamp

#### `EmployeeRelationsDocument`
Stores ER document records:
- document type
- title
- draft/final status
- version
- HTML content
- finalised DOCX path and filename
- created/updated metadata

---

## 8. Request/feature flows

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

## Manage Employee flow
1. Employee opened from dedicated lifecycle list
2. Employee lifecycle data reviewed on detail page
3. Employee can be marked as a leaver through structured transition
4. Leaving metadata is preserved historically
5. Employee can be reactivated if needed
6. Downstream modules respect lifecycle state when creating new records

## Planned first reporting flow
1. Lifecycle reporting view opened from Manage Employee area
2. Employee aggregates calculated directly from `Employee`
3. Headline counts displayed
4. Monthly leaver and reason-category summaries shown
5. Future turnover analytics can build on this view later

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
5. Policy text can be added or linked
6. Structured AI advice can be generated on demand
7. Structured advice is saved to its own table and mirrored into timeline
8. ER documents can be drafted, edited, finalised, and downloaded
9. ER draft creation can reuse latest structured AI advice
10. Exact ER document type now controls which AI sections are injected into the draft
11. Case stays as the single record of truth, including appeal fields on the same case

---

## 9. Compatibility layer
A legacy endpoint alias map remains in `app.py`.

Purpose:
- preserve older template references
- avoid route breakage during refactor
- support gradual cleanup rather than forced renaming
- extend safely as new module routes are added

This should only be reduced in a dedicated future cleanup phase.

---

## 10. Strengths of the current architecture
- `app.py` is materially smaller and safer than the previous monolith
- shared logic is centralised in services
- feature routing is separated by module
- route behaviour was preserved during refactor
- Employee Relations has been added without forcing a full structural rewrite
- Manage Employee has been added as a dedicated lifecycle feature area without breaking the legacy employee CRUD routes
- lifecycle state is now a shared operational rule across multiple modules
- ER uses isolated models for timeline, attachments, meetings, policy text, AI advice, and documents
- ER AI output is structured rather than trapped in timeline text only
- ER documents can now reuse structured AI output through deterministic exact-type mapping

---

## 11. Remaining architectural debt
These are known but non-blocking:

### 1. Hybrid shell remains
The app still starts from a live `app.py` instead of a full factory architecture.

### 2. Model centralisation
Models remain in a single canonical module rather than being split by feature package.

### 3. Templates are mixed
The template layer is only partially grouped by feature. Employee Relations and Manage Employee now use their own subfolders, but the rest of the app is still mixed.

### 4. Compatibility aliases remain
Useful now, but still technical debt for a later cleanup phase.

### 5. ER document composition is still HTML-first
The system currently creates smart HTML drafts using structured AI data, but does not yet have a dedicated exact letter composer per ER document type beyond the current section templates.

### 6. ER policy extraction is manual
Policy text can be pasted/linked, but automatic extraction from uploaded policy files is not yet implemented.

### 7. Lifecycle audit is not yet modelled separately
Manage Employee lifecycle changes are applied cleanly, but there is not yet a dedicated employee-lifecycle audit entity.

---

## 12. Recommended next architectural direction
Do not perform another major refactor immediately.

Recommended order:
1. continue feature development
2. keep cleanup incremental and localised
3. build the first Manage Employee reporting view next
4. keep it inside `manage_employee_bp`
5. use existing lifecycle fields on `Employee` as the reporting source
6. keep the reporting layer additive and low risk
7. revisit dedicated lifecycle audit/history modelling only if explicitly approved later

Architectural recommendation for the next reporting phase:
- add a reporting route under `manage_employee_bp`
- add a dedicated template under `templates/manage_employee/`
- keep data aggregation query-based for now
- avoid creating a new analytics model unless there is a strong later need
- preserve current route behaviour everywhere else

This is the correct architecture baseline going into the first Manage Employee reporting view phase.
