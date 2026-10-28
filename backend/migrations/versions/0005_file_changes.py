"""file change proposals and per-project write permission

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import importlib.util as _u, pathlib as _p
_spec=_u.spec_from_file_location('safe_helpers', _p.Path(__file__).resolve().parents[1] / 'safe_helpers.py'); _safe=_u.module_from_spec(_spec); _spec.loader.exec_module(_safe)
import sqlalchemy as sa
import app.db


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _safe.create_table(
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
    _safe.create_index('ix_file_changes_project_id', 'file_changes', ['project_id'])
    _safe.create_index('ix_file_changes_status', 'file_changes', ['status'])
    _safe.add_columns('projects', sa.Column('allow_write', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
