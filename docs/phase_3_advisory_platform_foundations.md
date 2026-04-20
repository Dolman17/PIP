# Phase 3: Advisory Platform Foundations

## Overview
This phase focuses on transforming the current application into a **commercially viable, modular HR platform** by introducing:

- Organisation-level configuration
- Module enablement
- Advisor escalation workflows
- Standardised AI governance
- Admin control surfaces
- Platform hardening

---

## Phase Goal
Create a configurable, advisor-backed HR platform core **without breaking existing routes or functionality**.

---

## Success Criteria
By the end of this phase, the platform should support:

- Organisation-level settings
- Module enablement per organisation
- Consistent AI consent & governance
- Advisor escalation from key modules
- Admin controls for AI and escalation
- Audit/reporting for AI and escalations

---

## Epics

### Epic 1 — Organisation & Platform Configuration
**Objective:** Build the shared control layer above modules.

**Key Features:**
- Organisation model
- Module enable/disable
- AI policy configuration
- Advisor escalation settings
- Branding defaults

---

### Epic 2 — Advisor Escalation MVP
**Objective:** Introduce core differentiator.

**Initial Modules:**
- PIP
- Employee Relations

**Key Features:**
- Escalation model
- Case summary packaging
- Document attachments
- Status tracking
- Advisor queue
- Timeline logging

**Statuses:**
- draft
- submitted
- acknowledged
- in_review
- closed
- cancelled

---

### Epic 3 — AI Governance Standardisation
**Objective:** Make AI behaviour consistent across modules.

**Key Features:**
- Shared consent service
- Standard warning UI
- Unified logging
- Admin audit view

---

### Epic 4 — Governance Admin Controls
**Objective:** Provide control surfaces.

**Key Features:**
- AI toggles per module
- Escalation routing
- Consent text management
- Audit dashboards

---

### Epic 5 — Platform Hardening
**Objective:** Improve deployment and repo quality.

**Key Tasks:**
- Clean repo (remove .venv, DB, uploads)
- Align deployment entrypoint
- Document setup
- Production readiness checklist

---

## Data Models

### Organisation
- id, name, slug, is_active
- branding fields
- sector pack
- timestamps

### OrganisationModuleSetting
- organisation_id
- module_key
- is_enabled
- ai_enabled
- escalation_enabled

### AIConfiguration
- organisation_id
- module_key
- consent_required
- warning_text
- version

### AdvisorEscalation
- module_key
- source_record_type/id
- submitted_by
- assigned_to
- status
- summary
- timestamps

### AdvisorEscalationDocument
- escalation_id
- file reference
- metadata

---

## Implementation Plan

### Sprint 1 — Platform Foundations
- Organisation model
- Module settings
- Admin UI
- Module visibility logic

### Sprint 2 — Escalation (PIP)
- Escalation models
- PIP escalation UI
- Admin queue
- Timeline logging

### Sprint 3 — Escalation (ER)
- Extend to Employee Relations
- Document selection
- Queue filtering

### Sprint 4 — AI Standardisation
- Shared AI service
- Warning templates
- Unified logging

### Sprint 5 — Governance & Reporting
- AI dashboard
- Escalation dashboard
- Filters & controls

### Sprint 6 — Hardening
- Repo cleanup
- Deployment alignment
- Documentation

---

## Strategic Outcome

This phase enables the product to be positioned as:

**"A modular HR workflow platform with governed AI and advisor escalation."**

---

## Next Phases (After Phase 3)

1. Reporting & dashboards expansion  
2. Supervision module  
3. Compliance module  
4. Care sector pack  
5. API & integrations  

---

## Key Principle

**Do not add more modules until the platform layer is complete.**
