# GitHub Projects Mapping — Phase 3 Advisory Platform Foundations

## Recommended project setup

Create a GitHub Project with these columns:

1. Backlog
2. Sprint 1 — Platform Foundations
3. Sprint 2 — Escalation MVP (PIP)
4. Sprint 3 — Escalation (ER)
5. Sprint 4 — AI Standardisation
6. Sprint 5 — Governance & Reporting
7. Sprint 6 — Platform Hardening
8. Done

## Import approach

Use the CSV file to bulk-create issues, then assign them into the matching sprint view or project iteration.

### Suggested labels
- `phase-3`
- `platform`
- `escalation`
- `ai-governance`
- `governance`
- `hardening`
- `sprint-1` to `sprint-6`
- `pip`
- `employee-relations`
- `admin`
- `backend`
- `ui`
- `audit`
- `reporting`
- `docs`
- `ops`

## Suggested custom fields in GitHub Projects

- **Sprint**: Sprint 1, Sprint 2, Sprint 3, Sprint 4, Sprint 5, Sprint 6
- **Area**: Platform, Escalation, AI Governance, Governance, Hardening
- **Status**: Backlog, Ready, In Progress, Blocked, Review, Done
- **Priority**: High, Medium, Low

## Recommended first import order

Start by creating the Sprint 1 items:
- Create Organisation model
- Create OrganisationModuleSetting model
- Run migration and seed default org
- Build module enablement helper
- Add admin settings page for module toggles
- Hide disabled modules from dashboard
- Hide disabled modules from navigation

## Practical note

GitHub Projects import formats can vary slightly depending on whether you are importing issues into the repo first or into a project workflow. This CSV is structured to be a clean issue-import base. After import, apply the project fields and move cards into the matching sprint columns.
