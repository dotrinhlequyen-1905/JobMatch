from alembic import context
from app.config import settings
from app.core.database import Base, engine
from app import models  # noqa: F401

if context.is_offline_mode():
    context.configure(
        url=settings.database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
        if connection.dialect.name == "sqlite":
            if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                raise RuntimeError("Migration produced invalid foreign key references")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
