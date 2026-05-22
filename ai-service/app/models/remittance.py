"""SQLAlchemy read models for keycloak — remittance schema."""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import KeycloakBase


class TransactionStatus(str, enum.Enum):
    # Payment phase
    PAYMENT_VALIDATED = "PAYMENT_VALIDATED"
    PAYMENT_ACCEPTED = "PAYMENT_ACCEPTED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_RESERVED = "PAYMENT_RESERVED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_VALIDATION_FAILED = "PAYMENT_VALIDATION_FAILED"
    PAYMENT_RESERVATION_FAILED = "PAYMENT_RESERVATION_FAILED"
    PAYMENT_ACCEPTANCE_FAILED = "PAYMENT_ACCEPTANCE_FAILED"

    # SOF phase
    SOF_PAY_PENDING = "SOF_PAY_PENDING"
    SOF_PAY_COMPLETED = "SOF_PAY_COMPLETED"
    SOF_PAY_FAILED = "SOF_PAY_FAILED"

    # Remittance phase
    TRANSACTION_SUBMITTED = "TRANSACTION_SUBMITTED"
    TRANSACTION_IN_PROGRESS = "TRANSACTION_IN_PROGRESS"
    TRANSACTION_SUCCESS = "TRANSACTION_SUCCESS"
    TRANSACTION_COMPLETED = "TRANSACTION_COMPLETED"
    TRANSACTION_CONFIRMED = "TRANSACTION_CONFIRMED"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    TRANSACTION_DECLINED = "TRANSACTION_DECLINED"
    TRANSACTION_ON_HOLD = "TRANSACTION_ON_HOLD"
    TRANSACTION_CANCELLED = "TRANSACTION_CANCELLED"
    TRANSACTION_EXPIRED = "TRANSACTION_EXPIRED"

    # Refund
    REFUND_REQUIRED = "REFUND_REQUIRED"
    PAYMENT_REFUND_REQUIRED = "PAYMENT_REFUND_REQUIRED"
    SOF_REFUND_REQUIRED = "SOF_REFUND_REQUIRED"
    REFUNDED = "REFUNDED"
    REFUND_FAILED = "REFUND_FAILED"
    REFUND_IN_PROGRESS = "REFUND_IN_PROGRESS"

    # Fraud
    FRAUD_CHECK_FAILED = "FRAUD_CHECK_FAILED"
    FRAUD_CHECK_DECLINED = "FRAUD_CHECK_DECLINED"
    FRAUD_CHECK_TIMEOUT = "FRAUD_CHECK_TIMEOUT"

    # Misc
    PENDING = "PENDING"
    INITIATED = "INITIATED"


# Terminal statuses — no further processing expected
TERMINAL_STATUSES: frozenset[TransactionStatus] = frozenset({
    TransactionStatus.TRANSACTION_SUCCESS,
    TransactionStatus.TRANSACTION_COMPLETED,
    TransactionStatus.TRANSACTION_CONFIRMED,
    TransactionStatus.TRANSACTION_FAILED,
    TransactionStatus.TRANSACTION_DECLINED,
    TransactionStatus.TRANSACTION_CANCELLED,
    TransactionStatus.TRANSACTION_EXPIRED,
    TransactionStatus.REFUNDED,
    TransactionStatus.REFUND_FAILED,
    TransactionStatus.FRAUD_CHECK_DECLINED,
    TransactionStatus.FRAUD_CHECK_FAILED,
})

# Failed statuses — used for failure rate calculations
FAILED_STATUSES: frozenset[TransactionStatus] = frozenset({
    TransactionStatus.TRANSACTION_FAILED,
    TransactionStatus.TRANSACTION_DECLINED,
    TransactionStatus.PAYMENT_FAILED,
    TransactionStatus.PAYMENT_VALIDATION_FAILED,
    TransactionStatus.PAYMENT_RESERVATION_FAILED,
    TransactionStatus.PAYMENT_ACCEPTANCE_FAILED,
    TransactionStatus.SOF_PAY_FAILED,
    TransactionStatus.REFUND_FAILED,
    TransactionStatus.FRAUD_CHECK_FAILED,
    TransactionStatus.FRAUD_CHECK_DECLINED,
})


class Transaction(KeycloakBase):
    """Primary operational table. One row per remittance attempt."""

    __tablename__ = "transaction"
    __table_args__ = {"schema": "remittance"}

    internal_transaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    hub_id: Mapped[int | None] = mapped_column(BigInteger)
    hub_name: Mapped[str | None] = mapped_column(String(255))
    payment_reference_id: Mapped[str | None] = mapped_column(String(16))
    hub_transaction_id: Mapped[str | None] = mapped_column(String(16))
    hub_transaction_id_check: Mapped[str | None] = mapped_column(String(48))
    hub_transaction_id_submit: Mapped[str | None] = mapped_column(String(48))
    partner_transaction_id_check: Mapped[str | None] = mapped_column(String(48))
    partner_transaction_id_submit: Mapped[str | None] = mapped_column(String(48))
    hub_transaction_reference: Mapped[str | None] = mapped_column(Text)
    refund_reference_id: Mapped[str | None] = mapped_column(String(16))

    service_id: Mapped[int | None] = mapped_column(BigInteger)    # → remit_service
    service_name: Mapped[str | None] = mapped_column(String(255))
    service_type: Mapped[int | None] = mapped_column(SmallInteger)
    partner_id: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str | None] = mapped_column(String(50))

    # Sender — PII fields (mask in logs / AI prompts)
    sender_account_id: Mapped[str | None] = mapped_column(String(16))
    sender_msisdn: Mapped[str | None] = mapped_column(String(40))       # PII
    sender_fullname: Mapped[str | None] = mapped_column(String(356))    # PII
    sender_dob: Mapped[str | None] = mapped_column(String(32))          # PII
    sender_currency: Mapped[str | None] = mapped_column(String(32))
    sender_country: Mapped[str | None] = mapped_column(String(60))
    sender_country_of_residence: Mapped[str | None] = mapped_column(String(50))
    sender_nationality: Mapped[str | None] = mapped_column(String(50))
    sender_email: Mapped[str | None] = mapped_column(String(50))

    # Recipient — PII fields
    recipient_id: Mapped[str | None] = mapped_column(String(16))
    recipient_msisdn: Mapped[str | None] = mapped_column(String(40))    # PII
    recipient_fullname: Mapped[str | None] = mapped_column(String(356)) # PII
    recipient_currency: Mapped[str | None] = mapped_column(String(8))
    recipient_country: Mapped[str | None] = mapped_column(String(60))
    recipient_nationality: Mapped[str | None] = mapped_column(String(60))
    recipient_dob: Mapped[str | None] = mapped_column(String(32))       # PII
    recipient_pickup_code: Mapped[str | None] = mapped_column(String(256))

    # Amounts
    remittance_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    recipient_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    customer_key_in_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    currency_flag: Mapped[int | None] = mapped_column(SmallInteger)     # 0=source, 1=destination
    retail_fee: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    retail_tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))

    # FX
    hub_exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(24, 12))
    retail_exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(24, 12))
    markup_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    markup_fee: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    hub_gross_fee: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))

    # Error / hub status
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    hub_status_id: Mapped[str | None] = mapped_column(String)
    hub_status: Mapped[str | None] = mapped_column(String)
    hub_sub_status_id: Mapped[str | None] = mapped_column(String)
    hub_sub_status: Mapped[str | None] = mapped_column(String)
    hub_error_code: Mapped[str | None] = mapped_column(String)
    hub_error_message: Mapped[str | None] = mapped_column(Text)
    fraud_status: Mapped[str | None] = mapped_column(String(30))

    # Payment / SOF
    payment_mode: Mapped[str | None] = mapped_column(String(40))
    card_id: Mapped[str | None] = mapped_column(String(40))
    source_of_fund_ref_id: Mapped[str | None] = mapped_column(String(21))
    proxy_refund_status: Mapped[str | None] = mapped_column(String(20))

    # Misc
    device_id: Mapped[str | None] = mapped_column(String(64))
    external_service_id: Mapped[int | None] = mapped_column(Integer)
    reference_hub_name: Mapped[str | None] = mapped_column(String(32))
    remit_purpose_id: Mapped[str | None] = mapped_column(String(20))
    is_notify_sms_sender: Mapped[bool | None] = mapped_column(Boolean)

    # Audit
    created_date: Mapped[datetime | None] = mapped_column(DateTime)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime)
    version: Mapped[int | None] = mapped_column(Integer)


class TransactionAud(KeycloakBase):
    """Audit table — full history of every status change on a transaction."""

    __tablename__ = "transaction_aud"
    __table_args__ = {"schema": "remittance"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    internal_transaction_id: Mapped[int | None] = mapped_column(BigInteger)
    audit_date: Mapped[datetime | None] = mapped_column(DateTime)

    status: Mapped[str | None] = mapped_column(String(50))
    hub_status: Mapped[str | None] = mapped_column(String)
    hub_status_id: Mapped[str | None] = mapped_column(String)
    hub_sub_status: Mapped[str | None] = mapped_column(String)
    hub_sub_status_id: Mapped[str | None] = mapped_column(String)
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    hub_error_code: Mapped[str | None] = mapped_column(String)
    hub_error_message: Mapped[str | None] = mapped_column(Text)
    fraud_status: Mapped[str | None] = mapped_column(String(30))
    proxy_refund_status: Mapped[str | None] = mapped_column(String(20))
    created_date: Mapped[datetime | None] = mapped_column(DateTime)
    version: Mapped[int | None] = mapped_column(Integer)
