"""Identity and OAuth metadata live outside every financial workspace."""
from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class IdentityBase(DeclarativeBase):
    pass


class User(IdentityBase):
    __tablename__ = "moniq_users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(IdentityBase):
    __tablename__ = "moniq_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("moniq_users.id"), index=True)
    expires: Mapped[int] = mapped_column(Integer)
    idle_expires: Mapped[int] = mapped_column(Integer)


class EmailGrant(IdentityBase):
    __tablename__ = "moniq_email_grants"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    expires: Mapped[int] = mapped_column(Integer)


class RateBucket(IdentityBase):
    __tablename__ = "moniq_rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires: Mapped[int] = mapped_column(Integer)


class GmailCredential(IdentityBase):
    __tablename__ = "moniq_gmail_credentials"
    user_id: Mapped[str] = mapped_column(ForeignKey("moniq_users.id"), primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class OAuthAttempt(IdentityBase):
    __tablename__ = "moniq_oauth_attempts"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("moniq_users.id"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("moniq_sessions.id", ondelete="CASCADE"))
    browser_digest: Mapped[str] = mapped_column(String(64))
    verifier: Mapped[bytes] = mapped_column(LargeBinary)
    expires: Mapped[int] = mapped_column(Integer)
