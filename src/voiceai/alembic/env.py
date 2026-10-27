"""Alembic environment for generating and applying database migrations."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from voiceai.core.config import get_settings
from voiceai.models import Base

# Load Alembic's configuration object.
config = context.config

# Configure migration logging using alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load the database connection settings from environment configuration.
settings = get_settings()

# Use a synchronous PostgreSQL driver for Alembic migrations.
# The application itself continues to use asyncpg.
alembic_url = settings.database_url.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
)
config.set_main_option(
    "sqlalchemy.url",
    alembic_url.replace("%", "%%"),
)

# Supply ORM metadata so Alembic can detect model/schema differences.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without opening a database connection."""

    # Read the configured URL and render SQL statements directly.
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    # Execute migration operations in a transaction context.
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply migrations interactively."""

    # Build a synchronous engine dedicated to this migration run.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Open a connection for Alembic's schema inspection and migration work.
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        # Apply the selected migration revision transactionally.
        with context.begin_transaction():
            context.run_migrations()


# Select the execution mode requested by Alembic.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
