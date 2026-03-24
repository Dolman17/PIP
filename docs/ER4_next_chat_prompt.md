# PIP CRM — New Chat Handoff Prompt (Post ER AI + Document-Type Prefills)

Use this as the starting prompt in the next chat.

---

You are helping continue development of my **PIP CRM** Flask app.

## Working style rules
These are important and must be followed:
- Do **not** rename, remove, or alter existing routes/endpoints unless I explicitly approve that route change first.
- Do **not** rename templates, models, or field names unless I explicitly ask.
- Treat existing routes and endpoint names as stable contracts.
- If a proposed change is major, risky, breaking, or could potentially break existing functionality, warn me first before proceeding.
- I prefer **full pasteover code**, not snippets.
- Keep all original routes intact.
- Do not remove unrelated functionality when refactoring.
- Practical, low-risk, incremental changes are preferred.

## Current project baseline
This is the **PIP CRM** app with a hybrid blueprint + services architecture:
- `app.py` is now a smaller bootstrap shell.
- feature routes live in `pip_app/blueprints/`
- shared logic lives in `pip_app/services/`
- canonical models live in `pip_app/models.py`
- root `models.py` is compatibility-oriented
- Employee Relations is now a live module

## Current modules implemented
- Authentication
- Dashboard
- Employee management
- PIP module
- Probation module
- Sickness module
- Employee Relations module
- Admin module

## Employee Relations current state
Employee Relations is now implemented through:
- ER dashboard
- ER case list
- ER case detail
- ER create/edit case
- ER meetings
- ER attachments upload/download
- ER policy text save/link workflow
- ER structured AI advice generation
- ER timeline logging
- ER documents create/edit/finalise/download
- ER AI-aware document draft prefills
- exact document-type-specific ER draft prefills

### ER access model
- superuser only

### ER case types
- Disciplinary
- Grievance
- Investigation

### ER document types currently in constants
- Investigation Invite
- Suspension Confirmation
- Disciplinary Hearing Invite
- Disciplinary Outcome Letter
- Warning Letter
- Dismissal Letter
- Grievance Meeting Invite
- Grievance Outcome Letter
- Appeal Invite
- Appeal Outcome Letter
- Witness Statement Template
- Meeting Notes Template

## ER models currently in place
- `EmployeeRelationsCase`
- `EmployeeRelationsTimelineEvent`
- `EmployeeRelationsMeeting`
- `EmployeeRelationsAttachment`
- `EmployeeRelationsPolicyText`
- `EmployeeRelationsAIAdvice`
- `EmployeeRelationsDocument`

## ER AI architecture currently in place
### In `pip_app/services/ai_utils.py`
Implemented:
- OpenAI client setup
- ER AI prompt builder
- strict JSON response handling
- parsed structured advice output
- timeline render helper for readable mirror text

### Structured ER AI fields currently stored
- overall risk view
- immediate next steps
- investigation questions
- hearing questions
- outcome / sanction guidance
- fairness / process checks
- suggested wording
- missing information
- raw response
- model name

### In `pip_app/blueprints/employee_relations.py`
Implemented:
- `/cases/<id>/policy-texts/add`
- `/cases/<id>/ai-advice/generate`
- AI advice saved to `EmployeeRelationsAIAdvice`
- timeline mirror still created
- document drafts now prefill from latest structured AI advice
- exact ER document type mapping now controls which AI sections are used in the draft

## ER UI current state
### `templates/employee_relations/detail.html`
Implemented:
- policy text form
- active policy display
- policy history table
- generate ER AI advice button
- structured latest AI advice card pulling from `er_case.ai_advice_records[0]`
- documents section
- meetings section
- attachments section
- timeline section

## Attached baseline docs for this next chat
Use these as the canonical summary files:
- `architecturev4.md`
- `app_scopev4.md`

## Current likely next step
The next best phase is **Employee Relations document workflow refinement**.

Recommended next options:
1. add user choice between:
   - plain draft
   - AI-prefilled draft
2. improve the exact document-type draft layouts even further
3. possibly add policy file extraction into ER policy text records later
4. optionally add “use latest AI advice” indicators or controls in the ER document flow UI

## Important current state summary
At the current baseline:
- ER AI works
- ER structured advice storage works
- ER structured advice rendering works
- ER AI-aware document prefills work
- exact ER document-type mapping works
- current system is stable and should be built on incrementally

Start from this baseline and continue development without breaking existing routes or naming.
