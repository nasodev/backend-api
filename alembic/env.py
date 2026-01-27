from logging.config import fileConfig

from sqlalchemy import engine_from_config, text
from sqlalchemy import pool

from alembic import context

from app.config import get_settings
from app.external import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

        # 마이그레이션 후 backend_api 사용자에게 권한 부여
        # postgres 사용자로 마이그레이션 실행 시에만 적용됨
        try:
            connection.execute(
                text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO backend_api")
            )
            connection.execute(
                text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO backend_api")
            )
            connection.commit()
        except Exception:
            # backend_api 사용자로 실행 시 권한 부여 불가 - 무시
            pass


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
