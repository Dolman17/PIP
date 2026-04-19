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


def ensure_default_module_settings():
    org = get_default_organisation()

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


def get_enabled_modules():
    org = ensure_default_module_settings()

    settings = {
        row.module_key: bool(row.is_enabled)
        for row in OrganisationModuleSetting.query.filter_by(organisation_id=org.id).all()
    }

    for module_key in DEFAULT_MODULE_KEYS:
        settings.setdefault(module_key, True)

    return settings


def get_module_settings_for_org():
    org = ensure_default_module_settings()
    settings = {
        row.module_key: row
        for row in OrganisationModuleSetting.query.filter_by(organisation_id=org.id).all()
    }
    return org, settings
