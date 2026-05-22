from sqlalchemy.orm import DeclarativeBase


class MlBase(DeclarativeBase):
    """Base for all ml_db models (ml_schema + service_management)."""


class KeycloakBase(DeclarativeBase):
    """Base for all keycloak DB models (remittance, customer, payment, portal, ekyc)."""
