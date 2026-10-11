"""Versioned PostgreSQL migrations; no private SQLite fallback in hosted mode."""
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def migrate(engine, kind, schema=None):
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            # Serialize migrations across workers without process-local assumptions.
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": "moniq-migrate:" + (schema or kind)})
            if schema:
                if not re.fullmatch(r"moniq_user_[0-9a-f]{32}", schema):
                    raise ValueError("Invalid workspace schema.")
                connection.execute(text('CREATE SCHEMA IF NOT EXISTS "' + schema + '"'))
        cfg = Config()
        cfg.set_main_option("script_location", str(MIGRATIONS / kind))
        cfg.attributes.update(connection=connection, schema=schema, kind=kind)
        command.upgrade(cfg, "head")


def migrate_identity(engine):
    migrate(engine, "identity")


def migrate_workspace(engine, schema=None):
    migrate(engine, "workspace", schema)
