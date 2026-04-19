"""add organisation_id to employee

Revision ID: 02d6340e42da
Revises: db0bdb053a0c
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "02d6340e42da"
down_revision = "db0bdb053a0c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("employee", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organisation_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_employee_organisation_id", ["organisation_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_employee_organisation_id_organisations",
            "organisations",
            ["organisation_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("employee", schema=None) as batch_op:
        batch_op.drop_constraint("fk_employee_organisation_id_organisations", type_="foreignkey")
        batch_op.drop_index("ix_employee_organisation_id")
        batch_op.drop_column("organisation_id")
