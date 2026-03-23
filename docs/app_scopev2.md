# PIP CRM — App Scope (Final Baseline After Phase 1E Cleanup)

## Purpose
PIP CRM is an internal HR workflow application for managing:
- performance improvement plans (PIPs)
- probation processes
- sickness cases
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

## 7. Admin module
Implemented:
- admin dashboard
- create/edit/delete users
- manage users
- database backup
- export data

Scope note:
- admin tooling remains part of the live application baseline

---

## 8. Taxonomy support
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

## 9. Timeline/activity logging
Implemented:
- timeline events created in key workflows
- recent activity feed on dashboard
- document workflow events
- PIP-related event logging

Current state:
- operational timeline support exists
- not yet a full enterprise-grade audit log

---

## 10. Technical capabilities in current scope
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

---

## Current access model
Broadly supported:
- superuser / high admin
- lower admin / line-manager style restricted views

Observed current behaviour:
- lower admin users are filtered to team-relevant data in selected flows
- superuser-only restrictions exist for admin/import actions

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

---

## Explicitly in current scope
These are part of the app as it exists now:
- internal HR workflow support
- employee administration
- PIP management
- probation management
- sickness tracking
- manager support workflows
- draft/resume workflows
- AI-assisted advice/suggestions
- document generation
- activity logging
- admin utilities

---

## Out of scope / not yet complete
These are not part of the finalised current baseline:

### Structural / engineering
- full app-factory conversion
- complete removal of endpoint alias layer
- fully modular template-folder architecture
- advanced test suite coverage across whole app
- API-first architecture

### Product / permissions
- deeply granular permissions model beyond current approach
- external client portal
- public API
- full settings/config UI
- full audit-grade change history for every entity
- advanced analytics beyond current dashboards

### Repo / process
- polished production repo structure across every local artifact pattern
- fully cleaned historical backup/code clutter unless manually completed

---

## Phase 1E close-out summary
At the end of Phase 1E cleanup:
- `app.py` is now a smaller app shell
- blueprints own feature routes
- services own shared helper logic
- duplicate sickness/timeline service files were removed
- app behaviour remained stable through regression testing

This is the current scope baseline for further feature development.
