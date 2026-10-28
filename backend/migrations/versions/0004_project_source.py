"""project source (github / local folder) fields

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import importlib.util as _u, pathlib as _p
_spec=_u.spec_from_file_location('safe_helpers', _p.Path(__file__).resolve().parents[1] / 'safe_helpers.py'); _safe=_u.module_from_spec(_spec); _spec.loader.exec_module(_safe)
import sqlalchemy as sa
import app.db


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _safe.add_columns('projects',
        sa.Column('source_type', sa.String(length=16), nullable=False, server_default=''),
        sa.Column('source_ref', sa.String(length=500), nullable=False, server_default=''),
        sa.Column('source_branch', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('source_synced_at', app.db.UTCDateTime(), nullable=True),
    )


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
