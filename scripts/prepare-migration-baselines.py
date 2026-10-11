"""Developer utility: create immutable initial revisions, never read a user's database."""
from pathlib import Path
import sys

from alembic.autogenerate import produce_migrations, render_python_code
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.identity_models import IdentityBase  # noqa: E402
from backend.app.models import Base  # noqa: E402

for kind, metadata in (("identity", IdentityBase.metadata), ("workspace", Base.metadata)):
    target = ROOT / "backend" / "migrations" / kind / "versions" / "0001_initial.py"
    if target.exists():
        raise SystemExit("Initial revisions already exist. Use a new migration for future changes.")
    with create_engine("sqlite://").connect() as connection:
        migration = produce_migrations(MigrationContext.configure(connection), metadata)
        upgrade = render_python_code(migration.upgrade_ops)
        downgrade = render_python_code(migration.downgrade_ops)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('"""Immutable initial ' + kind + ' schema."""\nfrom alembic import op\nimport sqlalchemy as sa\n\nrevision = "' + kind + '_0001"\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n\ndef upgrade():\n' + upgrade + '\n\ndef downgrade():\n' + downgrade + '\n', encoding="utf-8")
print("Created immutable identity and financial workspace initial migrations.")
