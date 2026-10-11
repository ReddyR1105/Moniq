"""Explicit offline SQLite-to-PostgreSQL copy. Requires an empty verified destination."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import config  # noqa: E402, F401
from backend.app.hosted_settings import HostedSettings  # noqa: E402
from backend.app.identity import IdentityStore, normalize_email  # noqa: E402
from backend.app.identity_models import User  # noqa: E402
from backend.app.models import Account, Base, Profile  # noqa: E402
from sqlalchemy import create_engine, delete, func, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", required=True, help="Path to the existing personal SQLite database; source opens read-only.")
parser.add_argument("--email", required=True, help="Verified invited account that will own the copied records.")
parser.add_argument("--copy", action="store_true", help="Perform the copy after backups and dry-run review. No Gmail token files are copied.")
args = parser.parse_args()
source_path = Path(args.source).resolve(strict=True)
if source_path.suffix not in {".db", ".sqlite", ".sqlite3"}:
    raise SystemExit("Choose an existing SQLite personal database.")
settings = HostedSettings.load()
if not settings.private_enabled:
    raise SystemExit("Use the verified private test configuration and an invited, verified destination account.")
service = IdentityStore(settings)
source = create_engine("sqlite:///file:" + source_path.as_posix() + "?mode=ro&uri=true")
try:
    with Session(service.engine) as db:
        user = db.scalar(select(User).where(User.email == normalize_email(args.email), User.verified.is_(True), User.enabled.is_(True)))
        if user is None:
            raise SystemExit("Destination is not a verified account.")
        destination = service.workspace(user.id)
    with source.connect() as original, destination.begin() as target:
        target.execute(text("SELECT pg_advisory_xact_lock(hashtext(:owner))"), {"owner": user.id})
        # An untouched registration contains only Profile. Do not overwrite any financial data.
        for table in Base.metadata.sorted_tables:
            if table.name != Profile.__tablename__ and target.scalar(select(func.count()).select_from(table)):
                raise SystemExit("Destination contains financial records. Copy was refused; nothing overwritten.")
        accounts = list(original.execute(select(Account.__table__)).mappings())
        if not accounts or any(account["mode"] != "registered" for account in accounts):
            raise SystemExit("Source is not a registered personal workspace. Synthetic demo/scenario imports are refused.")
        rows = {table.name: [dict(row) for row in original.execute(select(table)).mappings()] for table in Base.metadata.sorted_tables}
        print(f"Read-only source validated: {len(accounts)} registered accounts, {len(rows['transactions'])} transactions. No financial values or tokens printed.")
        if args.copy:
            target.execute(delete(Profile))
            for table in Base.metadata.sorted_tables:
                if rows[table.name]:
                    target.execute(table.insert(), rows[table.name])
                for column in table.primary_key:
                    if column.autoincrement is True or (column.autoincrement == "auto" and str(column.type) == "INTEGER" and not column.foreign_keys):
                        # Set serial sequences after preserving the existing primary keys.
                        sequence = target.scalar(text("SELECT pg_get_serial_sequence(:table, :column)"), {"table": "moniq_user_" + user.id + "." + table.name, "column": column.name})
                        if sequence:
                            maximum = target.scalar(select(func.max(column))) or 0
                            target.execute(text("SELECT setval(CAST(:sequence AS regclass), :value, :called)"), {"sequence": sequence, "value": max(1, maximum), "called": maximum > 0})
            print("Copied registered financial records transactionally. The local source was unchanged. Reconnect Gmail inside the new account.")
        else:
            print("Dry run only. Back up both databases, then use --copy after reviewing ownership and counts.")
finally:
    source.dispose()
    service.close()
