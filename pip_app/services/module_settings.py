from models import Organisation, OrganisationModuleSetting, db

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


def get_default_organisation():
    org = Organisation.query.order_by(Organisation.id.asc()).first()
    if org:
        return org

    org = Organisation(name="Default Organisation")
    db.session.add(org)
    db.session.commit()
    return org


def get_organisation_for_user(user=None, allow_default_fallback=True):
    if user is None:
        return get_default_organisation() if allow_default_fallback else None

    organisation = getattr(user, "organisation", None)
    if organisation is not None:
        return organisation

    organisation_id = getattr(user, "organisation_id", None)
    if organisation_id:
        organisation = db.session.get(Organisation, organisation_id)
        if organisation is not None:
            return organisation

    return get_default_organisation() if allow_default_fallback else None


def resolve_organisation(organisation=None, user=None, allow_default_fallback=True):
    if organisation is not None:
        return organisation
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

    existing_settings = {
        row.module_key: row
        for row in OrganisationModuleSetting.query.filter_by(organisation_id=org.id).all()
    }

    created_any = False
    for module_key in DEFAULT_MODULE_KEYS:
        if module_key not in existing_settings:
            db.session.add(
                OrganisationModuleSetting(
                    organisation_id=org.id,
                    module_key=module_key,
                    is_enabled=True,
                )
            )
            created_any = True

    if created_any:
        db.session.commit()

    return org


def ensure_default_module_settings():
    return ensure_module_settings_for_org()


def get_enabled_modules(organisation=None, user=None):
    org = ensure_module_settings_for_org(organisation=organisation, user=user)

    settings = {
        row.module_key: bool(row.is_enabled)
        for row in OrganisationModuleSetting.query.filter_by(organisation_id=org.id).all()
    }

    for module_key in DEFAULT_MODULE_KEYS:
        settings.setdefault(module_key, True)

    return settings


def get_module_settings_for_org(organisation=None, user=None):
    org = ensure_module_settings_for_org(organisation=organisation, user=user)
    settings = {
        row.module_key: row
        for row in OrganisationModuleSetting.query.filter_by(organisation_id=org.id).all()
    }
    return org, settings
