"""Schema for the ``abcdef.toml`` FordPass API constants bundle."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ('Secrets', 'SecretsAuth', 'SecretsB2C', 'SecretsHosts', 'SecretsRoadside', 'SecretsTMC')


class Secrets(TypedDict):
    """Top-level shape of ``abcdef.toml`` (FordPass API constants)."""

    application_id: str
    """Value of the ``application-id`` / ``Application-Id`` header on Ford-plane calls."""
    auth: SecretsAuth
    """OAuth / token-exchange parameter groups."""
    hosts: SecretsHosts
    """Per-tier base URLs."""
    profile_groups_default: str
    """Default ``profileGroups`` query value for the user-profile lookup."""
    roadside: SecretsRoadside
    """Roadside-assistance per-brand parameters."""
    user_agent: str
    """``User-Agent`` string the official mobile app emits on every API call."""


class SecretsAuth(TypedDict):
    """OAuth / token-exchange parameter groups."""

    b2c: SecretsB2C
    """Azure AD B2C settings."""
    tmc: SecretsTMC
    """TMC settings."""


class SecretsB2C(TypedDict):
    """Azure AD B2C identity-provider parameters."""

    client_id: str
    """OAuth2 ``client_id`` for the FordPass mobile-app B2C registration."""
    policy_template: str
    """``str.format`` template for the B2C user-flow name (``{locale}`` placeholder)."""
    redirect_uri: str
    """Native-app deep link used as the PKCE ``redirect_uri``."""
    tenant_id: str
    """Azure tenant ID owning the FordPass custom policies."""


class SecretsHosts(TypedDict):
    """Per-tier hostnames used by the FordPass API."""

    foundational: str
    """Base URL for the Foundational service (CAT mint, profile, message centre)."""
    login: str
    """Base URL for the Azure AD B2C login tenant."""
    tmc: str
    """Base URL for the TMC control plane (commands + telemetry)."""
    tmc_accounts: str
    """Base URL for the TMC token-exchange service."""
    vehicle: str
    """Base URL for the vehicle service (commands, telemetry alerts, SRSM, ...)."""


class SecretsRoadside(TypedDict):
    """Roadside-assistance per-brand parameters."""

    x_source: Mapping[str, str]
    """Brand name (lowercase) → ``x-source`` header value."""


class SecretsTMC(TypedDict):
    """TMC token-exchange parameters."""

    client_id: str
    """OAuth2 ``client_id`` sent on RFC 8693 token-exchange to mint the TMC bearer."""
