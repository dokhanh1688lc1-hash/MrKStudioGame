"""Helper cho migration idempotent: bỏ qua thay đổi đã tồn tại (DB cũ tạo bằng create_all)."""
from alembic import op
import sqlalchemy as sa


def _insp():
    return sa.inspect(op.get_bind())


def has_table(name: str) -> bool:
    return name in _insp().get_table_names()


def has_column(table: str, col: str) -> bool:
    if not has_table(table):
        return False
    return col in {c["name"] for c in _insp().get_columns(table)}


def has_index(table: str, name: str) -> bool:
    if not has_table(table):
        return False
    return name in {i["name"] for i in _insp().get_indexes(table)}


def create_table(name, *args, **kw):
    if not has_table(name):
        op.create_table(name, *args, **kw)


def create_index(name, table, cols, unique=False):
    if has_table(table) and not has_index(table, name):
        op.create_index(name, table, cols, unique=unique)


def add_columns(table, *cols):
    todo = [c for c in cols if not has_column(table, c.name)]
    if todo:
        with op.batch_alter_table(table, schema=None) as b:
            for c in todo:
                b.add_column(c)


def drop_columns(table, *names):
    todo = [n for n in names if has_column(table, n)]
    if todo:
        with op.batch_alter_table(table, schema=None) as b:
            for n in todo:
                b.drop_column(n)
