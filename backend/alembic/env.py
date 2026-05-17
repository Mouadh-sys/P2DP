from logging.config import fileConfig
import os
import sys

from sqlalchemy import create_engine
from alembic import context

# make sure the app package is importable when alembic runs from backend/
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from app.core.config import settings
from app.db.database import Base
import app.db.models  # noqa: F401 Import models so Base.metadata is populated

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set target metadata for 'autogenerate'
target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(settings.database_url)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

