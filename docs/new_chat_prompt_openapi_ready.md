# New Chat Prompt — PIP CRM Open API Readiness Phase

We are continuing development of the PIP CRM / Ellipse HR system.

## Important working preferences
Please follow these strictly:
- Do not rename or remove existing routes, models, forms, templates, or helper functions unless explicitly requested.
- Do not make risky or breaking structural changes silently.
- If a proposed change is major, risky, or could break current functionality, explain that clearly before proceeding.
- Prefer additive changes.
- I prefer full pasteover code, not partial diffs.
- Keep all existing route names and blueprint names intact.
- Respect current working endpoint names and blueprint-qualified `url_for(...)` usage.

## Current baseline
The app is a Flask + SQLAlchemy + Jinja + Tailwind internal HR workflow system with these live modules:
- PIP
- Probation
- Sickness
- Employee Relations
- Manage Employee lifecycle
- Admin tools

Recent live additions already completed:
- Manage Employee lifecycle module with mark-as-leaver and reactivate flows
- lifecycle protections preventing new records for leavers
- first Manage Employee reporting view (`/manage-employees/reporting`)
- workspace home upgraded from simple module selector to a production-style operational landing page with live KPIs and recent activity
- admin blueprint redirect fix for user creation/edit/delete flow

## Current architecture shape
- `app.py` is still the bootstrap shell
- feature routes live in `pip_app/blueprints/*`
- shared logic lives in `pip_app/services/*`
- models live in `pip_app/models.py`
- server-rendered templates remain the main UI approach
- this is NOT yet an app-factory rewrite

## Goal for this new phase
We now want to make the app **OpenAPI-ready** in a controlled, low-risk way.

That means:
- preparing the app for versioned API endpoints
- introducing clean JSON response structure
- separating API serialization from HTML rendering
- keeping all current UI functionality working unchanged
- designing the API layer so OpenAPI docs/spec generation can be added cleanly

## What I want you to help me build next
I want the next chat to focus on designing and implementing the first API foundation.

### Recommended starting scope
Please start with:
1. A low-risk API architecture plan for this app
2. The proposed folder/file structure for API support
3. A common API response format
4. A serializer pattern for model-to-JSON output
5. The first versioned API blueprint, e.g. `/api/v1`
6. A safe authentication approach for internal API usage
7. The first read-only endpoints to implement

## Recommended first endpoints
Start with read-only endpoints only.

Priority candidates:
- `/api/v1/employees`
- `/api/v1/employees/<id>`
- `/api/v1/manage-employee/reporting/summary`
- `/api/v1/pips`
- `/api/v1/probations`
- `/api/v1/sickness-cases`
- `/api/v1/employee-relations/cases` (restricted)

## Constraints
- No schema changes unless genuinely needed and clearly justified
- No route renames
- No breaking UI changes
- No frontend rewrite
- No public/open internet exposure design yet
- No write endpoints in the first pass unless explicitly requested

## What I want first in this new chat
Please begin by giving me:
1. A practical OpenAPI-readiness plan tailored to the current app
2. The recommended API folder structure
3. The exact first files we should create
4. Any low-risk prerequisites we should put in place before coding

Then, once agreed, move into full pasteover code for the first API foundation files.
