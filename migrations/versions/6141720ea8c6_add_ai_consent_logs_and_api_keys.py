"""Add AI consent logs and API keys

Revision ID: 6141720ea8c6
Revises: 4171ca098da6
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6141720ea8c6'
down_revision = '4171ca098da6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_consent_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(length=100), nullable=False),
        sa.Column('accepted', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('accepted_at', sa.DateTime(), nullable=False),
        sa.Column('request_ip', sa.String(length=100), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_consent_logs_user_id'), 'ai_consent_logs', ['user_id'], unique=False)

    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('organisation_id', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index(op.f('ix_api_keys_key_prefix'), 'api_keys', ['key_prefix'], unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=False)
    op.create_index(op.f('ix_api_keys_organisation_id'), 'api_keys', ['organisation_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_api_keys_organisation_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_prefix'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_ai_consent_logs_user_id'), table_name='ai_consent_logs')
    op.drop_table('ai_consent_logs')