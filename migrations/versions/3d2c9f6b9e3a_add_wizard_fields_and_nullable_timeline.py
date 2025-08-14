"""Add wizard fields to PIPRecord; make TimelineEvent.pip_record_id nullable

Revision ID: 3d2c9f6b9e3a
Revises: 01f5e8bdb1f1_add_wizard_fields_to_piprecord_make_
Create Date: 2025-08-09 21:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3d2c9f6b9e3a"
down_revision = "01f5e8bdb1f1"
branch_labels = None
depends_on = None


def upgrade():
    # --- PIPRecord: add wizard fields ---
    with op.batch_alter_table("pip_record", schema=None) as batch_op:
        batch_op.add_column(sa.Column("concern_category", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("severity", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("frequency", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.Text(), nullable=True))

    # --- TimelineEvent: allow probation-only events (nullable FK) ---
    with op.batch_alter_table("timeline_event", schema=None) as batch_op:
        batch_op.alter_column(
            "pip_record_id",
            existing_type=sa.Integer(),
            nullable=True,
            existing_nullable=False
        )


def downgrade():
    # --- TimelineEvent: revert to NOT NULL ---
    with op.batch_alter_table("timeline_event", schema=None) as batch_op:
        batch_op.alter_column(
            "pip_record_id",
            existing_type=sa.Integer(),
            nullable=False,
            existing_nullable=True
        )

    # --- PIPRecord: drop wizard fields ---
    with op.batch_alter_table("pip_record", schema=None) as batch_op:
        batch_op.drop_column("tags")
        batch_op.drop_column("frequency")
        batch_op.drop_column("severity")
        batch_op.drop_column("concern_category")
