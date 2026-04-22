"""add advisor escalation models

Revision ID: 6d3f2a91c6e4
Revises: 9f4db0b91f1a
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6d3f2a91c6e4"
down_revision = "9f4db0b91f1a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "advisor_escalations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=True),
        sa.Column("module_key", sa.String(length=50), nullable=False),
        sa.Column("source_record_type", sa.String(length=50), nullable=False),
        sa.Column("source_record_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("advisor_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_advisor_escalations_organisation_id"), "advisor_escalations", ["organisation_id"], unique=False)
    op.create_index(op.f("ix_advisor_escalations_module_key"), "advisor_escalations", ["module_key"], unique=False)
    op.create_index(op.f("ix_advisor_escalations_source_record_type"), "advisor_escalations", ["source_record_type"], unique=False)
    op.create_index(op.f("ix_advisor_escalations_source_record_id"), "advisor_escalations", ["source_record_id"], unique=False)
    op.create_index(op.f("ix_advisor_escalations_submitted_by_user_id"), "advisor_escalations", ["submitted_by_user_id"], unique=False)
    op.create_index(op.f("ix_advisor_escalations_assigned_to_user_id"), "advisor_escalations", ["assigned_to_user_id"], unique=False)
    op.create_index(op.f("ix_advisor_escalations_status"), "advisor_escalations", ["status"], unique=False)
    op.create_index(
        "ix_advisor_escalation_source_lookup",
        "advisor_escalations",
        ["source_record_type", "source_record_id"],
        unique=False,
    )

    op.create_table(
        "advisor_escalation_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("escalation_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["escalation_id"], ["advisor_escalations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_advisor_escalation_documents_escalation_id"), "advisor_escalation_documents", ["escalation_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_advisor_escalation_documents_escalation_id"), table_name="advisor_escalation_documents")
    op.drop_table("advisor_escalation_documents")

    op.drop_index("ix_advisor_escalation_source_lookup", table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_status"), table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_assigned_to_user_id"), table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_submitted_by_user_id"), table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_source_record_id"), table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_source_record_type"), table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_module_key"), table_name="advisor_escalations")
    op.drop_index(op.f("ix_advisor_escalations_organisation_id"), table_name="advisor_escalations")
    op.drop_table("advisor_escalations")