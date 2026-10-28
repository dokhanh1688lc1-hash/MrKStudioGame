"""budgets become run-count limits; drop cost columns

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from importlib import util as _u; import pathlib as _p
    _sp=_u.spec_from_file_location('safe_helpers', _p.Path(__file__).resolve().parents[1] / 'safe_helpers.py'); _s=_u.module_from_spec(_sp); _sp.loader.exec_module(_s)
    if _s.has_column('budgets', 'limit_runs'):
        return  # DB đã có lược đồ mới (tạo bằng create_all)
    with op.batch_alter_table('budgets', schema=None) as batch_op:
        batch_op.drop_constraint('ck_budget_limit', type_='check')
        batch_op.add_column(sa.Column('limit_runs', sa.Integer(), nullable=True))
    # Hạn mức USD cũ không còn ý nghĩa → đặt giới hạn lượt mặc định hợp lý (ít nhất 1)
    op.execute("UPDATE budgets SET limit_runs = CASE WHEN CAST(limit_usd AS INTEGER) >= 1 THEN CAST(limit_usd AS INTEGER) ELSE 1 END")
    with op.batch_alter_table('budgets', schema=None) as batch_op:
        batch_op.alter_column('limit_runs', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column('limit_usd')
        batch_op.create_check_constraint('ck_budget_limit', 'limit_runs > 0')
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('budget_limit')
        batch_op.drop_column('actual_cost')
        batch_op.drop_column('estimated_cost')
    with op.batch_alter_table('task_attempts', schema=None) as batch_op:
        batch_op.drop_column('cost_usd')
    with op.batch_alter_table('usage_records', schema=None) as batch_op:
        batch_op.drop_column('cost_usd')
    op.execute("DELETE FROM system_settings WHERE key = 'approval_cost_threshold_usd'")


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
