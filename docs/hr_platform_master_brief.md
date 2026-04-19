# HR Platform Master Brief

## Status
This document consolidates the current product, architecture, and development direction into a single working baseline.

It is intended to act as the master reference for future planning, development, and handoff.

---

## 1. Core Product Direction

The product is now a **module-first HR operations and case management platform**.

It should no longer be positioned primarily as a care-specific product.
Instead, it should be positioned as a broader HR workflow platform with optional **sector-specific packs**, with **Care** as the first specialist pack.

This is a **commercial and packaging pivot**, not a technical reset.

### Strategic positioning
The platform combines:
- structured HR workflows
- case management
- AI-assisted guidance
- built-in AI governance and auditability
- future advisor escalation workflows
- future multi-organisation commercial SaaS capability

### Recommended positioning statement
**A modular HR workflow and case management platform for employers, with structured people-process modules, AI guidance with governance, and future advisor escalation support.**

---

## 2. Strategic Summary

The strongest commercial direction is:
- broad modular HR platform first
- specialist sector packs second
- Care as the first sector pack
- AI governance and advisor escalation as differentiators

This keeps the current technical base relevant while broadening the addressable market.

### Commercial benefits
- broader than care alone
- easier packaging and pricing
- modular upsell path
- stronger long-term product identity
- more defensible than a narrow PIP-only or care-only product

---

## 3. Product Architecture Model

The platform should be understood in four layers.

### Layer A — Core Platform
Shared capabilities used across all enabled modules and sectors.

#### Responsibilities
- authentication
- authorisation
- organisation settings
- users and roles
- employee / people records
- dashboard and workspace shell
- timeline / audit history
- document storage and generation
- template rendering
- AI consent / warning controls
- advisor escalation framework
- shared reporting foundation
- API-readiness foundation
- module enablement / configuration

### Layer B — Functional Modules
Discrete or semi-discrete HR workflow domains.

#### Current / live modules
- PIP / capability
- probation
- sickness
- employee relations

#### Planned modules
- supervision
- disciplinary
- grievance
- compliance
- return-to-work
- onboarding
- reporting / insights

### Layer C — Sector Packs
Configuration overlays rather than separate codebases.

#### First sector pack
- Care Pack

#### Sector pack concerns
- labels / terminology
- templates
- workflow defaults
- reporting widgets
- dashboard language
- compliance extras
- recommended fields
- example content

### Layer D — Advisory Escalation
Service-integrated workflow capability.

#### Responsibilities
- AI warning / disclaimer interactions
- consent capture
- advisor escalation triggers
- packaging case history and documents
- tracking escalation state
- secure audit trail
- future human advisor handoff workflow

---

## 4. Technical Direction

The current technical base remains correct.

### Current architecture
- Flask modular monolith
- SQLAlchemy
- Jinja templates
- Tailwind CSS
- blueprint-based route separation
- server-rendered UI
- additive service-layer extraction pattern
- OpenAI integration
- low-risk incremental evolution

### Core rule
This direction does **not** justify a rewrite.

The pivot is about:
- product framing
- packaging
- modular enablement
- sector overlays
- advisory workflows
- multi-organisation readiness

It is **not** about rebuilding the stack.

---

## 5. Architecture Principles

### Preserve and extend
- keep the modular monolith
- preserve additive development
- avoid rewrite risk
- keep existing routes and blueprints stable
- separate configuration from code duplication

### Configuration over forking
Sector-specific behaviour should come primarily from:
- configuration
- templates
- defaults
- labels
- dashboard options

Sector packs should **not** create separate product codebases unless explicitly necessary.

### Thin routes, stronger services
Routes should remain thin and coordinate service calls.
Domain logic should increasingly live in services.

### Safe API evolution
Future APIs should expose stable domain contracts rather than sector-specific duplicated endpoints.

---

## 6. Domain Map

### Domain 1 — Platform Core
- auth
- users
- roles
- organisation settings
- branding / configuration
- template management
- module enablement
- AI warnings / acceptance
- advisor escalation settings
- API keys

### Domain 2 — People Core
- employee records
- lifecycle status
- manager assignment
- service / team assignment where relevant
- notes / history
- leaver / reactivation handling

### Domain 3 — Workflow Modules
- probation
- supervision
- PIP / capability
- sickness
- investigation
- disciplinary
- grievance
- return-to-work
- employee relations workflows
- related documents

### Domain 4 — Sector Configuration
- sector labels
- sector templates
- sector compliance additions
- workflow guidance
- dashboard variants
- recommended defaults

### Domain 5 — Reporting & Insights
- dashboard metrics
- module reporting
- filters by manager / service / organisation
- trend summaries
- export-ready data
- future API reporting surfaces

### Domain 6 — Advisory Workflows
- AI advice requests
- warning banners
- consent capture
- escalate-to-advisor actions
- case packaging
- escalation tracking

---

## 7. AI Governance Position

AI is already treated as governed product functionality, not a future idea.

### Live behaviour
- AI advice requires consent check
- consent is logged in `AIConsentLog`
- consent logging includes user, timestamp, IP, and user agent
- timeline events are created for AI-related activity
- AI advice is stored on relevant records
- AI routes fail more safely when API configuration is missing or invalid
- app startup no longer depends on a live OpenAI key

### Design principle
AI must always be:
- transparent
- auditable
- consent-driven
- defensible in an HR / legal context

### Commercial meaning
The platform should be positioned as:
**AI-assisted HR workflows with built-in governance, auditability, and advisor escalation direction.**

---

## 8. Current Implemented State

### Already implemented
- AI governance layer is live
- consent logging exists
- timeline-based audit behaviour exists
- AI advice storage is live
- module enablement system exists
- `Organisation` model exists
- `OrganisationModuleSetting` model exists
- admin module settings page exists
- sidebar and workspace visibility respect enabled modules
- workspace statistics respect enabled modules
- admin dashboard shows module status
- shared helper direction exists for organisation/module visibility logic

### Important limitation
The current module enablement implementation is still effectively **single-organisation mode**.

#### What that means
- current logic uses a default / first organisation
- module settings behave globally for the current instance
- route blocking is not yet the core enforcement model
- full multi-tenant isolation is not implemented yet

---

## 9. Multi-Organisation Direction

The next major architectural phase is the **multi-organisation foundation**.

### Goal
Move safely from:
- single-organisation modular platform

to:
- multi-organisation modular SaaS platform

### What this must eventually support
- users belong to organisations
- module settings resolve per organisation
- admin settings become organisation-scoped
- data ownership becomes organisation-aware
- tenant-safe isolation becomes possible across employees, cases, documents, AI logs, and API keys

### Important status note
This is **planned groundwork**, not fully implemented behaviour.

---

## 10. Current Blueprint / Codebase Rules

### Existing architecture pattern
The blueprint-based approach remains the right structure.

### Rule
Do not rename existing routes, endpoints, or blueprints unless explicitly approved in advance.

### Existing / expected blueprint direction
- `auth`
- `admin`
- `main`
- `employees`
- `manage_employee`
- `pip`
- `probation`
- `sickness`
- `employee_relations`
- future `supervision`
- future `compliance`
- future `reporting`
- future `api_v1`

### Development principle
Blueprints should represent domains and modules.
Sector packs should shape configuration, content, and presentation rather than create parallel route trees unless truly necessary.

---

## 11. Service Layer Direction

The service layer is increasingly important under the module-first architecture.

### Platform services
- permissions service
- organisation configuration service
- module enablement service
- branding / settings service

### People services
- employee lifecycle service
- employee scoping service
- manager assignment helpers

### Workflow services
- probation service
- supervision service
- PIP service
- sickness service
- ER case service

### Sector services
- sector pack resolution / configuration service
- template selection service
- workflow defaults service

### Advisory services
- AI guidance orchestration service
- disclaimer / consent recording service
- escalation packaging service
- advisor handoff service

### Reporting services
- dashboard aggregation service
- module reporting service
- insights / summary service

---

## 12. Data Model Direction

The SQLAlchemy model approach remains appropriate.

### Existing models likely retained
- `User`
- `Employee`
- `PIPRecord`
- probation models
- sickness models
- employee relations models
- `TimelineEvent`
- document / draft entities
- `Organisation`
- `OrganisationModuleSetting`
- `AIConsentLog`

### Likely future model categories
#### Platform configuration
- organisation-scoped settings records
- branding records
- API key records
- module setting extensions

#### Advisory workflow
- `AdvisorEscalation`
- `AdvisorEscalationDocument`
- AI request / consent / escalation tracking extensions where needed

#### Sector configuration
- sector pack settings
- template mapping by sector
- dashboard/widget configuration by sector if needed

#### Module expansion
- `SupervisionRecord`
- `ReturnToWorkRecord`
- additional ER case entities where needed

### Core rule
Sector-specific behaviour should usually come from configuration and templates, not duplicated sector data models.

---

## 13. UI / UX Direction

The UI should remain server-rendered with Jinja.

### UX framing
The product should increasingly present:
- a core workspace
- enabled modules
- role-aware dashboards
- advisor escalation options
- sector-aware terminology where configured

### Experience goal
The platform should feel:
- modular
- configurable
- practical
- advisor-backed
- broader than one vertical unless a sector pack is active

### Example navigation shape
- Home
- People
- Modules
- Documents
- Reporting
- Admin

Under Modules:
- Probation
- Supervision
- PIP
- Sickness
- Investigation
- Disciplinary
- Grievance
- Compliance

This should remain permission-aware and enabled-module-aware.

---

## 14. API Direction

API expansion remains strategically useful.

### Immediate API purpose
- expose module data cleanly
- support integrations
- support future workflow hooks
- support advisor escalation and event exchange later

### API principle
Expose stable `/api/v1/` domain contracts.
Do not duplicate APIs by sector unless there is a compelling reason.

### Recommended API grouping
- `/api/v1/employees`
- `/api/v1/probation`
- `/api/v1/pip`
- `/api/v1/sickness`
- `/api/v1/employee-relations`
- `/api/v1/supervision`
- `/api/v1/reporting`
- `/api/v1/advisor-escalations`

---

## 15. Advisor Escalation Direction

Advisor escalation is strategically important enough to be treated as a first-class capability.

### Core future workflow
1. user works through a module or case
2. user requests AI guidance
3. system presents clear warning / disclaimer
4. user acknowledges AI is guidance only
5. user can trigger escalation to advisor
6. system packages relevant case history and selected documents
7. escalation is sent or queued for human review

### Required concerns
- consent acknowledgement
- case summary generation
- selected-document packaging
- escalation status tracking
- audit trail
- secure permissions

### Strategic meaning
This may become one of the strongest differentiators in the product.

---

## 16. Product Packaging Model

### Core platform package
- employee records
- dashboard / workspace
- timeline / history
- documents
- admin and organisation settings
- AI guidance framework
- advisor escalation capability foundation

### Standard module bundle
- probation
- supervision
- PIP / capability

### Add-on module examples
- investigations pack
- disciplinaries & grievances pack
- sickness & return-to-work pack
- compliance pack
- reporting pack
- AI workflow support pack
- sector pack: care

---

## 17. Roadmap Structure

### Phase 1 — Product reframing
- update product documentation
- align internal language around platform / modules / packs
- rework navigation and workspace wording
- standardise master product positioning

### Phase 2 — Module packaging foundation
- define standard modules vs add-ons
- strengthen enabled-module UX
- standardise module launch surfaces
- align dashboards and workspace cards to packaging model

### Phase 3 — Multi-organisation foundation
- link users to organisations
- resolve module settings per organisation
- move admin settings toward organisation scope
- prepare safe data ownership migration path
- preserve existing routes and additive development

### Phase 4 — Standard modules
- strengthen probation
- add / strengthen supervision
- strengthen PIP / capability

### Phase 5 — Add-on modules
- investigation
- disciplinary
- grievance
- sickness / return-to-work
- compliance

### Phase 6 — Care Pack
- care terminology
- care templates
- care workflow defaults
- care-specific compliance and reporting extras

### Phase 7 — Advisor escalation
- disclaimers
- acceptance capture
- push-to-advisor workflow
- escalation tracking
- case packaging

### Phase 8 — API and reporting expansion
- module endpoints
- reporting summaries
- integration surfaces
- external workflow hooks where needed

---

## 18. Non-Negotiable Development Rules

### Route and behaviour safety
1. Do not rename, remove, or change existing Flask routes or endpoints unless explicitly approved.
2. Do not break existing functionality.
3. Preserve existing route names, blueprint names, templates, models, and field names unless explicitly requested.
4. Preserve current behaviour unless the requested task specifically changes it.

### Change control
5. If a change is risky, breaking, or could affect existing behaviour, explain the risk first and wait for approval.
6. Avoid unnecessary refactors.
7. Work one file at a time where possible to reduce risk.
8. If the exact current file is needed for a safe edit, request the full file first.

### Code delivery rules
9. Always provide full pasteover code for file changes unless snippets are explicitly requested.
10. Do not provide speculative edits to unseen files.
11. Do not silently clean up unrelated code.
12. Do not overengineer.

### Working style
13. Prefer practical, production-minded solutions.
14. Think commercially as well as technically.
15. Suggest the best next step when useful.

---

## 19. Current Working Baseline

### AI-related areas already hardened
- AI utility loading is safer
- OpenAI client creation is lazy rather than import-time dependent
- AI routes fail more gracefully when configuration is missing
- app startup and migrations do not rely on a valid live OpenAI key

### Module settings / organisation groundwork in place
- `Organisation` model exists
- `OrganisationModuleSetting` model exists
- module settings route exists in admin
- enabled modules are injected into templates
- sidebar / module navigation respects enabled modules
- workspace cards respect enabled modules
- workspace stats respect enabled modules
- admin dashboard surfaces module status
- module settings UI includes enabled summary banner
- shared organisation/module helper direction exists

### Current limitation to keep in mind
This is still a transitional architecture state, not a fully tenant-isolated system.

---

## 20. Naming Direction

Broad people / workflow-oriented naming remains stronger than care-specific master naming.

### Strong naming characteristics
- broad enough for multi-sector growth
- compatible with modular packaging
- suitable for AI guidance + advisor escalation
- not tied to one module or one vertical

### Naming rule
Care-specific naming is better suited to a sector pack than the top-level product identity.

---

## 21. Master Strategic Statement

The product should be built as a **module-first HR operations and case management platform** with:
- a shared core platform
- practical workflow modules
- optional add-on modules
- sector-specific packs beginning with Care
- governed AI guidance
- future advisor escalation workflows
- future multi-organisation SaaS capability
- additive API readiness

This preserves the strength of the current application while creating a broader and more commercially scalable product direction.

---

## 22. Recommended Immediate Next Build Focus

The highest-value next architectural step is:

### Multi-organisation foundation
Specifically:
- safe user-to-organisation linkage
- organisation-aware module resolution
- organisation-scoped admin settings groundwork
- phased data ownership strategy
- no route breakage
- minimal-risk additive migration path

### Why this is next
This is the main structural gap between the current working application and a commercially viable multi-organisation platform.

---

## 23. Working Instruction for Future Chats

When continuing development:
1. choose the safest implementation path
2. preserve routes and behaviour
3. request the exact current file when a safe edit requires it
4. return full pasteover code only unless explicitly told otherwise
5. flag migration or architecture risk clearly before any breaking change

This document should now be treated as the consolidated baseline for product and engineering direction.

