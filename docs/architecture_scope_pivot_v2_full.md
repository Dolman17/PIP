# Architecture & Scope Pivot — Module-First HR Platform (v2)

## Status
Updated to reflect implemented AI governance, consent logging, and advisory workflows.

---

## NEW: AI Governance Layer (IMPLEMENTED)

The platform now includes a live AI governance system:

### Live behaviour
- AI advice requires consent check
- Consent stored in AIConsentLog
- Includes user, timestamp, IP, user agent
- TimelineEvent created for audit trail
- Advice stored on PIPRecord

### Architectural impact
AI governance is now part of:
- Core Platform (Layer A)
- Advisory Workflows (Layer D)

### Design principle
AI usage must always be:
- transparent
- auditable
- consent-driven

---

# Architecture & Scope Pivot — Module-First HR Platform (v1)

## Status
This document updates the architecture and scope direction to reflect the latest commercial pivot.

The platform should no longer be treated primarily as a **care-specific workforce platform**.  
Instead, it should be treated as a **module-first HR operations platform** with optional **sector-specific packs**, beginning with care.

This is an additive pivot.  
The existing Flask codebase remains the delivery base.

---

## 1. Strategic architecture statement

The system should evolve into a:

**domain-structured, module-first HR operations platform with sector-specific packs and advisor-escalation workflows, built on the current Flask modular monolith.**

This means:
- keep the current modular monolith
- keep existing routes and blueprints stable
- preserve additive development
- avoid rewrite risk
- separate platform core from modules and sector overlays
- support future API-led integrations

---

## 2. Scope shift

### Previous scope emphasis
- social care workforce platform
- care-specific people operations product
- sector-led identity at the master-product level

### New scope emphasis
- modular HR operations platform
- configurable modules
- cross-sector commercial usability
- care as first specialist pack
- hybrid software + advisory model

### Key implication
The core product should be broader than care, while the first specialist pack can still be care-oriented.

---

## 3. Product architecture layers

The product should now be thought of in four architectural layers.

## Layer A — Core Platform
Shared platform capabilities used regardless of enabled modules or sector pack.

### Responsibilities
- authentication
- authorisation
- organisation settings
- users and roles
- people/employee records
- timeline/audit history
- document storage and generation
- dashboard shell
- module enablement/configuration
- AI consent/warning controls
- advisor escalation framework
- shared reporting framework
- API contracts and keys

### Architectural role
Provides stable shared infrastructure for the rest of the product.

---

## Layer B — Functional Modules
Independent or semi-independent HR workflow domains.

### Standard modules
- probation
- supervision
- PIP / capability

### Add-on modules
- investigation
- disciplinary
- grievance
- sickness / absence
- return-to-work
- compliance
- onboarding
- reporting / insights

### Architectural role
Functional domains that can be enabled, grouped, or sold separately.

---

## Layer C — Sector Packs
Configuration overlays that shape terminology, templates, workflow defaults, and dashboards.

### First sector pack
- Care Pack

### Sector pack concerns
- naming/labels
- templates
- process guidance
- recommended fields
- dashboard widgets
- compliance extras
- workflow defaults

### Architectural role
Sector packs should not fork the application.  
They should configure and extend the same core platform and modules.

---

## Layer D — Advisory Escalation
A specific service-integrated workflow layer.

### Responsibilities
- AI disclaimer/consent interactions
- advisor escalation triggers
- packaging case history for escalation
- sending case summary + selected documents
- signalling where human advice is recommended

### Architectural role
This becomes a commercial differentiator and should be treated as a first-class workflow capability.

---

## 4. Codebase interpretation

The current codebase remains a good fit for this direction.

### Current baseline
- Flask modular monolith
- blueprint-based route separation
- SQLAlchemy model layer
- server-rendered Jinja templates
- service-layer extraction pattern
- additive API-readiness work
- role-aware access model
- document generation already present

### Conclusion
The current architecture is still correct.  
The pivot is primarily about:
- product packaging
- domain framing
- modular enablement
- sector overlays
- workflow expansion

not a rewrite.

---

## 5. Recommended domain map

## Domain 1 — Platform Core
### Responsibilities
- auth
- users
- roles
- organisation settings
- branding/configuration
- module enablement
- template management
- AI warnings/acceptance
- advisor escalation settings
- API keys

---

## Domain 2 — People Core
### Responsibilities
- employee records
- lifecycle status
- manager assignment
- team/service assignment where needed
- employee notes/history
- leaver/reactivation handling

### Notes
This remains foundational across all sectors.

---

## Domain 3 — Workflow Modules
### Responsibilities
- probation
- supervision
- PIP / capability
- sickness
- investigation
- disciplinary
- grievance
- return-to-work
- related document workflows

### Notes
These should remain distinct enough to enable modular packaging.

---

## Domain 4 — Sector Configuration
### Responsibilities
- sector-specific labels
- templates
- compliance additions
- workflow guidance
- dashboard variants
- recommended settings

### Notes
Care should be the first pack built here.

---

## Domain 5 — Reporting & Insights
### Responsibilities
- dashboard metrics
- module-level reporting
- service/manager filters where relevant
- sector-pack widgets
- trend summaries
- future export/API summaries

---

## Domain 6 — Advisory Workflows
### Responsibilities
- AI suggestion requests
- warning banners and acceptance prompts
- escalate-to-advisor actions
- case packaging
- send-to-advisor workflows
- tracking escalation state

---

## 6. Blueprint direction

The current blueprint approach should remain.

### Existing/expected blueprints
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

### Rule
Do not rename existing blueprints unless explicitly requested.

### New design principle
Blueprints should continue to represent domains/modules, while sector packs should influence configuration, content, and presentation rather than becoming separate blueprint trees unless genuinely necessary.

---

## 7. Service-layer direction

The service layer becomes even more important under a module-first architecture.

### Service categories

#### Platform services
- permissions service
- organisation configuration service
- module enablement service
- branding/settings service

#### People services
- employee lifecycle service
- employee scoping service
- manager assignment helpers

#### Workflow services
- probation service
- supervision service
- PIP service
- sickness service
- ER case service

#### Sector services
- sector pack resolution/configuration service
- template selection service
- workflow defaults service

#### Advisory services
- AI guidance orchestration service
- disclaimer/consent recording service
- escalation packaging service
- advisor handoff service

#### Reporting services
- dashboard aggregation service
- module reporting service
- insights/summary service

### Rule
Routes should remain thin and coordinate service calls rather than carrying domain logic directly.

---

## 8. Data model implications

The current SQLAlchemy model approach remains appropriate.

### Existing models likely retained
- `User`
- `Employee`
- `PIPRecord`
- probation models
- sickness models
- employee relations models
- `TimelineEvent`
- document/draft entities

### New model categories likely required

#### Platform configuration
- `Organisation`
- `EnabledModule` or organisation module settings
- branding/settings records
- AI policy/disclaimer acknowledgement records
- API key records

#### Advisory workflow
- `AdvisorEscalation`
- `AdvisorEscalationDocument`
- AI request/acceptance tracking models if not already present

#### Sector configuration
- sector/pack setting model
- sector-specific template selection mapping
- sector-specific dashboard/widget config if needed later

#### Module expansion
- `SupervisionRecord`
- `ReturnToWorkRecord`
- further ER/dispute entities if the current schema does not already cover them cleanly

### Design principle
Sector-specific behaviour should usually come from configuration, templates, flags, and defaults rather than duplicating the whole data model by sector.

---

## 9. UI architecture implications

The frontend should remain server-rendered with Jinja.

### New UI framing
The UI should increasingly present:
- core workspace
- enabled modules
- advisor escalation options
- role-aware dashboards
- sector-aware labels/templates where configured

### Important UX implication
The platform should feel:
- modular
- configurable
- practical
- advisor-backed
- not locked to one sector unless a sector pack is active

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

This can still be shaped around enabled modules and permissions.

---

## 10. API direction

The API becomes even more strategically useful in this model.

### Immediate API role
- expose module data cleanly
- support integrations
- support future external workflow hooks
- support advisor escalation/event exchange if needed later

### Design principle
Expose platform and module domains through stable `/api/v1/` contracts, not sector-specific duplicated endpoints where avoidable.

### Recommended API groupings
- `/api/v1/employees`
- `/api/v1/probation`
- `/api/v1/pip`
- `/api/v1/sickness`
- `/api/v1/employee-relations`
- `/api/v1/supervision`
- `/api/v1/reporting`
- `/api/v1/advisor-escalations`

### Sector pack rule
Sector packs should change behaviour/configuration, not force separate API shapes unless there is a compelling reason.

---

## 11. Advisor escalation architecture

This is now strategically important enough to define directly.

## Core workflow
1. user works through a module/case
2. user requests AI guidance
3. system presents clear warning/disclaimer
4. user acknowledges AI is guidance only
5. user can trigger escalation to advisor
6. system packages relevant case history/documents
7. escalation is sent or queued for human review

## Required architecture concerns
- consent acknowledgement
- case summary generation
- selected-document packaging
- escalation status tracking
- audit trail
- secure permissions

### Strategic note
This workflow may become one of the strongest differentiators in the product.

---

## 12. Recommended implementation roadmap

## Phase 1 — Product reframing
- update product documentation
- reframe architecture around core/modules/packs
- rework navigation and UI wording
- introduce module-oriented dashboard structure

## Phase 2 — Module packaging foundation
- define module enablement rules
- organisation settings for enabled modules
- dashboard cards driven by enabled modules
- standardise module launch pages

## Phase 3 — Standard modules
- strengthen probation
- add/strengthen supervision
- strengthen PIP / capability

## Phase 4 — Add-on modules
- investigation
- disciplinary
- grievance
- sickness / return-to-work
- compliance if included at this stage

## Phase 5 — Care Pack
- care terminology
- care templates
- care workflow defaults
- care-specific reporting and compliance additions

## Phase 6 — Advisor escalation
- disclaimers
- acceptance capture
- push-to-advisor workflow
- escalation tracking

## Phase 7 — API and reporting expansion
- module endpoints
- reporting summaries
- integration surfaces

---

## 13. Non-goals for this phase

The following remain non-goals:
- full rewrite
- microservices migration
- SPA rebuild
- sector-specific codebase forks
- route renaming
- breaking blueprint reorganisation
- deep data-model replacement without migration path

The right pattern remains:
**preserve the modular monolith, expand it safely, and separate configuration from code duplication.**

---

## 14. Final architectural summary

The product should now be built as a **module-first HR operations platform** with:

- a shared core platform
- practical workflow modules
- optional add-on modules
- sector-specific packs starting with care
- advisor escalation workflows as a differentiator
- additive API-readiness

This preserves the strength of the current application while creating a broader and more commercially scalable product direction.
