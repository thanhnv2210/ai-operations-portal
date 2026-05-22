"""In-memory reference data cache.

Loaded once at startup from ml_db. Provides O(1) lookups for IDs that appear
as foreign keys in remittance.transaction and customer.beneficiary.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_schema import Country, MobileOperator, IssuerMl, MlFxRates
from app.models.service_management import ExternalPartner, RemitService

log = logging.getLogger(__name__)


@dataclass
class CountryInfo:
    id: int
    country_name: str | None
    iso_code: str | None
    currency_iso: str | None


@dataclass
class OperatorInfo:
    id: int
    operator_id: int | None
    operator_name: str | None
    iso_code: str | None
    country_id: int | None


@dataclass
class ServiceInfo:
    remit_service_id: int
    system_name: str | None
    service_name_display: str | None
    external_partner_id: int | None
    foreign_country_name: str | None
    foreign_currency: str | None
    local_currency: str | None
    status: str | None
    is_available: bool | None


@dataclass
class PartnerInfo:
    external_partner_id: int
    external_partner_name: str | None


@dataclass
class ReferenceCache:
    # ml_schema lookups
    countries_by_id: dict[int, CountryInfo] = field(default_factory=dict)
    operators_by_id: dict[int, OperatorInfo] = field(default_factory=dict)
    operators_by_telepin_id: dict[int, OperatorInfo] = field(default_factory=dict)

    # service_management lookups
    services_by_id: dict[int, ServiceInfo] = field(default_factory=dict)
    partners_by_id: dict[int, PartnerInfo] = field(default_factory=dict)
    partners_by_name: dict[str, PartnerInfo] = field(default_factory=dict)

    @property
    def loaded(self) -> bool:
        return bool(self.partners_by_id)

    def country_name(self, country_id: int | None) -> str | None:
        if country_id is None:
            return None
        return self.countries_by_id.get(country_id, CountryInfo(country_id, None, None, None)).country_name

    def service_name(self, service_id: int | None) -> str | None:
        if service_id is None:
            return None
        svc = self.services_by_id.get(service_id)
        return svc.service_name_display or svc.system_name if svc else None

    def partner_name(self, partner_id: int | None) -> str | None:
        if partner_id is None:
            return None
        p = self.partners_by_id.get(partner_id)
        return p.external_partner_name if p else None


# Module-level singleton
_cache = ReferenceCache()


def get_cache() -> ReferenceCache:
    return _cache


async def load(ml_session: AsyncSession) -> None:
    """Populate the cache from ml_db. Called once during app lifespan startup."""
    global _cache

    log.info("Loading reference data cache from ml_db...")

    countries = (await ml_session.execute(select(Country))).scalars().all()
    _cache.countries_by_id = {
        c.id: CountryInfo(
            id=c.id,
            country_name=c.country_name,
            iso_code=c.country_iso_code,
            currency_iso=c.currency_iso,
        )
        for c in countries
    }

    operators = (await ml_session.execute(select(MobileOperator))).scalars().all()
    _cache.operators_by_id = {
        o.id: OperatorInfo(
            id=o.id,
            operator_id=o.operator_id,
            operator_name=o.operator_name,
            iso_code=o.iso_code,
            country_id=o.country_id,
        )
        for o in operators
    }
    _cache.operators_by_telepin_id = {
        o.operator_id: _cache.operators_by_id[o.id]
        for o in operators
        if o.operator_id is not None
    }

    services = (await ml_session.execute(select(RemitService))).scalars().all()
    _cache.services_by_id = {
        s.remit_service_id: ServiceInfo(
            remit_service_id=s.remit_service_id,
            system_name=s.system_name,
            service_name_display=s.service_name_display,
            external_partner_id=s.external_partner_id,
            foreign_country_name=s.foreign_country_name,
            foreign_currency=s.foreign_currency,
            local_currency=s.local_currency,
            status=s.status,
            is_available=s.is_available,
        )
        for s in services
    }

    partners = (await ml_session.execute(select(ExternalPartner))).scalars().all()
    _cache.partners_by_id = {
        p.external_partner_id: PartnerInfo(
            external_partner_id=p.external_partner_id,
            external_partner_name=p.external_partner_name,
        )
        for p in partners
    }
    _cache.partners_by_name = {
        p.external_partner_name: _cache.partners_by_id[p.external_partner_id]
        for p in partners
        if p.external_partner_name is not None
    }

    log.info(
        "Cache loaded: %d countries, %d operators, %d services, %d partners",
        len(_cache.countries_by_id),
        len(_cache.operators_by_id),
        len(_cache.services_by_id),
        len(_cache.partners_by_id),
    )
