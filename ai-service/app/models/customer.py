"""SQLAlchemy read models for keycloak — customer schema."""

from sqlalchemy import Boolean, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import KeycloakBase


class Beneficiary(KeycloakBase):
    """Saved recipient profiles per sender."""

    __tablename__ = "beneficiary"
    __table_args__ = {"schema": "customer"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bene_id: Mapped[str | None] = mapped_column(String)            # Telepin beneficiary ID
    sender_account_id: Mapped[str | None] = mapped_column(String)

    # Name — PII
    bene_first_name: Mapped[str | None] = mapped_column(String)    # PII
    bene_last_name: Mapped[str | None] = mapped_column(String)     # PII
    bene_full_name: Mapped[str | None] = mapped_column(String)     # PII
    sender_first_name: Mapped[str | None] = mapped_column(String)  # PII
    sender_last_name: Mapped[str | None] = mapped_column(String)   # PII

    # Contact / account — PII
    benemsisdn: Mapped[str | None] = mapped_column(String)         # PII
    bene_bank_acct_no: Mapped[str | None] = mapped_column(String)  # PII
    wallet_account_number: Mapped[str | None] = mapped_column(String)  # PII

    # Destination
    receiving_country: Mapped[int | None] = mapped_column(Integer) # FK → country.id
    mobile_operator: Mapped[int | None] = mapped_column(Integer)   # Telepin operator_id
    issuer_id: Mapped[int | None] = mapped_column(Integer)
    issuer_alternative_id: Mapped[int | None] = mapped_column(Integer)
    branch_code: Mapped[str | None] = mapped_column(String)
    bank_acc_type_flag: Mapped[bool | None] = mapped_column(Boolean)  # true=savings

    # Purpose / relationship
    remit_purpose: Mapped[str | None] = mapped_column(String)
    remit_purpose_note: Mapped[str | None] = mapped_column(Text)
    cust_relationship: Mapped[str | None] = mapped_column(String)

    # Identity — PII
    nationality: Mapped[str | None] = mapped_column(String)
    dob: Mapped[str | None] = mapped_column(String)                # PII
    birth_place: Mapped[str | None] = mapped_column(String)
    gender: Mapped[str | None] = mapped_column(String)

    # Address
    bene_address: Mapped[str | None] = mapped_column(Text)
    province_id: Mapped[int | None] = mapped_column(Integer)
    city_id: Mapped[int | None] = mapped_column(Integer)
    postal_code: Mapped[str | None] = mapped_column(String)

    # Status
    status: Mapped[str | None] = mapped_column(String)             # ACTIVE / INACTIVE / DELETED
    status_remark: Mapped[str | None] = mapped_column(Text)
    warning_message: Mapped[str | None] = mapped_column(Text)
    sys_flag: Mapped[int | None] = mapped_column(SmallInteger)
    old_bene_id: Mapped[str | None] = mapped_column(String)


class BeneficiaryService(KeycloakBase):
    """Links a beneficiary to a specific remit service with validation status."""

    __tablename__ = "beneficiary_service"
    __table_args__ = {"schema": "customer"}

    ml_bene_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_account_id: Mapped[str | None] = mapped_column(String)
    ml_operator_id: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str | None] = mapped_column(String)  # PENDING / VALID / INVALID
    validation_state_partner_response: Mapped[str | None] = mapped_column(Text)
    referer_id: Mapped[str | None] = mapped_column(String)
