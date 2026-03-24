# PIP CRM — App Scope (Updated for Manage Employee Lifecycle + First Reporting View)

## Purpose
PIP CRM is an internal HR workflow application for managing:
- performance improvement plans (PIPs)
- probation processes
- sickness cases
- employee relations cases
- employee lifecycle administration
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

## 4. Manage Employee module
Implemented:
- dedicated manage employee list
- employee lifecycle detail view
- active / leaver / all employee filtering
- lifecycle-aware employee search
- structured mark-as-leaver workflow
- reactivate workflow
- linked-record summary display

Lifecycle data currently in scope on `Employee`:
- employment status
- active vs leaver state
- leaving date
- leaving reason category
- leaving reason detail
- leaving notes
- marked as leaver timestamp
- marked as leaver by
- reactivated timestamp
- reactivated by

Lifecycle behaviour now in scope:
- employee records are preserved historically
- leavers remain in the system instead of being deleted
- lifecycle state is used to prevent new downstream process creation where appropriate
- historic leave data is preserved on reactivation for now

Current downstream module protections now in scope:
- no new PIPs for leavers
- no new probation records for leavers
- no new sickness cases for leavers
- no new Employee Relations cases for leavers

Current outcome:
- the application now has the first usable employee lifecycle foundation needed for turnover and attrition reporting

---

## 5. PIP module
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

## 6. Probation module
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

## 7. Sickness module
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

## 8. Employee Relations module
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

---

## 9. Admin module
Implemented:
- admin dashboard
- create/edit/delete users
- manage users
- database backup
- export data

Scope note:
- admin tooling remains part of the live application baseline

---

## 10. Taxonomy support
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

## 11. Timeline/activity logging
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
- Manage Employee lifecycle changes are not yet stored in a dedicated lifecycle audit model

---

## 12. Technical capabilities in current scope
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
- additive employee lifecycle service layer

---

## Current access model
Broadly supported:
- superuser / high admin
- lower admin / line-manager style restricted views in selected flows

Observed current behaviour:
- lower admin users are filtered to team-relevant data in selected flows
- superuser-only restrictions exist for admin/import actions
- Employee Relations is currently restricted to superusers
- Manage Employee views respect scoped employee visibility for lower admin users

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
- employee lifecycle administration
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
- active vs leaver employee state handling

---

## Current next planned phase: first Manage Employee reporting view
Next intended build phase:
- introduce the first reporting view for the Manage Employee module using the lifecycle data already now in place

Planned reporting scope:
- active employee count
- leaver count
- total employee count
- leavers by month
- leavers by reason category
- optionally leavers by service if low risk and easy to add

Purpose of this reporting phase:
- provide the first usable turnover-style insight screen
- prove the lifecycle data model is now operationally useful
- create a foundation for future attrition/headcount reporting without large schema change

Scope note:
- this reporting phase is planned next work
- it should remain additive and low risk
- it should use existing lifecycle fields on `Employee`

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
- dedicated employee lifecycle audit log model
- advanced turnover / attrition analytics suite beyond the first reporting view

### Repo / process
- polished production repo structure across every local artifact pattern
- fully cleaned historical backup/code clutter unless manually completed

---

## Updated baseline summary
At the current baseline:
- `app.py` remains a smaller shell
- blueprints own feature routes
- services own shared helper logic
- Employee Relations is now a live module, not a placeholder
- Manage Employee is now a live module rather than only a planned direction
- employee lifecycle state is now represented directly on `Employee`
- downstream modules now respect leaver state for new-record creation
- the next logical development phase is the first reporting view for Manage Employee using lifecycle data already in place

This is the current app scope baseline for the next chat window.
