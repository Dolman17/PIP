# PIP CRM — App Scope (Updated After Employee Relations Document Phase)

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

### ER documents currently in scope
ER document workflow now supports:
- create draft
- edit draft content
- finalise to DOCX
- download final DOCX
- versioning at the ER document record level
- timeline logging of draft/final events

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
- document generation
- activity logging
- admin utilities

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
- Employee Relations AI advice (planned next)
- Employee Relations policy PDF extraction/review workflow (planned next)

### Repo / process
- polished production repo structure across every local artifact pattern
- fully cleaned historical backup/code clutter unless manually completed

---

## Current next planned phase
Next intended build phase:
- Employee Relations AI advice

Planned ER AI scope:
- on-demand generation only
- policy-aware advice
- output saved to ER case history/timeline
- support for risk flags, next steps, investigation questions, hearing questions, outcome guidance, sanction guidance, fairness checks, and wording suggestions

---

## Updated baseline summary
At the current baseline:
- `app.py` remains a smaller shell
- blueprints own feature routes
- services own shared helper logic
- Employee Relations is now a live module, not a placeholder
- ER meetings, attachments, and documents are all implemented
- the next logical development phase is ER AI

This is the current app scope baseline for the next chat window.
