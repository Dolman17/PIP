# PIP CRM — Architecture (Updated for Planned Manage Employee Module)

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

The app now runs in a **stable hybrid blueprint + service architecture**:
- `app.py` is the bootstrap, compatibility, and dashboard shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- SQLAlchemy models are defined in `pip_app/models.py`
- `models.py` remains a compatibility re-export layer
- templates remain primarily in `templates/`, with feature grouping now in active use for Employee Relations

This is intentionally **not yet a full app-factory refactor**.

This update also records the next planned functional expansion: a dedicated **Manage Employee** module for employee lifecycle administration, personnel-file style record handling, leaver processing, and future turnover analytics.

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
│  ├─ manage_employee.py   # planned next module
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
│  ├─ manage_employee_utils.py   # likely next service area
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
├─ manage_employee/   # planned next template group
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

### `manage_employee_bp` (planned next)
Planned employee lifecycle / personnel-file workflows:
- richer employee record management beyond basic CRUD
- personnel-file style employee administration
- active vs leaver state handling
- structured make-leaver flow
- lifecycle metadata updates that support future turnover analytics

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

### `manage_employee_utils.py` (planned next)
Likely future responsibilities:
- employee lifecycle status helpers
- make-leaver workflow helpers
- date / reason validation for employee exits
- future turnover/headcount support helpers

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
- `EmployeeRelationsPolicyText`
- `EmployeeRelationsAIAdvice`
- `EmployeeRelationsDocument`

Future model direction for planned Manage Employee work:
- `Employee` is the most likely entity to be expanded first for lifecycle/leaver tracking
- keep any additions additive and migration-safe
- avoid renaming or breaking existing employee routes while introducing lifecycle fields

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

## Planned Manage Employee flow
1. Employee record opened from dedicated manage-employee area
2. Personnel-file style details maintained in one place
3. Employee can be marked as a leaver through a structured workflow
4. Leaving metadata is preserved historically
5. Future reporting layers can use active/leaver states for turnover metrics

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
- ER uses isolated models for timeline, attachments, meetings, policy text, AI advice, and documents
- ER AI output is structured rather than trapped in timeline text only
- ER documents can now reuse structured AI output through deterministic exact-type mapping

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

### 5. ER document composition is still HTML-first
The system currently creates smart HTML drafts using structured AI data, but does not yet have a dedicated exact letter composer per ER document type beyond the current section templates.

### 6. ER policy extraction is manual
Policy text can be pasted/linked, but automatic extraction from uploaded policy files is not yet implemented.

---

## 11. Recommended next architectural direction
Do not perform another major refactor immediately.

Recommended order:
1. continue feature development
2. keep cleanup incremental and localised
3. build the planned **Manage Employee** module next
4. keep it as a dedicated feature area rather than overloading the existing lightweight `employees_bp`
5. use employee lifecycle state and leaver metadata to prepare for future turnover analytics
6. refine ER document workflow after Manage Employee
7. revisit deeper architectural refactor only if explicitly approved later

Architectural recommendation for Manage Employee:
- preserve existing `employees_bp` routes for current employee CRUD/import flows
- add a separate `manage_employee_bp` if the feature grows beyond a small extension
- keep any new employee-lifecycle helpers in a dedicated service layer rather than burying logic inside templates or route handlers
- treat leaver handling as a historical state transition, not a delete/archive shortcut

This is the correct architecture baseline going into the planned Manage Employee module phase.
