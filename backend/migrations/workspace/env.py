from alembic import context

cfg = context.config
context.configure(connection=cfg.attributes["connection"], version_table="moniq_workspace_version",
                  version_table_schema=cfg.attributes.get("schema"))
with context.begin_transaction():
    context.run_migrations()
