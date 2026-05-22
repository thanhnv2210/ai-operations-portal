"""SQLAlchemy read models for keycloak — payment schema."""

from decimal import Decimal

from sqlalchemy import BigInteger, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import KeycloakBase


class SofPayment(KeycloakBase):
    """SOF payment attempt. One-to-one with remittance.transaction."""

    __tablename__ = "ml_m_sof_payment"
    __table_args__ = {"schema": "payment"}

    payment_id: Mapped[str] = mapped_column(String, primary_key=True)
    internal_transaction_id: Mapped[int | None] = mapped_column(BigInteger)  # FK → remittance.transaction
    card_id: Mapped[str | None] = mapped_column(String(40))
    payment_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    status: Mapped[str | None] = mapped_column(String)
    refund_initiated_by: Mapped[str | None] = mapped_column(String)  # "system" or portal user login


class TokenizedCard(KeycloakBase):
    """NETS tokenized debit cards registered as SOF."""

    __tablename__ = "m_ml_tokenized_card"
    __table_args__ = {"schema": "payment"}

    card_id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    telepin_account_id: Mapped[str | None] = mapped_column(String)
    device_id: Mapped[str | None] = mapped_column(String)
    sof_type: Mapped[str | None] = mapped_column(String)
    card_token: Mapped[str | None] = mapped_column(String(48))
    last_4_digits_fpan: Mapped[str | None] = mapped_column(String)
    bank_fiid: Mapped[str | None] = mapped_column(String)
    issuer_short_name: Mapped[str | None] = mapped_column(String)
    token_status: Mapped[int | None] = mapped_column(SmallInteger)
    card_status: Mapped[str | None] = mapped_column(String)         # REGISTERED / UNREGISTERED
