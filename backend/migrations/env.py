from alembic import context

from app.db import Base
from app import models  # noqa: F401  (đăng ký bảng)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connection = context.config.attributes["connection"]
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True,
                      compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
