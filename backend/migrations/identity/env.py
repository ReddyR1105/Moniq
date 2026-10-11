from alembic import context

cfg = context.config
context.configure(connection=cfg.attributes["connection"], version_table="moniq_identity_version")
with context.begin_transaction():
    context.run_migrations()
