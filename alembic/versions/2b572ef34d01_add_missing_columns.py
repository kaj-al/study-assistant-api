"""Add missing columns: users.role/updated_at, notes.user_id/source/updated_at, History.user_id/title/extra_data

Revision ID: 2b572ef34d01
Revises: 1a464fa12a90
Create Date: 2026-10-24 12:11:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = '2b572ef34d01'
down_revision = '1a464fa12a90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(), nullable=True, server_default='student'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('notes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(), nullable=True, server_default='manual'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('History', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('title', sa.String(), nullable=True, server_default=''))
        batch_op.add_column(sa.Column('extra_data', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('History', schema=None) as batch_op:
        batch_op.drop_column('extra_data')
        batch_op.drop_column('title')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('notes', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('source')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('role')
n