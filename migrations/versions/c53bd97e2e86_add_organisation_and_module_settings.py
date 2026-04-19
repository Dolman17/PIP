"""add organisation and module settings

Revision ID: c53bd97e2e86
Revises: 6141720ea8c6
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c53bd97e2e86"
down_revision = "6141720ea8c6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organisations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "organisation_module_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("module_key", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organisation_id", "module_key", name="uq_org_module"),
    )

    op.create_index(
        op.f("ix_organisation_module_settings_organisation_id"),
        "organisation_module_settings",
        ["organisation_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_organisation_module_settings_organisation_id"),
        table_name="organisation_module_settings",
    )
    op.drop_table("organisation_module_settings")
    op.drop_table("organisations")
