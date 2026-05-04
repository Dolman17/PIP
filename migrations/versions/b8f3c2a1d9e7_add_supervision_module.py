"""add supervision module

Revision ID: b8f3c2a1d9e7
Revises: 6d3f2a91c6e4
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


revision = "b8f3c2a1d9e7"
down_revision = "6d3f2a91c6e4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "supervision_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("manager_user_id", sa.Integer(), nullable=True),
        sa.Column("meeting_title", sa.String(length=255), nullable=True),
        sa.Column("meeting_type", sa.String(length=100), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_time", sa.String(length=20), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("supervision_period_start", sa.Date(), nullable=True),
        sa.Column("supervision_period_end", sa.Date(), nullable=True),
        sa.Column("wellbeing_summary", sa.Text(), nullable=True),
        sa.Column("performance_summary", sa.Text(), nullable=True),
        sa.Column("conduct_summary", sa.Text(), nullable=True),
        sa.Column("training_summary", sa.Text(), nullable=True),
        sa.Column("workload_summary", sa.Text(), nullable=True),
        sa.Column("achievements_summary", sa.Text(), nullable=True),
        sa.Column("concerns_summary", sa.Text(), nullable=True),
        sa.Column("employee_comments", sa.Text(), nullable=True),
        sa.Column("manager_comments", sa.Text(), nullable=True),
        sa.Column("manager_confidential_notes", sa.Text(), nullable=True),
        sa.Column("agreed_support", sa.Text(), nullable=True),
        sa.Column("overall_summary", sa.Text(), nullable=True),
        sa.Column("next_meeting_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("updated_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["manager_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_supervision_records_employee_id",
        "supervision_records",
        ["employee_id"],
    )
    op.create_index(
        "ix_supervision_records_manager_user_id",
        "supervision_records",
        ["manager_user_id"],
    )
    op.create_index(
        "ix_supervision_records_meeting_date",
        "supervision_records",
        ["meeting_date"],
    )
    op.create_index(
        "ix_supervision_records_meeting_type",
        "supervision_records",
        ["meeting_type"],
    )
    op.create_index(
        "ix_supervision_records_next_meeting_date",
        "supervision_records",
        ["next_meeting_date"],
    )
    op.create_index(
        "ix_supervision_records_organisation_id",
        "supervision_records",
        ["organisation_id"],
    )
    op.create_index(
        "ix_supervision_records_status",
        "supervision_records",
        ["status"],
    )

    op.create_table(
        "supervision_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supervision_id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_type", sa.String(length=50), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["supervision_id"], ["supervision_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_supervision_actions_due_date",
        "supervision_actions",
        ["due_date"],
    )
    op.create_index(
        "ix_supervision_actions_employee_id",
        "supervision_actions",
        ["employee_id"],
    )
    op.create_index(
        "ix_supervision_actions_organisation_id",
        "supervision_actions",
        ["organisation_id"],
    )
    op.create_index(
        "ix_supervision_actions_status",
        "supervision_actions",
        ["status"],
    )
    op.create_index(
        "ix_supervision_actions_supervision_id",
        "supervision_actions",
        ["supervision_id"],
    )

    op.create_table(
        "supervision_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meeting_type", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_supervision_templates_organisation_id",
        "supervision_templates",
        ["organisation_id"],
    )

    op.create_table(
        "supervision_template_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=100), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["supervision_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_supervision_template_questions_template_id",
        "supervision_template_questions",
        ["template_id"],
    )

    op.create_table(
        "supervision_timeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supervision_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["supervision_id"], ["supervision_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_supervision_timeline_events_supervision_id",
        "supervision_timeline_events",
        ["supervision_id"],
    )
    op.create_index(
        "ix_supervision_timeline_events_timestamp",
        "supervision_timeline_events",
        ["timestamp"],
    )


def downgrade():
    op.drop_index("ix_supervision_timeline_events_timestamp", table_name="supervision_timeline_events")
    op.drop_index("ix_supervision_timeline_events_supervision_id", table_name="supervision_timeline_events")
    op.drop_table("supervision_timeline_events")

    op.drop_index("ix_supervision_template_questions_template_id", table_name="supervision_template_questions")
    op.drop_table("supervision_template_questions")

    op.drop_index("ix_supervision_templates_organisation_id", table_name="supervision_templates")
    op.drop_table("supervision_templates")

    op.drop_index("ix_supervision_actions_supervision_id", table_name="supervision_actions")
    op.drop_index("ix_supervision_actions_status", table_name="supervision_actions")
    op.drop_index("ix_supervision_actions_organisation_id", table_name="supervision_actions")
    op.drop_index("ix_supervision_actions_employee_id", table_name="supervision_actions")
    op.drop_index("ix_supervision_actions_due_date", table_name="supervision_actions")
    op.drop_table("supervision_actions")

    op.drop_index("ix_supervision_records_status", table_name="supervision_records")
    op.drop_index("ix_supervision_records_organisation_id", table_name="supervision_records")
    op.drop_index("ix_supervision_records_next_meeting_date", table_name="supervision_records")
    op.drop_index("ix_supervision_records_meeting_type", table_name="supervision_records")
    op.drop_index("ix_supervision_records_meeting_date", table_name="supervision_records")
    op.drop_index("ix_supervision_records_manager_user_id", table_name="supervision_records")
    op.drop_index("ix_supervision_records_employee_id", table_name="supervision_records")
    op.drop_table("supervision_records")