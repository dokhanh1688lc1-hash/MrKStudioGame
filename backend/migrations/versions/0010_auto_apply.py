"""projects.auto_apply: AI tự áp dụng thay đổi file (cần allow_write)

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
import importlib.util as _u, pathlib as _p
_spec = _u.spec_from_file_location('safe_helpers', _p.Path(__file__).resolve().parents[1] / 'safe_helpers.py'); _safe = _u.module_from_spec(_spec); _spec.loader.exec_module(_safe)

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _safe.add_columns('projects', sa.Column('auto_apply', sa.Boolean(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
