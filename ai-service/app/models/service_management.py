"""SQLAlchemy read models for ml_db — service_management (corridor configuration)."""

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, SmallInteger, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MlBase


class ExternalPartner(MlBase):
    """Hub/partner registry — TELEPIN, WU, THUNES, TRANGLO."""

    __tablename__ = "external_partner"
    __table_args__ = {"schema": "service_management"}

    external_partner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_partner_name: Mapped[str | None] = mapped_column(String(255))
    customer_names_input_required: Mapped[bool | None] = mapped_column(Boolean)


class RemitService(MlBase):
    """Core corridor definition — one row per sending/receiving country + operator + hub."""

    __tablename__ = "remit_service"
    __table_args__ = {"schema": "service_management"}

    remit_service_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_name: Mapped[str | None] = mapped_column(String(255))
    service_name_display: Mapped[str | None] = mapped_column(String(255))

    # Sending side
    local_currency: Mapped[str | None] = mapped_column(String(10))
    local_country_id: Mapped[int | None] = mapped_column(Integer)
    local_country_name: Mapped[str | None] = mapped_column(String(100))

    # Receiving side
    foreign_currency: Mapped[str | None] = mapped_column(String(10))
    foreign_country_id: Mapped[int | None] = mapped_column(Integer)
    foreign_country_name: Mapped[str | None] = mapped_column(String(100))

    # Hub linkage
    external_service_id: Mapped[int | None] = mapped_column(Integer)
    external_partner_id: Mapped[int | None] = mapped_column(Integer)
    reference_hub: Mapped[int | None] = mapped_column(Integer)
    mobile_operator_id: Mapped[int | None] = mapped_column(Integer)

    # Config
    status: Mapped[str | None] = mapped_column(String(10))        # ACTIVATE / INACTIVE
    service_type: Mapped[int | None] = mapped_column(Integer)     # 1=wallet, 2=bank, 3=wechat
    markup_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    markup_rate_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    payment_method: Mapped[str | None] = mapped_column(String(16))
    beneficiary_validation_required: Mapped[bool | None] = mapped_column(Boolean)
    beneficiary_auto_inclusion: Mapped[bool | None] = mapped_column(Boolean)
    is_available: Mapped[bool | None] = mapped_column(Boolean)
    time_check_required: Mapped[bool | None] = mapped_column(Boolean)
    active_time_start: Mapped[object | None] = mapped_column(Time)
    active_time_end: Mapped[object | None] = mapped_column(Time)


class RemitCorridorReference(MlBase):
    __tablename__ = "remit_corridor_reference"
    __table_args__ = {"schema": "service_management"}

    country_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referer_id: Mapped[str] = mapped_column(String, primary_key=True)
    payer_id: Mapped[str | None] = mapped_column(String)
    payer_type: Mapped[str | None] = mapped_column(String)   # BANK / WALLET / CASH_PICKUP
    service_id: Mapped[int | None] = mapped_column(Integer)
    external_partner_id: Mapped[int | None] = mapped_column(Integer)
    bene_validation_required: Mapped[bool | None] = mapped_column(Boolean)
    bene_transaction_validation_required: Mapped[bool | None] = mapped_column(Boolean)


class RemitServiceTierFee(MlBase):
    __tablename__ = "remit_service_tier_fee"
    __table_args__ = {"schema": "service_management"}

    remit_service_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(20, 9), primary_key=True)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    markup_fee: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
    markup_rate_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    retail_fee: Mapped[Decimal | None] = mapped_column(Numeric(20, 9))
