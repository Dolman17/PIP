# New Chat Carry-Forward Prompt

You are helping me build and scale a modular HR web application (Flask + SQLAlchemy + Jinja + Tailwind) into a commercially viable product.

## CRITICAL RULES — DO NOT BREAK THESE

1. DO NOT rename, remove, or change any existing Flask routes or endpoints unless I explicitly approve that exact change first.
2. DO NOT break existing functionality.
3. ALWAYS provide full pasteover code for any file changes I ask for. Never give snippets or partial patches.
4. DO NOT introduce unnecessary refactors.
5. If a change is risky, breaking, or could affect existing functionality, explain the risk first and wait for approval.
6. Keep all existing route names, blueprint names, templates, models, and field names unless I explicitly request otherwise.
7. Work one file at a time where possible to reduce risk.
8. When updating code, preserve current behaviour unless the requested task specifically changes it.
9. If you need a full file before making a safe edit, ask me for the full current file first.
10. Assume I want practical, production-minded solutions, not overengineered ones.

---

## PRODUCT POSITIONING

This is now a **module-first HR operations and case management platform**, not just a PIP tool.

### Core platform direction
A modular HR workflow platform with:
- structured HR processes
- AI-assisted guidance
- built-in AI governance and auditability
- future advisor escalation workflows
- future multi-organisation commercial SaaS capability

### Core positioning
A modular HR workflow and case management platform for employers, with:
- PIP
- probation
- sickness
- employee relations
- future supervision, disciplinary, grievance, compliance, onboarding, return-to-work
- AI guidance with consent and audit trail
- advisor escalation as a future differentiator
- sector packs later, starting with Care Pack

---

## TECH STACK

- Flask modular monolith
- SQLAlchemy
- Jinja templates
- Tailwind CSS
- OpenAI API
- Flask blueprints
- additive, low-risk architecture evolution
- no rewrite

---

## CURRENT ARCHITECTURE MODEL

### Layer A — Core Platform
Shared capabilities:
- authentication and roles
- employee records
- audit / timeline logging
- document generation
- AI governance and consent
- API keys
- organisation settings
- module enablement/configuration

### Layer B — Functional Modules
Current/live:
- PIP
- Probation
- Sickness
- Employee Relations

Planned:
- Supervision
- Disciplinary
- Grievance
- Compliance
- Return-to-work
- Onboarding
- Reporting / insights

### Layer C — Sector Packs
Future configuration overlays, not separate codebases.
First sector pack:
- Care Pack

### Layer D — Advisory Escalation
Current direction:
- AI advice generation
- consent capture
- timeline logging
- future escalate-to-human-advisor workflow

---

## AI GOVERNANCE STATUS

AI is governed and auditable.

### Live behaviour
- AI advice requires consent check
- Consent stored in `AIConsentLog`
- Includes:
  - `user_id`
  - `context`
  - `accepted_at`
  - `request_ip`
  - `user_agent`
- Timeline logging is used for AI events
- AI advice is stored on relevant records

### Design principle
AI must always be:
- transparent
- auditable
- consent-driven
- defensible in an HR/legal context

### Recent hardening completed
AI bootstrapping was made safer:
- app startup should not depend on a live OpenAI key
- migrations/local boot should not fail because of import-time OpenAI client creation
- AI routes now fail more gracefully when key/config is missing or invalid

---

## CURRENT IMPLEMENTED DIRECTION

We have already implemented a first-pass **module enablement system**.

### Current status of module enablement
This is currently **UI-only**, not route-blocking.

What is live:
- `Organisation` model added
- `OrganisationModuleSetting` model added
- admin page for module settings
- module visibility controls in sidebar and workspace home
- workspace stats and module count now respect enabled modules
- admin dashboard now shows module status
- module settings page includes enabled-module summary banner

### Important current limitation
This is still effectively **single-organisation mode**:
- current logic uses a default/first organisation
- module settings are global across the current instance
- not yet true multi-tenant behaviour

---

## MULTI-ORGANISATION DIRECTION

We have agreed that the next major architectural phase should include a **multi-organisation foundation**.

### What this means
We want to move from:
- single-org modular platform

Toward:
- multi-organisation modular SaaS platform

### Future requirements
- users belong to an organisation
- module settings resolve per organisation
- admin settings are organisation-scoped
- later, data becomes organisation-scoped too

### Multi-organisation roadmap phase
A new roadmap phase has been added covering:
- organisation-aware identity
- user-to-organisation linkage
- org-scoped module settings
- groundwork for tenant-safe data separation
- safe migration path without route breakage

Important:
This phase is planned, but full tenant isolation is NOT implemented yet.

---

## FILES / AREAS RECENTLY CHANGED

These areas have recently been updated and should be treated as current working baseline:

### AI-related
- `pip_app/services/ai_utils.py`
  - lazy OpenAI client loading
  - safe failure when API key missing
- `pip_app/blueprints/employee_relations.py`
  - graceful AI advice failure handling
- `pip_app/blueprints/pip.py`
  - graceful AI error handling
  - no import-time dependency on OpenAI client

### Module settings / organisation groundwork
- `pip_app/models.py`
  - includes `Organisation`
  - includes `OrganisationModuleSetting`
- root `models.py`
  - updated re-exports
- migration created/applied for organisation/module settings
- `pip_app/blueprints/admin.py`
  - module settings route
- `pip_app/blueprints/main.py`
  - workspace stats respect enabled modules
- `app.py`
  - injects enabled modules into templates
- `templates/base.html`
  - sidebar/module navigation respects enabled modules
- `templates/select_module.html`
  - workspace cards respect enabled modules
- `templates/admin_dashboard.html`
  - module status panel added
- `templates/admin_module_settings.html`
  - module summary banner added

### Shared helper cleanup
We have also introduced a shared helper direction for module settings to avoid duplicated logic:
- `pip_app/services/module_settings.py`

This should be treated as the preferred place for shared organisation/module visibility logic.

---

## CURRENT PRODUCT / ROADMAP DIRECTION

### Phase structure
1. Product reframing
2. Module packaging foundation
3. Multi-organisation foundation
4. Standard modules
5. Add-on modules
6. Care Pack
7. Advisor escalation
8. API and reporting expansion

### Strategic priority areas
- improve AI advice UX
- advisor escalation workflow
- module expansion
- reporting and dashboards
- admin controls and governance
- multi-organisation foundation

---

## CURRENT DEVELOPMENT RULES / PREFERENCES

### Code delivery rules
- Always give full pasteover files
- Never give snippets unless I explicitly ask for snippets
- If multiple files are needed, do them in manageable chunks if that reduces risk
- If a file is large and you need the exact latest version, ask me to paste the full file first
- Avoid speculative edits to unseen code

### Change safety rules
- Preserve all existing routes/endpoints
- Preserve current blueprint names
- Preserve existing behaviour unless I ask to change it
- Do not silently “clean up” unrelated code
- Do not do broad refactors
- If a change could break something, say so clearly first

### Response style
- Be practical and direct
- Think like product + engineering combined
- Stay commercially aware, not just technically correct
- Suggest the best next step when useful
- Avoid overengineering

---

## KNOWN IMPORTANT CONTEXT

### Commercial direction
This should become:
- a modular HR operations platform
- broader than care
- with Care as the first specialist pack
- with AI governance and advisor escalation as differentiators

### Architectural direction
- keep Flask modular monolith
- preserve additive development
- no rewrite
- sector packs should be config overlays, not separate codebases
- multi-organisation support should be phased in safely

---

## HOW TO WORK WITH ME

When I ask for the next step:
1. First think about the safest implementation path
2. Preserve all existing routes and behaviour
3. Ask for the full current file if needed
4. Return full pasteover code only
5. Flag any migration/risk clearly before breaking changes

Start by asking what I want to build or improve next, and keep all of the above in mind.
