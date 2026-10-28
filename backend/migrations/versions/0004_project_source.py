"""project source (github / local folder) fields

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa
import app.db


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_type', sa.String(length=16), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('source_ref', sa.String(length=500), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('source_branch', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('source_synced_at', app.db.UTCDateTime(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
