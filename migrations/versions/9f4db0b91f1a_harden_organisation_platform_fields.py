"""harden organisation platform fields

Revision ID: 9f4db0b91f1a
Revises: db0bdb053a0c
Create Date: 2026-04-22

"""

from alembic import op
import sqlalchemy as sa
import re


# revision identifiers, used by Alembic.
revision = "9f4db0b91f1a"
down_revision = "02d6340e42da"
branch_labels = None
depends_on = None


def _slugify(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "organisation"


def upgrade():
    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("primary_colour", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("secondary_colour", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("logo_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("font_family", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("sector_pack", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    bind = op.get_bind()
    metadata = sa.MetaData()

    organisations = sa.Table(
        "organisations",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=255)),
        sa.Column("slug", sa.String(length=255)),
        sa.Column("is_active", sa.Boolean),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )

    rows = bind.execute(
        sa.select(
            organisations.c.id,
            organisations.c.name,
            organisations.c.slug,
            organisations.c.created_at,
            organisations.c.updated_at,
        ).order_by(organisations.c.id.asc())
    ).fetchall()

    used_slugs = set()

    for row in rows:
        raw_slug = row.slug or _slugify(row.name or "organisation")
        candidate = raw_slug
        suffix = 2

        while candidate in used_slugs:
            candidate = f"{raw_slug}-{suffix}"
            suffix += 1

        used_slugs.add(candidate)

        bind.execute(
            organisations.update()
            .where(organisations.c.id == row.id)
            .values(
                slug=candidate,
                is_active=True,
                updated_at=row.updated_at or row.created_at,
            )
        )

    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.alter_column("slug", existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column("is_active", existing_type=sa.Boolean(), nullable=False)
        batch_op.create_index("ix_organisations_slug", ["slug"], unique=True)

    with op.batch_alter_table("organisation_module_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "ai_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "escalation_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

    with op.batch_alter_table("organisation_module_settings", schema=None) as batch_op:
        batch_op.alter_column("ai_enabled", server_default=None)
        batch_op.alter_column("escalation_enabled", server_default=None)


def downgrade():
    with op.batch_alter_table("organisation_module_settings", schema=None) as batch_op:
        batch_op.drop_column("escalation_enabled")
        batch_op.drop_column("ai_enabled")

    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.drop_index("ix_organisations_slug")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("sector_pack")
        batch_op.drop_column("font_family")
        batch_op.drop_column("logo_url")
        batch_op.drop_column("secondary_colour")
        batch_op.drop_column("primary_colour")
        batch_op.drop_column("is_active")
        batch_op.drop_column("slug")
