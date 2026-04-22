import re

from models import Organisation, OrganisationModuleSetting, db

DEFAULT_ORGANISATION_NAME = "Default Organisation"
DEFAULT_ORGANISATION_SLUG = "default-organisation"

DEFAULT_MODULE_KEYS = [
    "pip",
    "probation",
    "sickness",
    "employee_relations",
]

DEFAULT_MODULE_LABELS = [
    ("pip", "Performance Improvement Plans"),
    ("probation", "Probation"),
    ("sickness", "Sickness"),
    ("employee_relations", "Employee Relations"),
]

DEFAULT_MODULE_SETTINGS = {
    "pip": {
        "is_enabled": True,
        "ai_enabled": True,
        "escalation_enabled": True,
    },
    "probation": {
        "is_enabled": True,
        "ai_enabled": True,
        "escalation_enabled": False,
    },
    "sickness": {
        "is_enabled": True,
        "ai_enabled": False,
        "escalation_enabled": False,
    },
    "employee_relations": {
        "is_enabled": True,
        "ai_enabled": True,
        "escalation_enabled": True,
    },
}


def slugify_organisation_name(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "organisation"


def build_unique_organisation_slug(name, exclude_org_id=None):
    base_slug = slugify_organisation_name(name)
    candidate = base_slug
    suffix = 2

    while True:
        query = Organisation.query.filter_by(slug=candidate)
        if exclude_org_id is not None:
            query = query.filter(Organisation.id != exclude_org_id)

        existing = query.first()
        if existing is None:
            return candidate

        candidate = f"{base_slug}-{suffix}"
        suffix += 1


def bootstrap_organisation_defaults(organisation):
    changed = False

    if not organisation.name:
        organisation.name = DEFAULT_ORGANISATION_NAME
        changed = True

    if not getattr(organisation, "slug", None):
        organisation.slug = build_unique_organisation_slug(
            organisation.name or DEFAULT_ORGANISATION_NAME,
            exclude_org_id=organisation.id,
        )
        changed = True

    if getattr(organisation, "is_active", None) is None:
        organisation.is_active = True
        changed = True

    existing_settings = {
        row.module_key: row
        for row in OrganisationModuleSetting.query.filter_by(
            organisation_id=organisation.id
        ).all()
    }

    created_any = False

    for module_key in DEFAULT_MODULE_KEYS:
        defaults = DEFAULT_MODULE_SETTINGS.get(
            module_key,
            {
                "is_enabled": True,
                "ai_enabled": True,
                "escalation_enabled": True,
            },
        )

        row = existing_settings.get(module_key)
        if row is None:
            db.session.add(
                OrganisationModuleSetting(
                    organisation_id=organisation.id,
                    module_key=module_key,
                    is_enabled=defaults["is_enabled"],
                    ai_enabled=defaults["ai_enabled"],
                    escalation_enabled=defaults["escalation_enabled"],
                )
            )
            created_any = True
            continue

        row_changed = False

        if getattr(row, "is_enabled", None) is None:
            row.is_enabled = defaults["is_enabled"]
            row_changed = True

        if getattr(row, "ai_enabled", None) is None:
            row.ai_enabled = defaults["ai_enabled"]
            row_changed = True

        if getattr(row, "escalation_enabled", None) is None:
            row.escalation_enabled = defaults["escalation_enabled"]
            row_changed = True

        if row_changed:
            changed = True

    if changed or created_any:
        db.session.commit()

    return organisation


def get_default_organisation():
    org = Organisation.query.order_by(Organisation.id.asc()).first()
    if org:
        return bootstrap_organisation_defaults(org)

    org = Organisation(
        name=DEFAULT_ORGANISATION_NAME,
        slug=DEFAULT_ORGANISATION_SLUG,
        is_active=True,
    )
    db.session.add(org)
    db.session.commit()

    return bootstrap_organisation_defaults(org)


def get_organisation_for_user(user=None, allow_default_fallback=True):
    if user is None:
        return get_default_organisation() if allow_default_fallback else None

    organisation = getattr(user, "organisation", None)
    if organisation is not None:
        return bootstrap_organisation_defaults(organisation)

    organisation_id = getattr(user, "organisation_id", None)
    if organisation_id:
        organisation = db.session.get(Organisation, organisation_id)
        if organisation is not None:
            return bootstrap_organisation_defaults(organisation)

    return get_default_organisation() if allow_default_fallback else None


def resolve_organisation(organisation=None, user=None, allow_default_fallback=True):
    if organisation is not None:
        return bootstrap_organisation_defaults(organisation)

    return get_organisation_for_user(
        user=user,
        allow_default_fallback=allow_default_fallback,
    )


def ensure_module_settings_for_org(organisation=None, user=None):
    org = resolve_organisation(
        organisation=organisation,
        user=user,
        allow_default_fallback=True,
    )
    return bootstrap_organisation_defaults(org)


def ensure_default_module_settings():
    return ensure_module_settings_for_org()


def get_enabled_modules(organisation=None, user=None):
    org = ensure_module_settings_for_org(organisation=organisation, user=user)

    settings = {
        row.module_key: bool(row.is_enabled)
        for row in OrganisationModuleSetting.query.filter_by(
            organisation_id=org.id
        ).all()
    }

    for module_key in DEFAULT_MODULE_KEYS:
        defaults = DEFAULT_MODULE_SETTINGS.get(module_key, {})
        settings.setdefault(module_key, bool(defaults.get("is_enabled", True)))

    return settings


def get_module_settings_for_org(organisation=None, user=None):
    org = ensure_module_settings_for_org(organisation=organisation, user=user)
    settings = {
        row.module_key: row
        for row in OrganisationModuleSetting.query.filter_by(
            organisation_id=org.id
        ).all()
    }
    return org, settings


def get_module_controls(organisation=None, user=None):
    org = ensure_module_settings_for_org(organisation=organisation, user=user)
    controls = {}

    for row in OrganisationModuleSetting.query.filter_by(organisation_id=org.id).all():
        controls[row.module_key] = {
            "is_enabled": bool(row.is_enabled),
            "ai_enabled": bool(getattr(row, "ai_enabled", True)),
            "escalation_enabled": bool(getattr(row, "escalation_enabled", True)),
        }

    for module_key in DEFAULT_MODULE_KEYS:
        defaults = DEFAULT_MODULE_SETTINGS.get(
            module_key,
            {
                "is_enabled": True,
                "ai_enabled": True,
                "escalation_enabled": True,
            },
        )
        controls.setdefault(
            module_key,
            {
                "is_enabled": bool(defaults["is_enabled"]),
                "ai_enabled": bool(defaults["ai_enabled"]),
                "escalation_enabled": bool(defaults["escalation_enabled"]),
            },
        )

    return controls
