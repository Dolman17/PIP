# PIP CRM — New Chat Prompt (Manage Employee Module Kickoff)

You are continuing development of the PIP CRM Flask app.

## Current baseline
The app is a stable hybrid blueprint + service architecture:
- `app.py` is the shell/bootstrap
- routes live in `pip_app/blueprints/*`
- shared logic lives in `pip_app/services/*`
- canonical models live in `pip_app/models.py`
- templates are mostly in `templates/`
- Employee Relations is already a live module with meetings, attachments, policy text, structured AI advice, and document workflows

The current baseline documents for this next chat are:
- `app_scopev5.md`
- `architecturev5.md`

## Important working preferences
- Do not rename, remove, or alter existing routes/endpoints unless explicitly asked first.
- Do not make major/risky/breaking changes silently.
- If a change is schema-affecting or could break existing behaviour, explain the risk first.
- Keep changes incremental and practical.
- Prefer full pasteover files when providing code.
- Preserve existing working functionality unless the requested change explicitly replaces it.

## Next planned feature area
Build a new **Manage Employee** module.

## Goal of the module
Create a more complete employee-management / personnel-file style module that goes beyond the current lightweight employee CRUD pages.

A key requirement is the ability to make an employee a **leaver**, so that the app can later support:
- turnover statistics
- attrition reporting
- better active vs leaver tracking
- future historic headcount continuity

## What the new Manage Employee module should cover
Planned scope:
- richer employee management area
- personnel-file style administration features
- active vs leaver state handling
- structured **make employee a leaver** workflow
- leaving date capture
- leaving reason/category capture
- optional lifecycle notes
- preservation of former employees historically rather than deleting records
- future-ready foundation for turnover analytics

## Architectural direction
Recommended approach:
- keep the current `employees_bp` stable for existing employee CRUD/import flows
- introduce a separate `manage_employee_bp` if that is the cleanest option
- keep lifecycle/leaver logic in dedicated service/helper functions where appropriate
- treat leaver handling as a state transition, not a delete/archive shortcut

## First task for the new chat
Start by designing the Manage Employee module safely and incrementally.

Recommended first outputs:
1. Proposed module scope and screens
2. Suggested model changes needed for active/leaver tracking
3. Recommended blueprint/routes structure
4. Step-by-step build order
5. Any risk flags before code changes

## Current context note
Employee Relations document origin is now being stored explicitly via `draft_origin`, and the project is moving on from ER document refinement to the new Manage Employee module as the next planned phase.
