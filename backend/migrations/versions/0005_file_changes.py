"""file change proposals and per-project write permission

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
import app.db


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'file_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('path', sa.String(length=400), nullable=False),
        sa.Column('new_content', sa.Text(), nullable=False),
        sa.Column('base_sha', sa.String(length=64), nullable=False),
        sa.Column('applied_sha', sa.String(length=64), nullable=False),
        sa.Column('backup_path', sa.String(length=600), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('source', sa.String(length=12), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('decided_by', sa.String(length=64), nullable=True),
        sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
        sa.Column('decided_at', app.db.UTCDateTime(), nullable=True),
        sa.CheckConstraint("status IN ('pending','applied','rejected','reverted')", name='ck_fchange_status'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_file_changes_project_id', 'file_changes', ['project_id'])
    op.create_index('ix_file_changes_status', 'file_changes', ['status'])
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('allow_write', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
