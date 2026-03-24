import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

DEFAULT_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _safe_text(value):
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def build_employee_relations_prompt(er_case, active_policy_text=None):
    employee_name = f"{er_case.employee.first_name} {er_case.employee.last_name}".strip()

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

You are supporting HR professionals and managers with practical internal guidance.
You are not providing legal advice.

Rules:
- Be balanced, fair, neutral, and policy-aware.
- Do not assume guilt or wrongdoing.
- Base the advice on the facts supplied.
- If policy text is supplied, treat it as the primary internal standard.
- If key information is missing, state that clearly.
- Avoid unnecessary repetition.
- Do not invent policy wording.
- Keep the advice operational and useful.

You must return valid JSON only.
Do not include markdown.
Do not include code fences.
Do not include any text before or after the JSON.

Return exactly this JSON structure:
{
  "overall_risk_view": "string",
  "immediate_next_steps": "string",
  "investigation_questions": "string",
  "hearing_questions": "string",
  "outcome_sanction_guidance": "string",
  "fairness_process_checks": "string",
  "suggested_wording": "string",
  "missing_information": "string"
}

Each field should contain concise but useful bullet-style plain text using hyphens.
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
Job Title: {_safe_text(getattr(er_case.employee, "job_title", None))}
Service: {_safe_text(getattr(er_case.employee, "service", None))}
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
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_content = response.choices[0].message.content.strip()
    parsed = json.loads(raw_content)

    return {
        "model_name": DEFAULT_OPENAI_MODEL,
        "raw_response": raw_content,
        "overall_risk_view": parsed.get("overall_risk_view", "").strip(),
        "immediate_next_steps": parsed.get("immediate_next_steps", "").strip(),
        "investigation_questions": parsed.get("investigation_questions", "").strip(),
        "hearing_questions": parsed.get("hearing_questions", "").strip(),
        "outcome_sanction_guidance": parsed.get("outcome_sanction_guidance", "").strip(),
        "fairness_process_checks": parsed.get("fairness_process_checks", "").strip(),
        "suggested_wording": parsed.get("suggested_wording", "").strip(),
        "missing_information": parsed.get("missing_information", "").strip(),
    }


def render_employee_relations_advice_for_timeline(advice_data):
    sections = [
        ("Overall Risk View", advice_data.get("overall_risk_view")),
        ("Immediate Next Steps", advice_data.get("immediate_next_steps")),
        ("Investigation Questions", advice_data.get("investigation_questions")),
        ("Hearing Questions", advice_data.get("hearing_questions")),
        ("Outcome / Sanction Guidance", advice_data.get("outcome_sanction_guidance")),
        ("Fairness & Process Checks", advice_data.get("fairness_process_checks")),
        ("Suggested Wording for HR / Manager", advice_data.get("suggested_wording")),
        ("Missing Information", advice_data.get("missing_information")),
    ]

    lines = ["Employee Relations AI Advice", ""]

    for heading, content in sections:
        lines.append(heading)
        lines.append(content.strip() if content else "—")
        lines.append("")

    return "\n".join(lines).strip()
