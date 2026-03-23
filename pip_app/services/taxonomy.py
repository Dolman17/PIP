from __future__ import annotations

CURATED_TAGS = {
    "Timekeeping": ["lateness", "missed clock-in", "extended breaks", "early finish", "timekeeping policy"],
    "Attendance": ["unauthorised absence", "short notice absence", "patterns of absence", "fit note", "return to work"],
    "Quality of Work": ["accuracy", "attention to detail", "rework", "documentation", "SOP adherence"],
    "Productivity": ["missed deadlines", "slow throughput", "low output", "prioritisation", "time management"],
    "Conduct": ["inappropriate language", "unprofessional behaviour", "non-compliance", "policy breach", "conflict"],
    "Communication": ["tone", "late replies", "stakeholder updates", "handover quality", "listening"],
    "Teamwork/Collaboration": ["handover gaps", "knowledge sharing", "supporting peers", "collaboration tools"],
    "Compliance/Process": ["data entry errors", "checklist missed", "audit finding", "process deviation"],
    "Customer Service": ["response times", "complaint handling", "service standards", "follow-up"],
    "Health & Safety": ["PPE", "risk assessment", "manual handling", "incident reporting"],
}

ACTION_TEMPLATES = {
    "Timekeeping": {
        "Low": [
            "Agree start-time target and grace window",
            "Daily check-in for 2 weeks at start of shift",
            "Keep punctuality log; review weekly",
        ],
        "Moderate": [
            "Formal punctuality target with variance log",
            "Escalate if 2+ breaches in a week",
            "Buddy assigned for morning routine",
        ],
        "High": [
            "Issue written reminder citing policy",
            "Daily manager sign-off for 3 weeks",
            "Escalation to formal stage if breaches continue",
        ],
        "_default": [
            "Agree punctuality expectations",
            "Daily check-in for first 2 weeks",
            "Weekly review of log",
        ],
    },
    "Performance": {
        "Low": [
            "Break down tasks into weekly milestones",
            "Mid-week check-in with progress update",
            "Share example of quality standard",
        ],
        "Moderate": [
            "Set SMART targets per task",
            "Stand-up updates Mon/Wed/Fri",
            "Peer review before handoff",
        ],
        "High": [
            "Written performance targets with deadlines",
            "Daily status update for 10 working days",
            "Escalate to formal PIP stage if no improvement",
        ],
        "_default": [
            "Agree 2–3 SMART targets",
            "Weekly progress review",
            "Identify training/module to close gap",
        ],
    },
    "Conduct": {
        "_default": [
            "Reference conduct policy and expectations",
            "Agree behaviour standards; confirm by email",
            "Book values refresher session",
        ]
    },
    "Attendance": {
        "_default": [
            "Follow reporting procedure for absence",
            "Return-to-work meeting after each absence",
            "Pattern review after 4 weeks",
        ]
    },
    "Communication": {
        "_default": [
            "Acknowledge messages within agreed SLA",
            "Use agreed update template for stakeholders",
            "Add handover note at end of shift",
        ]
    },
    "Quality of Work": {
        "_default": [
            "Introduce checklist for critical steps",
            "Peer review for first 4 weeks",
            "Log defects and agree prevention steps",
        ]
    },
    "Productivity": {
        "_default": [
            "Time-block key tasks; share plan daily",
            "Weekly throughput targets",
            "Remove low-value tasks with manager",
        ]
    },
}


def merge_curated_and_recent(category: str, recent_tags: list[str], cap: int = 30) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for tag in CURATED_TAGS.get(category, []):
        key = tag.lower()
        if key not in seen:
            out.append(tag)
            seen.add(key)

    for tag in recent_tags:
        if not tag:
            continue
        clean = tag.strip()
        key = clean.lower()
        if key and key not in seen:
            out.append(clean)
            seen.add(key)
        if len(out) >= cap:
            break

    return out


def pick_actions_from_templates(category: str, severity: str) -> list[str]:
    cat = (category or "").strip()
    sev = (severity or "").strip()

    block = ACTION_TEMPLATES.get(cat) or {}
    if not block:
        block = {
            "_default": [
                "Agree clear targets",
                "Weekly review",
                "Training / buddy support as needed",
            ]
        }

    if sev in block and block[sev]:
        return block[sev]

    if block.get("_default"):
        return block["_default"]

    for value in block.values():
        if isinstance(value, list) and value:
            return value

    return []