from __future__ import with_statement
import logging
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import os
import sys

# Add your app directory to sys.path so it finds models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db  # 👈 this imports your SQLAlchemy instance and models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Set target metadata
target_metadata = db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
