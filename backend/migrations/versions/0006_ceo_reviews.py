"""ceo reviews

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import importlib.util as _u, pathlib as _p
_spec=_u.spec_from_file_location('safe_helpers', _p.Path(__file__).resolve().parents[1] / 'safe_helpers.py'); _safe=_u.module_from_spec(_spec); _spec.loader.exec_module(_safe)
import sqlalchemy as sa
import app.db


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _safe.create_table(
        'ceo_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=12), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('followup_task_id', sa.Integer(), nullable=True),
        sa.Column('decided_by', sa.String(length=64), nullable=False),
        sa.Column('decided_at', app.db.UTCDateTime(), nullable=False),
        sa.CheckConstraint("decision IN ('accepted','rework','forward','dismissed')", name='ck_ceo_decision'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.ForeignKeyConstraint(['followup_task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id'),
    )


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
