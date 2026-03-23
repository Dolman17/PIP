import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _safe_text(value):
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _join_items(values):
    cleaned = [str(v).strip() for v in values if v and str(v).strip()]
    return ", ".join(cleaned) if cleaned else "—"


def build_employee_relations_prompt(er_case, active_policy_text=None):
    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}".strip()
    employee_job_title = _safe_text(getattr(er_case.employee, "job_title", None))
    employee_service = _safe_text(getattr(er_case.employee, "service", None))

    recent_meetings = []
    for meeting in (er_case.meetings or [])[:5]:
        recent_meetings.append(
            "\n".join(
                [
                    f"Meeting Type: {_safe_text(meeting.meeting_type)}",
                    f"Meeting Date/Time: {_safe_text(meeting.meeting_datetime)}",
                    f"Location: {_safe_text(meeting.location)}",
                    f"Attendees: {_safe_text(meeting.attendees)}",
                    f"Notes: {_safe_text(meeting.notes)}",
                    f"Adjournment Notes: {_safe_text(meeting.adjournment_notes)}",
                    f"Outcome Summary: {_safe_text(meeting.outcome_summary)}",
                ]
            )
        )

    recent_timeline = []
    for event in (er_case.timeline_events or [])[:10]:
        recent_timeline.append(
            "\n".join(
                [
                    f"Timestamp: {_safe_text(event.timestamp)}",
                    f"Event Type: {_safe_text(event.event_type)}",
                    f"Notes: {_safe_text(event.notes)}",
                    f"Updated By: {_safe_text(event.updated_by)}",
                ]
            )
        )

    policy_text = _safe_text(active_policy_text)

    system_prompt = """
You are an expert UK HR Employee Relations advisor.

Your task is to provide practical, policy-aware guidance for an internal HR case.
You are supporting HR professionals and managers with structured advice, not giving legal advice.

Rules:
- Be balanced, fair, and neutral.
- Do not assume guilt or wrongdoing.
- Base advice on the case details provided.
- Where policy text is provided, use it as the primary internal standard.
- If information is missing, explicitly say what is missing.
- Avoid unnecessary repetition.
- Do not include special category personal data unless directly relevant.
- Do not make up policy wording that is not supported by the provided policy text.
- Keep the advice practical and operational.

Return the answer using these exact section headings:

1. Overall Risk View
2. Immediate Next Steps
3. Investigation Questions
4. Hearing Questions
5. Outcome / Sanction Guidance
6. Fairness & Process Checks
7. Suggested Wording for HR / Manager
8. Missing Information

Under each section, use short bullet points.
""".strip()

    user_prompt = f"""
CASE OVERVIEW
Case ID: {_safe_text(er_case.id)}
Case Type: {_safe_text(er_case.case_type)}
Title: {_safe_text(er_case.title)}
Status: {_safe_text(er_case.status)}
Stage: {_safe_text(er_case.stage)}
Priority: {_safe_text(er_case.priority_level)}
Policy Type: {_safe_text(er_case.policy_type)}
Date Raised: {_safe_text(er_case.date_raised)}
Raised By: {_safe_text(er_case.raised_by)}

EMPLOYEE
Name: {_safe_text(employee_name)}
Job Title: {employee_job_title}
Service: {employee_service}
Service Area: {_safe_text(er_case.service_area)}
Department: {_safe_text(er_case.department)}

ALLEGATION / GRIEVANCE
Summary: {_safe_text(er_case.summary)}
Allegation or Grievance: {_safe_text(er_case.allegation_or_grievance)}

DISCIPLINARY / GRIEVANCE DETAILS
Disciplinary Category: {_safe_text(er_case.disciplinary_category)}
Grievance Category: {_safe_text(er_case.grievance_category)}
Gross Misconduct Flag: {_safe_text(er_case.gross_misconduct_flag)}
Misconduct Date: {_safe_text(er_case.misconduct_date)}
Suspension Flag: {_safe_text(er_case.suspension_flag)}
Suspension With Pay: {_safe_text(er_case.suspension_with_pay)}
Previous Warnings Summary: {_safe_text(er_case.previous_warnings_summary)}
Recommended Sanction: {_safe_text(er_case.recommended_sanction)}
Final Sanction: {_safe_text(er_case.final_sanction)}
Warning Level: {_safe_text(er_case.warning_level)}
Warning Review Date: {_safe_text(er_case.warning_review_date)}
Warning Expiry Date: {_safe_text(er_case.warning_expiry_date)}
Person Complained About: {_safe_text(er_case.person_complained_about)}
Bullying Flag: {_safe_text(er_case.bullying_flag)}
Harassment Flag: {_safe_text(er_case.harassment_flag)}
Discrimination Flag: {_safe_text(er_case.discrimination_flag)}
Requested Resolution: {_safe_text(er_case.requested_resolution)}
Mediation Considered: {_safe_text(er_case.mediation_considered)}
Grievance Outcome: {_safe_text(er_case.grievance_outcome)}

INVESTIGATION / APPEAL
Investigation Scope: {_safe_text(er_case.investigation_scope)}
Investigation Findings: {_safe_text(er_case.investigation_findings)}
Recommended Next Step: {_safe_text(er_case.recommended_next_step)}
Appeal Requested: {_safe_text(er_case.appeal_requested_flag)}
Appeal Request Date: {_safe_text(er_case.appeal_request_date)}
Appeal Reason: {_safe_text(er_case.appeal_reason)}
Appeal Hearing Date: {_safe_text(er_case.appeal_hearing_date)}
Appeal Outcome: {_safe_text(er_case.appeal_outcome)}
Appeal Outcome Date: {_safe_text(er_case.appeal_outcome_date)}

DATES / OWNERS
Next Action Date: {_safe_text(er_case.next_action_date)}
Investigation Deadline: {_safe_text(er_case.investigation_deadline)}
Hearing Date: {_safe_text(er_case.hearing_date)}
Outcome Due Date: {_safe_text(er_case.outcome_due_date)}
Appeal Deadline: {_safe_text(er_case.appeal_deadline)}
Date Closed: {_safe_text(er_case.date_closed)}
HR Lead: {_safe_text(er_case.hr_lead)}
Investigating Manager: {_safe_text(er_case.investigating_manager)}
Hearing Chair: {_safe_text(er_case.hearing_chair)}
Note Taker: {_safe_text(er_case.note_taker)}
Appeal Manager: {_safe_text(er_case.appeal_manager)}

RECENT MEETINGS
{chr(10).join(recent_meetings) if recent_meetings else "—"}

RECENT TIMELINE
{chr(10).join(recent_timeline) if recent_timeline else "—"}

ACTIVE POLICY TEXT
{policy_text}
""".strip()

    return system_prompt, user_prompt


def generate_employee_relations_advice(er_case, active_policy_text=None):
    system_prompt, user_prompt = build_employee_relations_prompt(
        er_case=er_case,
        active_policy_text=active_policy_text,
    )

    response = client.chat.completions.create(
        model=DEFAULT_OPENAI_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content.strip()