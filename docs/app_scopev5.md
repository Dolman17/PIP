# PIP CRM — App Scope (Updated for Planned Manage Employee Module)

## Purpose
PIP CRM is an internal HR workflow application for managing:
- performance improvement plans (PIPs)
- probation processes
- sickness cases
- employee relations cases
- associated HR administration, drafting, and tracking activity

The app is intended for internal HR/admin users and line managers with role-aware access.

---

## Current live modules

## 1. Authentication
Implemented:
- login
- logout
- Flask-Login user loading
- role-aware route protection via `admin_level`
- superuser-only controls for selected admin workflows

---

## 2. Main dashboard
Implemented:
- dashboard landing page
- total employee count
- open/completed PIP counts
- overdue review counts
- due-soon review logic
- recent activity feed
- draft resume banner support
- JSON stats endpoint for dashboard charts

Current use:
- central operational overview for day-to-day app usage

---

## 3. Employee management
Implemented:
- employee list
- employee detail
- add employee
- edit employee
- quick-add employee
- employee import flow (CSV/XLSX)
- import validation and commit

Employee data currently in scope:
- first name
- last name
- email
- job title
- line manager
- service
- team ID
- start date

Current limitation:
- employee records are still relatively lightweight and do not yet function as a full personnel-file or lifecycle-management module
- leaver handling is not yet implemented as a structured workflow
- employee turnover statistics cannot yet be calculated reliably from employee lifecycle states

---

## 4. PIP module
Implemented:
- PIP list
- PIP detail
- direct create/edit
- employee-select create flow
- multi-step wizard
- draft save / dismiss / resume
- AI advice generation
- AI action suggestion generation
- action plan items
- auto review date logic
- document generation and editing workflow

PIP data in current scope:
- concerns
- concern category
- severity
- frequency
- tags
- meeting notes
- start date
- review date
- capability meeting date/time/venue
- created by
- action items
- AI advice
- document drafts/finals

Document workflow implemented:
- create draft from DOCX template
- convert DOCX to editable HTML
- save edited HTML back to DOCX
- finalise version
- download generated document

---

## 5. Probation module
Implemented:
- probation create flow
- probation dashboard
- probation detail/edit
- add support plans
- add reviews
- status updates
- probation employee list
- probation draft save/resume/dismiss flow

Scope note:
- probation is part of the current baseline, not a future placeholder

---

## 6. Sickness module
Implemented:
- sickness dashboard
- sickness list
- create sickness case
- employee-specific sickness creation
- sickness case detail
- add sickness meeting
- update sickness status
- rolling trigger calculation logic
- dashboard-driven recommended action output

Current sickness analytics in scope:
- open cases
- recently closed cases
- long-term cases
- upcoming meetings
- potential trigger employees
- severity/action guidance

---

## 7. Employee Relations module
Implemented:
- Employee Relations module tile
- ER dashboard
- ER case list
- ER case detail
- ER create case
- ER edit case
- ER meetings
- ER attachments with upload/download
- ER documents with draft/edit/finalise/download flow
- ER timeline/activity history
- superuser-only access restriction
- ER policy text save/link workflow
- ER structured AI advice generation
- ER AI advice storage and structured case-page rendering
- ER AI-aware document draft prefills
- ER exact document-type-specific draft prefills

### ER case types currently in scope
- Disciplinary
- Grievance
- Investigation

### ER workflow scope currently implemented
- create and manage a single ER case record
- store appeal information on the same case
- capture case dates, categories, assigned roles, sanctions/outcomes, and confidential notes
- record meetings
- upload supporting files
- create and finalise case-linked documents
- log major events to case history
- save active policy text against a case
- generate structured ER AI advice on demand
- reuse structured ER AI content inside ER document drafts

### ER meetings currently in scope
Structured meeting support exists for:
- Investigation Meeting
- Disciplinary Hearing
- Grievance Meeting
- Appeal Hearing
- Suspension Review

Stored meeting data includes:
- type
- datetime
- location
- attendees
- notes
- adjournment notes
- outcome summary

### ER attachments currently in scope
Case-level upload support exists for categories including:
- Evidence
- Witness Statement
- Investigation Report
- Meeting Notes
- Letter
- Appeal
- Policy
- Other

### ER policy text currently in scope
Implemented:
- paste policy text directly against an ER case
- optionally link policy text to an uploaded attachment
- mark the newest policy entry as active
- retain older policy entries as archived history
- display active policy text on the ER case page

Stored policy text data includes:
- title
- linked source filename
- linked attachment reference
- raw text
- cleaned text
- active/archived state
- created/updated metadata

### ER AI advice currently in scope
Implemented:
- on-demand generation only
- policy-aware prompt context
- structured JSON response handling
- persistence to dedicated ER AI advice table
- mirrored timeline entry for readable case history
- structured rendering on the ER case page

Structured ER AI advice sections currently stored:
- overall risk view
- immediate next steps
- investigation questions
- hearing questions
- outcome / sanction guidance
- fairness / process checks
- suggested wording
- missing information
- raw response
- model name

### ER documents currently in scope
ER document workflow now supports:
- create draft
- edit draft content
- finalise to DOCX
- download final DOCX
- versioning at the ER document record level
- timeline logging of draft/final events
- AI-prefilled draft creation when ER AI advice exists
- exact document-type-specific AI-prefill logic

Current ER document types in scope:
- Investigation Invite
- Suspension Confirmation
- Disciplinary Hearing Invite
- Disciplinary Outcome Letter
- Warning Letter
- Dismissal Letter
- Grievance Meeting Invite
- Grievance Outcome Letter
- Appeal Invite
- Appeal Outcome Letter
- Witness Statement Template
- Meeting Notes Template

### ER document draft prefills currently in scope
When AI advice exists, the generated HTML draft can now prefill from structured advice, varying by exact document type.

Examples:
- Investigation Invite → investigation questions, next steps, fairness checks
- Disciplinary Hearing Invite → hearing questions, sanction guidance, fairness checks
- Disciplinary Outcome Letter → suggested wording, sanction guidance, missing information
- Grievance Outcome Letter → suggested wording, fairness/process checks, next steps
- Witness Statement Template → investigation-question-led prompts
- Meeting Notes Template → structured prompts for questioning and process checks

### ER access model currently in scope
- superuser only

---

## 8. Admin module
Implemented:
- admin dashboard
- create/edit/delete users
- manage users
- database backup
- export data

Scope note:
- admin tooling remains part of the live application baseline

---

## 9. Taxonomy support
Implemented:
- concern category data
- predefined tags
- tag suggestion endpoint
- action template support
- curated template/tag helper logic

Used mainly by:
- PIP workflow
- AI suggestion enrichment

---

## 10. Timeline/activity logging
Implemented:
- timeline events created in key workflows
- recent activity feed on dashboard
- document workflow events
- PIP-related event logging
- Employee Relations timeline support
- ER meeting/upload/document events logged to ER case history
- ER AI advice generation mirrored into ER timeline
- ER policy text additions/links logged to ER timeline

Current state:
- operational timeline support exists
- not yet a full enterprise-grade audit log

---

## 11. Technical capabilities in current scope
Implemented:
- Flask app with blueprint routing
- service-based shared logic
- SQLAlchemy models
- Flask-Migrate
- CSRF protection
- OpenAI integration
- DOCX/HTML conversion helpers
- SQLite local database
- WSGI deployment entry point
- compatibility layer for legacy endpoints
- module-aware navigation and session switching
- structured ER AI response parsing and persistence

---

## Current access model
Broadly supported:
- superuser / high admin
- lower admin / line-manager style restricted views in selected flows

Observed current behaviour:
- lower admin users are filtered to team-relevant data in selected flows
- superuser-only restrictions exist for admin/import actions
- Employee Relations is currently restricted to superusers

---

## Current main entities
Observed core entities:
- `User`
- `Employee`
- `PIPRecord`
- `PIPActionItem`
- `TimelineEvent`
- `DraftPIP`
- `DocumentFile`
- `ImportJob`
- `SicknessCase`
- `SicknessMeeting`
- `ProbationRecord`
- `ProbationReview`
- `ProbationPlan`
- `DraftProbation`
- `EmployeeRelationsCase`
- `EmployeeRelationsTimelineEvent`
- `EmployeeRelationsMeeting`
- `EmployeeRelationsAttachment`
- `EmployeeRelationsPolicyText`
- `EmployeeRelationsAIAdvice`
- `EmployeeRelationsDocument`

---

## Explicitly in current scope
These are part of the app as it exists now:
- internal HR workflow support
- employee administration
- PIP management
- probation management
- sickness tracking
- Employee Relations case management
- manager support workflows
- draft/resume workflows
- AI-assisted advice/suggestions in the PIP module
- structured AI-assisted advice in the Employee Relations module
- document generation
- activity logging
- admin utilities

---

## Planned next module: Manage Employee
Next intended build phase:
- introduce a dedicated **Manage Employee** module to extend the current lightweight employee area into a fuller personnel-file and employee-lifecycle module

Planned scope for Manage Employee:
- central employee record hub beyond the current basic add/edit screens
- core personnel-file style fields and administrative tracking
- employment-status management
- structured **make employee a leaver** workflow
- capture of leaver date and key leaving metadata
- separation of active employees vs leavers
- future-ready data needed for turnover and attrition reporting

Planned employee lifecycle data direction:
- employee status (for example active / leaver)
- leaving date
- leaving reason / category
- optional notes tied to employee lifecycle changes
- retained historical employee record rather than delete-based handling

Expected reporting outcomes after this module:
- employee turnover stats in future dashboards
- leaver trend reporting
- better historic headcount continuity
- stronger downstream analytics for recruitment and retention

Scope note:
- this Manage Employee module is **planned next work**, not part of the current live baseline yet
- current employee administration remains limited to create/edit/import/detail workflows

---

## Out of scope / not yet complete
These are not part of the current stable baseline:

### Structural / engineering
- full app-factory conversion
- complete removal of endpoint alias layer
- fully modular template-folder architecture across the whole app
- advanced test suite coverage across the whole app
- API-first architecture

### Product / permissions
- deeply granular permissions model beyond the current approach
- external client portal
- public API
- full settings/config UI
- full audit-grade change history for every entity
- advanced analytics beyond current dashboards
- automatic policy PDF/DOCX extraction into ER policy text
- user choice between plain ER draft vs AI-prefilled ER draft
- exact letter-template-by-doc-type composer beyond current HTML draft prefills

### Repo / process
- polished production repo structure across every local artifact pattern
- fully cleaned historical backup/code clutter unless manually completed

---

## Current next planned phase
Next intended build phase:
- build a new **Manage Employee** module focused on personnel-file style employee administration and lifecycle handling

Planned next scope:
- expand employee management beyond the current lightweight CRUD/import feature set
- add a structured **make employee a leaver** workflow
- capture leaving date and related lifecycle metadata
- preserve leavers historically rather than treating records as only active staff
- lay the data foundation for future turnover, attrition, and headcount-change reporting

Follow-on phases after Manage Employee:
- Employee Relations document workflow refinement
- optional ER plain-vs-AI draft choice and further document composition improvements

---

## Updated baseline summary
At the current baseline:
- `app.py` remains a smaller shell
- blueprints own feature routes
- services own shared helper logic
- Employee Relations is now a live module, not a placeholder
- ER meetings, attachments, policy text, AI advice, and documents are all implemented
- ER document drafts can now reuse structured AI advice
- ER document drafts now vary by exact ER document type
- the next logical development phase is a new Manage Employee module for personnel-file administration, leaver handling, and future turnover analytics
- Employee Relations document workflow refinement now becomes the follow-on phase after Manage Employee

This is the current app scope baseline for the next chat window.
