"""department lessons

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import importlib.util as _u, pathlib as _p
_spec=_u.spec_from_file_location('safe_helpers', _p.Path(__file__).resolve().parents[1] / 'safe_helpers.py'); _safe=_u.module_from_spec(_spec); _spec.loader.exec_module(_safe)
import sqlalchemy as sa
import app.db


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _safe.create_table(
        'lessons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_key', sa.String(length=40), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('source', sa.String(length=10), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('uses', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
        sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
        sa.CheckConstraint("status IN ('suggested','active','archived')", name='ck_lesson_status'),
        sa.CheckConstraint("source IN ('manual','ceo')", name='ck_lesson_source'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    _safe.create_index('ix_lessons_department_key', 'lessons', ['department_key'])
    _safe.create_index('ix_lessons_status', 'lessons', ['status'])


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
