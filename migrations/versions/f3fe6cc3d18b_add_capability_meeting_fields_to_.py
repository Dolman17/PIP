"""Add capability meeting fields to PIPRecord

Revision ID: f3fe6cc3d18b
Revises: 9658cd988851
Create Date: 2025-07-21 22:13:01.416907

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3fe6cc3d18b'
down_revision = '9658cd988851'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('pip_record', sa.Column('capability_meeting_date', sa.DateTime(), nullable=True))
    op.add_column('pip_record', sa.Column('capability_meeting_time', sa.String(), nullable=True))
    op.add_column('pip_record', sa.Column('capability_meeting_venue', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('pip_record', 'capability_meeting_venue')
    op.drop_column('pip_record', 'capability_meeting_time')
    op.drop_column('pip_record', 'capability_meeting_date')
    # ### end Alembic commands ###
