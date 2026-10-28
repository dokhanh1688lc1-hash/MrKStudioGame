"""production: documents, tests, builds, checklist, finance, analytics

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa
import app.db


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('analytics_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('source', sa.String(length=200), nullable=False),
    sa.Column('period_start', sa.String(length=10), nullable=False),
    sa.Column('period_end', sa.String(length=10), nullable=False),
    sa.Column('metrics', sa.Text(), nullable=False),
    sa.Column('limitations', sa.Text(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('created_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
    sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_reports_project_id'), 'analytics_reports', ['project_id'], unique=False)
    op.create_table('checklist_states',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=40), nullable=False),
    sa.Column('done', sa.Boolean(), nullable=False),
    sa.Column('note', sa.String(length=300), nullable=False),
    sa.Column('by', sa.String(length=64), nullable=False),
    sa.Column('at', app.db.UTCDateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'key', name='uq_checklist')
    )
    op.create_index(op.f('ix_checklist_states_project_id'), 'checklist_states', ['project_id'], unique=False)
    op.create_table('finance_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('kind', sa.String(length=8), nullable=False),
    sa.Column('category', sa.String(length=30), nullable=False),
    sa.Column('amount_cents', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('occurred_on', sa.String(length=10), nullable=False),
    sa.Column('note', sa.String(length=300), nullable=False),
    sa.Column('estimated', sa.Boolean(), nullable=False),
    sa.Column('confirmed', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.String(length=64), nullable=False),
    sa.Column('confirmed_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
    sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
    sa.CheckConstraint("kind IN ('cost','revenue')", name='ck_fin_kind'),
    sa.CheckConstraint('amount_cents > 0', name='ck_fin_amount'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_finance_records_project_id'), 'finance_records', ['project_id'], unique=False)
    op.create_table('game_builds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.String(length=40), nullable=False),
    sa.Column('platform', sa.String(length=12), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('file_path', sa.String(length=300), nullable=False),
    sa.Column('changelog', sa.Text(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('created_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
    sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
    sa.CheckConstraint("platform IN ('windows','linux','macos','android','ios','web','other')", name='ck_build_platform'),
    sa.CheckConstraint("status IN ('planned','ready','failed','released')", name='ck_build_status'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'version', 'platform', name='uq_build')
    )
    op.create_index(op.f('ix_game_builds_project_id'), 'game_builds', ['project_id'], unique=False)
    op.create_table('test_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('area', sa.String(length=60), nullable=False),
    sa.Column('steps', sa.Text(), nullable=False),
    sa.Column('expected', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('last_run_at', app.db.UTCDateTime(), nullable=True),
    sa.Column('created_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
    sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
    sa.CheckConstraint("status IN ('not_run','passed','failed','blocked')", name='ck_test_status'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_cases_project_id'), 'test_cases', ['project_id'], unique=False)
    op.create_table('test_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('test_case_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('build_id', sa.Integer(), nullable=True),
    sa.Column('run_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
    sa.CheckConstraint("severity = '' OR severity IN ('low','medium','high','critical')", name='ck_run_severity'),
    sa.CheckConstraint("status IN ('passed','failed','blocked')", name='ck_run_status'),
    sa.ForeignKeyConstraint(['build_id'], ['game_builds.id'], ),
    sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_runs_test_case_id'), 'test_runs', ['test_case_id'], unique=False)
    op.create_table('project_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
    sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
    sa.CheckConstraint("kind IN ('gdd','market_report','design','art_bible','audio_bible','tech','qa_report','monetization','marketing','store_listing','legal','release_notes','other')", name='ck_doc_kind'),
    sa.CheckConstraint("status IN ('draft','approved')", name='ck_doc_status'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'title', 'version', name='uq_doc_version')
    )
    op.create_index(op.f('ix_project_documents_project_id'), 'project_documents', ['project_id'], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
