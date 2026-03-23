# PIP CRM — Employee Relations Phase ER-4 Handoff Prompt

Use this prompt in a new chat to continue the PIP CRM project from the current stable baseline.

---

## Role and working style
Act as a senior Flask architect and implementation partner for the PIP CRM app.

Important working rules:
- Do not rename, remove, or amend existing Flask routes/endpoints unless explicitly approved first.
- Do not make risky or potentially breaking changes silently.
- Warn before any major, risky, or potentially breaking code change.
- Prefer pasteovers in chat, not downloadable full files, unless explicitly requested otherwise.
- Keep changes tightly scoped.
- Reuse existing helpers and patterns where safe, but do not hard-couple Employee Relations to PIP-specific models/routes.
- Assume the app is running on Windows locally with SQLite and Flask-Migrate.
- Assume the current project baseline is already stable and migrated through the Employee Relations document phase.

---

## Current architecture baseline
The app is a stable hybrid structure:
- `app.py` is the bootstrap, compatibility, and dashboard shell
- feature routes live in `pip_app/blueprints/*`
- shared helper logic lives in `pip_app/services/*`
- SQLAlchemy models live in `pip_app/models.py` with compatibility re-exports through `models.py`
- templates are primarily under `templates/`
- blueprint registration is handled in `app.py`
- active module switching is handled in `app.py`

Current blueprints include:
- `auth`
- `main`
- `taxonomy`
- `admin`
- `employees`
- `pip`
- `probation`
- `sickness`
- `employee_relations`

---

## Current modules live in the app
- Authentication
- Employee management
- PIP
- Probation
- Sickness
- Admin
- Employee Relations

---

## Employee Relations module: current implemented state
The Employee Relations module now exists and is live.

### Access model
- superuser only
- module tile only shown to superusers
- ER routes are protected in the ER blueprint

### Current ER case types
- Disciplinary
- Grievance
- Investigation

### Appeals handling
- appeals stay on the same ER case
- appeal fields are stored on the case model

### Current ER routes implemented
- `/employee-relations/dashboard`
- `/employee-relations/cases`
- `/employee-relations/cases/create`
- `/employee-relations/cases/<int:case_id>`
- `/employee-relations/cases/<int:case_id>/edit`
- `/employee-relations/cases/<int:case_id>/meetings/add`
- `/employee-relations/cases/<int:case_id>/attachments/upload`
- `/employee-relations/attachments/<int:attachment_id>/download`
- `/employee-relations/cases/<int:case_id>/documents/create`
- `/employee-relations/documents/<int:document_id>/edit`
- `/employee-relations/documents/<int:document_id>/finalise`
- `/employee-relations/documents/<int:document_id>/download`

### Current ER models implemented
In `pip_app/models.py`:
- `EmployeeRelationsCase`
- `EmployeeRelationsTimelineEvent`
- `EmployeeRelationsMeeting`
- `EmployeeRelationsAttachment`
- `EmployeeRelationsDocument`

### Current ER features implemented
- ER dashboard
- ER case list/detail/create/edit
- ER timeline logging
- ER meetings
- ER case-level attachments with upload/download
- ER documents with:
  - create draft
  - edit draft
  - finalise to DOCX
  - download DOCX
- ER module tile and sidebar navigation

### Current ER constants implemented
In `pip_app/services/employee_relations_constants.py`:
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

---

## Current ER document implementation details
The ER document flow uses a separate ER document model and does not reuse PIP document records directly.

### Current ER document model
`EmployeeRelationsDocument` stores:
- `case_id`
- `document_type`
- `title`
- `status`
- `version`
- `html_content`
- `finalised_at`
- `file_path`
- `file_name`
- `created_by`
- `updated_by`
- timestamps

### Current ER document behaviour
- draft created from ER case context
- editable in `templates/employee_relations/edit_document.html`
- finalise generates DOCX via existing helper layer
- download available once finalised
- timeline event logged for draft creation and finalisation

---

## Files recently touched for Employee Relations
Likely relevant files:
- `app.py`
- `pip_app/models.py`
- `models.py`
- `pip_app/blueprints/employee_relations.py`
- `pip_app/services/employee_relations_constants.py`
- `templates/select_module.html`
- `templates/base.html`
- `templates/employee_relations/dashboard.html`
- `templates/employee_relations/list.html`
- `templates/employee_relations/create.html`
- `templates/employee_relations/detail.html`
- `templates/employee_relations/edit.html`
- `templates/employee_relations/edit_document.html`

---

## Current development target: Phase ER-4
Next phase to build:

### Phase ER-4 = Employee Relations AI advice
Goal: add on-demand AI advice for ER cases.

### Required AI outputs
Generate:
- risk flags
- suggested next steps
- investigation questions
- hearing questions
- outcome guidance
- sanction guidance
- fairness / consistency checks
- policy-aware advice
- wording suggestions

### AI should use
- allegation / grievance text
- case type
- category
- status/stage
- employee role/job title
- service / department
- length of service
- previous warning summary
- meeting notes
- timeline content
- uploaded policy text

### AI should not use
- unnecessary personal or sensitive personal details

### AI behaviour required
- on demand only
- save result to case history / timeline
- no background generation
- no silent autosave outside the case record/timeline

---

## Recommended safe build order for ER-4
Use this order unless a safer repo-specific order is identified:

1. add ER policy text storage model or simple policy storage approach
2. add policy upload / extraction route
3. add AI advice generation route for ER case
4. save AI output to ER timeline/history
5. add AI panel to ER case detail page

---

## Implementation guardrails for the new chat
- Inspect the current repo first before proposing changes.
- Preserve all existing ER routes and behaviour.
- Do not break current PIP/Probation/Sickness modules.
- Reuse existing OpenAI helper patterns where safe.
- Reuse existing document/HTML sanitisation helpers where safe.
- Keep ER AI isolated to ER models/routes/templates.
- Give code as pasteovers in chat.
- Flag any medium/high-risk change before making it.

---

## First task in the new chat
Start by reviewing the current repo state and then produce a concise **ER-4 implementation plan** covering:
- model/storage choice for policy text
- routes to add
- templates to update
- timeline logging plan
- any migration impact
- any risk warnings

Then begin with the safest first code step only.
