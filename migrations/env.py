import sys
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# Adiciona caminho raiz para importar backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app 
from backend.db import db
# Ensure models are imported so metadata is populated.
# backend.app should already do this, but this is an explicit ensure.
# If backend.app definitely imports all models, this next line might be redundant
# but is common practice in Alembic env.py files.
import backend.models # noqa

config = context.config
fileConfig(config.config_file_name)

target_metadata = db.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool
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
