# PIP CRM — App Scope (Updated for Live Workspace Home + Manage Employee Reporting + API-Ready Next Phase)

## Purpose
PIP CRM is an internal HR workflow application for managing:
- performance improvement plans (PIPs)
- probation processes
- sickness cases
- employee relations cases
- employee lifecycle administration
- HR reporting and operational dashboards
- associated drafting, document generation, and tracking activity

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

## 2. Workspace home / module selection
Implemented:
- fullscreen workspace home page
- production-style module landing page
- live KPI cards for core module counts
- quick access links
- recent activity panels
- role-aware module visibility
- no-sidebar operational shell for entry page

Current live homepage metrics:
- active employees
- leavers
- open PIPs
- active probations
- open sickness cases
- open ER cases (superuser only)
- missing employee email count

Current live homepage recent activity panels:
- recent leavers
- recent PIP activity
- recent probation activity
- recent sickness activity
- recent ER activity (superuser only)

Current outcome:
- the old module chooser is now a real operational workspace home

---

## 3. Main dashboard
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
- central operational overview for day-to-day PIP module usage

---

## 4. Employee management
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

## 5. Manage Employee module
Implemented:
- dedicated manage employee list
- employee lifecycle detail view
- active / leaver / all employee filtering
- lifecycle-aware employee search
- structured mark-as-leaver workflow
- reactivate workflow
- linked-record summary display
- first lifecycle reporting view

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

Current reporting view now live:
- total employees
- active employees
- leavers
- leavers by month
- leavers by reason
- leavers by service
- active vs leavers by service
- start/end date filters
- service filter
- period turnover calculation
- opening / closing / average headcount calculation

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
- the application now has a usable employee lifecycle foundation plus the first real turnover-style reporting layer

---

## 6. PIP module
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

## 7. Probation module
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

## 8. Sickness module
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

## 9. Employee Relations module
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

---

## 10. Admin tools
Implemented:
- admin dashboard
- user list
- create user
- edit user
- delete user
- export ZIP data bundle
- database backup download

Recent fix now in scope:
- blueprint-safe admin redirects using `admin.manage_users`

---

## Current technical state
The system is now live with:
- multi-blueprint structure
- service extraction for shared logic
- lifecycle-aware employee administration
- first employee reporting view
- production-style workspace home
- admin user management working with blueprint-safe routing

---

## Next phase now in scope
The next development phase is:

# Open API readiness

This means preparing the app for controlled API exposure without changing the existing UI behaviour.

Planned additive scope for the next phase:
- define API design principles and authentication approach
- identify read-only endpoints to expose first
- create a versioned `/api/` structure
- standardise JSON response shape
- add API-safe serializers for key models
- add token or key-based authentication for API routes
- add permission rules for API consumers
- prepare core modules for future external/mobile/client access
- document endpoints clearly for future OpenAPI generation

Recommended first API-ready domains:
- employees
- manage employee reporting summaries
- PIPs (read-only first)
- probation records (read-only first)
- sickness cases (read-only first)
- ER cases (superuser/admin restricted)

Recommended rule:
- start with read-only API endpoints before any write endpoints

---

## Out of scope for this immediate next phase
Not part of the first API-readiness step unless explicitly chosen:
- full public API exposure
- third-party OAuth
- external webhooks
- write-capable public integrations
- app-factory rewrite
- full SPA frontend replacement

---

## Current priority summary
1. Preserve current stable UI routes and workflows
2. Keep all existing blueprint names and route names intact
3. Add API-readiness additively
4. Start with versioned read-only endpoints
5. Generate an internal API foundation that can later support OpenAPI docs cleanly
