"""Remove legacy pip_id columns now that pip_record_id exists

Revision ID: 4e9e838b7b35
Revises: 9675f85d84a3
Create Date: 2025-07-21
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '4e9e838b7b35'
down_revision = '9675f85d84a3'
branch_labels = None
depends_on = None

def upgrade():
    # disable foreign keys while we rebuild
    op.execute("PRAGMA foreign_keys=OFF")

    # drop pip_id in pip_action_item
    with op.batch_alter_table('pip_action_item') as batch_op:
        batch_op.drop_column('pip_id')

    # drop pip_id in timeline_event
    with op.batch_alter_table('timeline_event') as batch_op:
        batch_op.drop_column('pip_id')

    # re-enable foreign keys
    op.execute("PRAGMA foreign_keys=ON")


def downgrade():
    op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table('pip_action_item') as batch_op:
        batch_op.add_column(
            sa.Column('pip_id', sa.Integer(), nullable=False)
        )

    with op.batch_alter_table('timeline_event') as batch_op:
        batch_op.add_column(
            sa.Column('pip_id', sa.Integer(), nullable=False)
        )

    op.execute("PRAGMA foreign_keys=ON")
