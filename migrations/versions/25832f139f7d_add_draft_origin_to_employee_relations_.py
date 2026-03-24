"""Add draft_origin to employee relations documents

Revision ID: 25832f139f7d
Revises: f774c8f8693c
Create Date: 2026-03-24 10:23:35.219536

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "25832f139f7d"
down_revision = "f774c8f8693c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "employee_relations_documents",
        sa.Column(
            "draft_origin",
            sa.String(length=50),
            nullable=False,
            server_default="plain",
        ),
    )
    op.create_index(
        op.f("ix_employee_relations_documents_draft_origin"),
        "employee_relations_documents",
        ["draft_origin"],
        unique=False,
    )

    # Optional but cleaner: remove the DB-level default after backfilling existing rows
    with op.batch_alter_table("employee_relations_documents") as batch_op:
        batch_op.alter_column("draft_origin", server_default=None)


def downgrade():
    op.drop_index(
        op.f("ix_employee_relations_documents_draft_origin"),
        table_name="employee_relations_documents",
    )
    op.drop_column("employee_relations_documents", "draft_origin")