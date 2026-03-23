from __future__ import annotations

from datetime import date, timedelta


def clamp_date_range(
    start: date | None,
    end: date | None,
    window_start: date,
    window_end: date,
):
    """Return overlap of [start, end] with [window_start, window_end].

    Returns:
        (clamped_start, clamped_end) if there is overlap
        (None, None) otherwise
    """
    if not start:
        return None, None

    real_end = end or window_end

    if real_end < window_start or start > window_end:
        return None, None

    clamped_start = max(start, window_start)
    clamped_end = min(real_end, window_end)

    if clamped_end < clamped_start:
        return None, None

    return clamped_start, clamped_end


def compute_sickness_trigger_metrics(
    q_cases,
    *,
    today: date,
    window_days: int = 365,
    bradford_medium: int = 200,
    bradford_high: int = 400,
    episodes_threshold: int = 3,
    total_days_threshold: int = 14,
    long_term_days: int = 28,
):
    """Compute rolling-window sickness trigger metrics per employee.

    This is extracted from the current app.py logic and kept behaviourally
    aligned with the existing dashboard/employee detail calculations.

    Episode definition (current Phase 3 approach):
        each SicknessCase == 1 episode

    Bradford:
        episodes^2 * total_days_within_window
    """
    from models import SicknessCase  # local import to avoid circulars during transition

    window_start = today - timedelta(days=window_days)
    window_end = today

    cases = (
        q_cases.filter(
            SicknessCase.start_date.isnot(None),
            SicknessCase.start_date <= window_end,
        )
        .all()
    )

    metrics_by_employee = {}

    for sc in cases:
        if not getattr(sc, "employee", None) or not getattr(sc, "start_date", None):
            continue

        clamped_start, clamped_end = clamp_date_range(
            sc.start_date,
            sc.end_date,
            window_start,
            window_end,
        )
        if not clamped_start:
            continue

        days = (clamped_end - clamped_start).days + 1
        if days <= 0:
            continue

        data = metrics_by_employee.setdefault(
            sc.employee.id,
            {
                "employee": sc.employee,
                "episodes": 0,
                "total_days": 0,
                "has_long_term": False,
                "longest_spell_days": 0,
            },
        )

        data["episodes"] += 1
        data["total_days"] += days
        data["longest_spell_days"] = max(data["longest_spell_days"], days)

        if days >= long_term_days:
            data["has_long_term"] = True

    potential_triggers = []

    for data in metrics_by_employee.values():
        employee = data["employee"]
        episodes = data["episodes"]
        total_days = data["total_days"]
        has_long_term = data["has_long_term"]
        longest_spell_days = data["longest_spell_days"]

        bradford = (episodes * episodes * total_days) if total_days > 0 else 0

        flags = []
        actions = []

        if episodes >= episodes_threshold:
            flags.append(f"Episodes ≥ {episodes_threshold} in 12 months")
            actions.append("Review absence pattern and agree next steps (informal stage).")

        if total_days >= total_days_threshold:
            flags.append(f"≥ {total_days_threshold} days total in 12 months")
            actions.append("Check fit note / evidence and update absence records.")

        if has_long_term:
            flags.append(f"Long-term case (≥ {long_term_days} days)")
            actions.append("Consider OH referral and a welfare meeting plan.")

        severity = "none"
        if bradford >= bradford_high:
            flags.append(f"Bradford ≥ {bradford_high}")
            severity = "high"
            actions.append("Consider formal sickness stage (policy dependent) and document rationale.")
        elif bradford >= bradford_medium:
            flags.append(f"Bradford ≥ {bradford_medium}")
            severity = "medium"
            actions.append("Book an absence review and set review checkpoints.")
        elif flags:
            severity = "low"
            actions.append("Keep monitoring; ensure RTW notes are complete.")

        if not flags:
            continue

        seen = set()
        actions_unique = []
        for action in actions:
            if action not in seen:
                seen.add(action)
                actions_unique.append(action)

        potential_triggers.append(
            {
                "employee": employee,
                "episodes": episodes,
                "total_days": total_days,
                "bradford": bradford,
                "has_long_term": has_long_term,
                "longest_spell_days": longest_spell_days,
                "flags_label": ", ".join(flags),
                "severity": severity,
                "actions": actions_unique,
            }
        )

    severity_rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
    potential_triggers.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 0),
            item["bradford"],
            item["episodes"],
        ),
        reverse=True,
    )

    return potential_triggers