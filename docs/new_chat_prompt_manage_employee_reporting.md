# PIP CRM — New Chat Prompt (Manage Employee Reporting View)

You are continuing development of the PIP CRM Flask app.

## Current baseline

The app is running in a stable hybrid blueprint + service architecture:

- `app.py` is the shell/bootstrap
- routes live in `pip_app/blueprints/*`
- shared logic lives in `pip_app/services/*`
- canonical models live in `pip_app/models.py`
- templates are mostly in `templates/`

Live functional areas already include:
- authentication
- dashboard
- employee CRUD/import
- PIP module
- probation module
- sickness module
- Employee Relations module
- admin tools

A new **Manage Employee** module now exists and is live enough to use for employee lifecycle administration.

## Important working preferences

- Do **not** rename, remove, or alter existing routes/endpoints unless explicitly asked first.
- Do **not** make major/risky/breaking changes silently.
- If a change is schema-affecting or could break existing behaviour, explain the risk first.
- Keep changes incremental and practical.
- Prefer full pasteover files when providing code.
- Preserve existing working functionality unless the requested change explicitly replaces it.

## Current Manage Employee status

Implemented:

### Blueprint
- `manage_employee_bp`

### Routes
- `/manage-employees`
- `/manage-employees/<employee_id>`
- `/manage-employees/<employee_id>/mark-leaver`
- `/manage-employees/<employee_id>/reactivate`

### Lifecycle service support
- `get_employee_status_label(employee)`
- `mark_employee_as_leaver(...)`
- `reactivate_employee(...)`

### Current lifecycle data now in use on `Employee`
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

### Current lifecycle behaviour
- employees are preserved historically
- leaver handling is a state transition, not deletion
- reactivation keeps historic leave metadata intact for now
- downstream modules now block new records for leavers:
  - PIP
  - Probation
  - Sickness
  - Employee Relations

## Current Manage Employee templates in place

- `templates/manage_employee/index.html`
- `templates/manage_employee/detail.html`
- `templates/manage_employee/mark_leaver.html`

These already support:
- active / leaver / all filtering
- search
- lifecycle badges
- lifecycle detail panel
- mark as leaver flow
- reactivate flow
- linked-record summaries

## Next planned feature for this new chat

Build the **first reporting view** for the Manage Employee module.

## Goal of this reporting view

Create a low-risk first reporting screen using the new employee lifecycle data so the app can start showing simple turnover-style insights without major schema change.

## Reporting scope for this phase

Build a first reporting view that includes:

- active employee count
- leaver count
- total employee count
- leavers by month
- leavers by reason category
- optionally leavers by service if easy and low risk

Keep the reporting view practical and light:
- no major analytics engine
- no major refactor
- no risky model restructuring

## Architectural direction

Recommended implementation approach:

- add a new route under `manage_employee_bp`
- add a dedicated template, likely:
  - `templates/manage_employee/reporting.html`
- use existing `Employee` lifecycle fields as the data source
- calculate aggregates in the blueprint or a small dedicated helper/service if it improves cleanliness
- keep queries team-aware for lower admin users if that pattern already exists for scoped employee data

## Suggested build order

1. Design the reporting route and template safely
2. Add headline KPI cards
3. Add monthly leaver breakdown
4. Add leaving-reason breakdown
5. Optionally add service breakdown if clean
6. Link to the reporting page from the Manage Employee index/detail area

## Risk notes

Potential low-risk:
- adding a reporting route/template
- additive query logic
- additive nav links

Potential higher-risk:
- introducing a brand-new analytics model
- changing existing employee route behaviour
- changing lifecycle field semantics

Avoid higher-risk changes unless explicitly agreed.

## First task in the new chat

Start by proposing the first reporting view design and then provide the full pasteover for:
- updated `pip_app/blueprints/manage_employee.py`
- new `templates/manage_employee/reporting.html`

If helpful, also provide any small template link updates needed in:
- `templates/manage_employee/index.html`
- `templates/manage_employee/detail.html`

## Current context note

The Manage Employee module is now the active next-phase feature area. The immediate goal is not more lifecycle schema work, but the first usable reporting view built from the lifecycle data now already in place.
