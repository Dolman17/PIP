# Phase 1E Close-out

## Outcome
Phase 1E is complete.

The app has been moved from a large mixed `app.py` toward a safer hybrid structure:
- route logic is largely blueprint-based
- shared helper logic now lives in services
- `app.py` has been reduced to bootstrap, compatibility, and dashboard concerns
- regression checks passed during the refactor

---

## Completed in Phase 1E

### Service extraction complete
Shared helper logic has been extracted into:
- `ai_utils.py`
- `auth_utils.py`
- `dashboard_utils.py`
- `document_utils.py`
- `import_utils.py`
- `sickness_metrics.py`
- `storage_utils.py`
- `taxonomy.py`
- `time_utils.py`
- `timeline_utils.py`

### Blueprint alignment complete
The following blueprints now consume services rather than depending on large helper blocks in `app.py`:
- `pip.py`
- `employees.py`
- `probation.py` for time helpers
- `sickness.py` for time helpers and sickness metrics

### `app.py` reduced
`app.py` now focuses on:
- Flask setup
- extension initialisation
- blueprint registration
- CSRF exemptions
- context processors
- legacy endpoint alias compatibility
- active module switching
- dashboard routes
- health route

---

## What was explicitly preserved
To reduce risk, the following were intentionally preserved:
- existing route URLs
- existing endpoint names via alias shim
- current login / role behaviour
- active module handling
- current dashboard behaviour
- current document flow
- current draft/resume flow

---

## Validation completed
The following areas were re-tested during close-out:
- app boot
- dashboard
- dashboard stats JSON
- employee list/detail/add/edit
- employee quick-add
- employee import flow
- PIP wizard
- AI suggestion endpoints
- document draft/edit/finalise/download flow
- sickness dashboard
- probation pages using date helpers

All reported as working after the final `app.py` cleanup.

---

## Remaining tidy items
These are not blockers, but should be handled in a small follow-up cleanup phase:

### 1. Duplicate service modules
Current duplicates/overlaps:
- `sickness_metrics.py` vs `sickness_utils.py`
- `timeline_utils.py` vs `timeline.py`

Action:
- choose one canonical file for each concern
- remove the duplicate after confirming imports

### 2. Repo hygiene
Current repo snapshot still includes:
- `.env`
- `.venv` / `.venv-1`
- local DB file
- historical backup files
- nested git-related artifacts

Action:
- clean repo contents
- confirm `.gitignore`
- remove non-source artifacts from tracked tree

### 3. Unused imports / dead code
Action:
- run one lightweight cleanup pass
- remove dead imports and obsolete transitional comments

---

## Recommended next step
The safest next move is **not** another major refactor.

Recommended order:
1. short tidy/cleanup pass
2. re-baseline documentation
3. return to feature delivery

This keeps the architectural gains from Phase 1E without reopening avoidable risk.
