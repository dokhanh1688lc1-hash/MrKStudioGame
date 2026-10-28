"""asset library

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa
import app.db


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('kind', sa.String(length=12), nullable=False),
        sa.Column('source', sa.String(length=14), nullable=False),
        sa.Column('license', sa.String(length=200), nullable=False),
        sa.Column('license_url', sa.String(length=400), nullable=False),
        sa.Column('author', sa.String(length=160), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(length=300), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('created_at', app.db.UTCDateTime(), nullable=False),
        sa.Column('updated_at', app.db.UTCDateTime(), nullable=False),
        sa.CheckConstraint("kind IN ('image','audio','font','model','data','other')", name='ck_asset_kind'),
        sa.CheckConstraint("source IN ('own','purchased','open_license','ai_generated','unknown')", name='ck_asset_source'),
        sa.CheckConstraint("status IN ('draft','approved','rejected')", name='ck_asset_status'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assets_project_id', 'assets', ['project_id'])
    op.create_index('ix_assets_status', 'assets', ['status'])


def downgrade() -> None:
    raise NotImplementedError("Không hỗ trợ hạ cấp; khôi phục từ bản sao lưu.")
