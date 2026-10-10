"""Provider boundaries for the existing prototype and optional local Gmail."""
from typing import Protocol


class BankProvider(Protocol):
    def create_link_token(self) -> str: ...
    def exchange_public_token(self, public_token: str) -> str: ...
    def sync(self, account_id: int, cursor: str | None) -> dict:
        """Return added, modified, removed, next_cursor, has_more; reconcile posted pending ids atomically."""
        ...


class OfferProvider(Protocol):
    def fetch_verified_offers(self) -> list[dict]: ...


class ExplanationProvider(Protocol):
    def explain(self, question: str, calculated_evidence: dict) -> str:
        """Read-only evidence: never execute model-generated SQL or compute money using a model."""
        ...


def integration_status():
    from .config import PUBLIC_DEMO
    return {"bank": "synthetic-demo", "assistant": "local-data-backed", "deals": "synthetic-samples",
            "gmail": "disabled in public demo" if PUBLIC_DEMO else "optional authorized local read-only import",
            "plaid": "not implemented", "gemini": "not implemented",
            "message_import": "user-initiated paste; no SMS or iMessage access"}
