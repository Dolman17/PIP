# PIP CRM — App Scope (Current Baseline)

## Purpose
PIP CRM is an internal HR workflow app for managing:
- performance improvement plans (PIPs)
- probation records
- sickness case tracking
- related HR administration and document generation

The app is aimed at HR/admin users and line managers, with role-aware access controls.

---

## Core modules in scope

## 1. Authentication and access
Implemented:
- login
- logout
- user loader via Flask-Login
- role-aware access using `admin_level`
- superuser-only admin actions

Current behaviour:
- authentication gates the application
- module access is controlled in-route
- AJAX routes with specific workflow needs are selectively CSRF exempted

---

## 2. Dashboard
Implemented:
- main dashboard
- open/completed PIP counts
- overdue review counts
- due-soon logic
- recent activity feed
- dashboard JSON stats endpoint
- draft resume banner support through PIP draft lookup

Scope:
- app-level landing dashboard for day-to-day usage
- role-filtered view for lower admin levels

---

## 3. Employee management
Implemented:
- employee list
- employee detail
- add employee
- edit employee
- quick-add employee
- employee import flow (CSV/XLSX)
- duplicate checks during validation/commit

Data covered:
- name
- email
- job title
- line manager
- service
- team
- start date

Scope notes:
- employee import is currently an admin/superuser workflow
- quick-add supports in-flow creation from other modules

---

## 4. PIP module
Implemented:
- PIP list
- PIP detail
- create PIP
- edit PIP
- employee selection for PIP creation
- multi-step PIP wizard
- draft save / dismiss / resume
- AI advice generation
- AI action suggestion generation
- action plan items
- review date auto-calculation
- document generation workflow

Document workflow implemented:
- create draft document from template
- edit document HTML snapshot
- convert edited HTML back to DOCX
- finalise document
- download final/draft document

PIP data currently in scope:
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
- draft state

---

## 5. Probation module
Implemented:
- probation create wizard
- probation draft save/resume/dismiss
- create probation record
- probation detail view
- edit probation record
- add probation review
- add probation support plan
- update probation status
- probation dashboard
- probation employee list

Scope notes:
- probation is active and user-facing
- draft flow mirrors the broader refactor direction used in PIP

---

## 6. Sickness module
Implemented:
- sickness dashboard
- sickness case list
- create sickness case
- employee-specific sickness creation
- view sickness case
- add sickness meeting
- update sickness status
- sickness trigger calculations on dashboard
- recommended actions based on severity/flags

Current sickness analytics in scope:
- open cases
- closed cases in past 12 months
- long-term cases
- upcoming meetings
- potential trigger employees
- severity filtering
- service filtering

---

## 7. Admin tools
Implemented:
- admin dashboard
- user list
- create user
- edit user
- delete user
- database backup
- data export

Scope notes:
- admin tools are part of the current live baseline
- these remain centrally important for maintenance workflows

---

## 8. Taxonomy / action support
Implemented:
- category API
- predefined tags API
- tag suggestion API
- action template API
- curated taxonomy helper logic
- template-assisted AI suggestion enrichment

Scope notes:
- taxonomy is a support module used mainly by the PIP experience

---

## 9. Timeline / activity logging
Implemented:
- timeline event creation in key flows
- dashboard recent activity usage
- document workflow logging
- PIP and related action tracking

Scope notes:
- timeline logging exists but is still lightweight
- not yet a full audit log

---

## 10. Technical foundations
Implemented:
- Flask
- SQLAlchemy
- Flask-Migrate
- CSRF protection
- blueprint-based feature split
- service layer extraction
- SQLite local DB
- WSGI entry point
- template-driven UI
- OpenAI integration

---

## Explicitly in current scope
These are part of the app as it exists today:
- internal HR workflow support
- line-manager support for PIPs
- document generation for PIP process
- draft/resume workflows
- role-filtered access
- local deployment/dev usage
- migration-backed schema evolution

---

## Not yet fully in scope / not complete
These are either partial, future, or still rough around the edges:

### Structural
- full app-factory conversion
- full removal of compatibility alias layer
- fully modular template folder structure

### Product / workflow
- polished audit trail across every entity
- advanced reporting beyond current dashboards
- deep permissions model beyond current `admin_level`
- external client portal
- API-first architecture
- fully centralised settings/config UI

### Repo / engineering hygiene
- cleaned repo artifact history
- removal of duplicate service files
- removal of historical backup code from main tree
- production-grade secrets/config separation in repo snapshot

---

## Current user roles / access model
Broadly supported:
- superuser / higher admin
- lower admin / line-manager-style limited view

Observed current behaviour:
- lower admin users are filtered to relevant team data in some flows
- superuser-only routes exist for admin tooling and imports

---

## Current data entities in play
Main observed entities:
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

## Phase 1E close-out summary
At the end of Phase 1E:
- `app.py` is now mainly bootstrap + dashboard + compatibility glue
- feature routes are in blueprints
- shared logic is in services
- the app still intentionally runs in a hybrid architecture
- route behaviour has been preserved through the refactor

This is the correct current scope baseline for future feature work or tidy-up phases.
