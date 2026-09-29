from logging.config import fileConfig
from os import getenv

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from app.database import Base

# Import models so they are registered in Base.metadata
from app.models.user import User
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.meeting_agenda import MeetingAgenda
from app.models.meeting_action import MeetingAction


# Load environment variables from .env
load_dotenv()

# Alembic Config object
config = context.config

# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --------------------------------------------------
# Database configuration
# --------------------------------------------------

DB_ENGINE = getenv("DB_ENGINE")
DB_NAME = getenv("DB_NAME")
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")

# Validate required environment variables
required_vars = {
    "DB_ENGINE": DB_ENGINE,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
}

missing_vars = [name for name, value in required_vars.items() if not value]

if missing_vars:
    raise ValueError(
        f"Missing database environment variables: {', '.join(missing_vars)}"
    )


# Build PostgreSQL connection URL
DATABASE_URL = (
    f"{DB_ENGINE}://"
    f"{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/"
    f"{DB_NAME}"
)

# Set database URL for Alembic
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%")
)


# --------------------------------------------------
# SQLAlchemy metadata
# --------------------------------------------------

target_metadata = Base.metadata


# --------------------------------------------------
# Migration functions
# --------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

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
    """Run migrations in online mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()