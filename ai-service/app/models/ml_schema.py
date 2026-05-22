"""SQLAlchemy read models for ml_db — ml_schema (reference/master data)."""

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import MlBase


class Country(MlBase):
    __tablename__ = "country"
    __table_args__ = {"schema": "ml_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_id: Mapped[int | None] = mapped_column(Integer)
    country_name: Mapped[str | None] = mapped_column(String(50))
    country_iso_code: Mapped[str | None] = mapped_column(String(3))
    isd_code: Mapped[str | None] = mapped_column(String(3))
    currency_iso: Mapped[str | None] = mapped_column(String(5))


class MobileOperator(MlBase):
    __tablename__ = "mobile_operator"
    __table_args__ = {"schema": "ml_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[int | None] = mapped_column(Integer)
    operator_name: Mapped[str | None] = mapped_column(String(128))
    operator_name_hiapp: Mapped[str | None] = mapped_column(String(148))
    iso_code: Mapped[str | None] = mapped_column(String(3))
    country_id: Mapped[int | None] = mapped_column(Integer)
    country_name: Mapped[str | None] = mapped_column(String(25))
    operator_code: Mapped[str | None] = mapped_column(String)
    default_issuer_id: Mapped[int | None] = mapped_column(Integer)


class IssuerMl(MlBase):
    """ML-owned issuer table (IDs from 10000+). See also ml_schema.issuer for Telepin-sourced."""

    __tablename__ = "issuer_ml"
    __table_args__ = {"schema": "ml_schema"}

    issuer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issuer_name: Mapped[str | None] = mapped_column(String(100))
    mobile_operator_id: Mapped[int | None] = mapped_column(Integer)
    country_id: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool | None] = mapped_column(Boolean)


class MlFxRates(MlBase):
    __tablename__ = "ml_fx_rates"
    __table_args__ = {"schema": "ml_schema"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[str | None] = mapped_column(String(20))
    from_currency: Mapped[str | None] = mapped_column(String(20))
    to_currency: Mapped[str | None] = mapped_column(String(20))
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(24, 12))
    service_id: Mapped[int | None] = mapped_column(Integer)
    receiving_country_id: Mapped[str | None] = mapped_column(String(20))


class ReceivingCountry(MlBase):
    __tablename__ = "receiving_countries"
    __table_args__ = {"schema": "ml_schema"}

    country_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[str] = mapped_column(String(25), primary_key=True)
    iso_code: Mapped[str | None] = mapped_column(String(3))
    active_flag: Mapped[bool | None] = mapped_column(Boolean)


class HubServiceData(MlBase):
    """Maps hub payer codes to hub_id per country (ml_r_hub_service_data)."""

    __tablename__ = "ml_r_hub_service_data"
    __table_args__ = {"schema": "ml_schema"}

    payer_type: Mapped[str] = mapped_column(String, primary_key=True)
    payer_value: Mapped[str] = mapped_column(String, primary_key=True)
    country_iso_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    hub_id: Mapped[int | None] = mapped_column(Integer)
    payer_name: Mapped[str | None] = mapped_column(Text)
