"""Token / OAuth response shapes (B2C, CAT, TMC)."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from fordpass.typing.common import TokenType

__all__ = ('B2CTokenResponse', 'CATTokenResponse', 'TMCTokenResponse')


class B2CTokenResponse(TypedDict, total=False):
    """Body returned by the Azure AD B2C ``/oauth2/v2.0/token`` endpoint."""

    access_token: str
    """B2C access token (used as the ``idpToken`` for the CAT mint)."""
    expires_in: int
    """Access-token lifetime in seconds."""
    expires_on: int
    """Token expiry time (epoch seconds)."""
    id_token: str
    """OpenID Connect ID token."""
    not_before: int
    """Token validity start time (epoch seconds)."""
    refresh_token: str
    """B2C refresh token."""
    resource: str
    """Audience the token was issued for."""
    scope: str
    """Space-separated scope list."""
    token_type: TokenType
    """Always ``Bearer``."""


class CATTokenResponse(TypedDict, total=False):
    """Body returned by the CAT-mint and CAT-refresh endpoints."""

    access_token: str
    """Newly-minted CAT access token (EdDSA JWT, ``token_type=A``)."""
    expires_in: int
    """Access-token lifetime in seconds."""
    refresh_token: str
    """Newly-minted CAT refresh token (EdDSA JWT, ``token_type=R``)."""


class TMCTokenResponse(TypedDict, total=False):
    """Body returned by the TMC token-exchange endpoint."""

    access_token: str
    """Newly-minted TMC bearer (RS256 JWT)."""
    expires_in: int
    """Bearer lifetime in seconds."""
    issued_token_type: str
    """RFC 8693 issued-token-type URI."""
    token_type: TokenType
    """Always ``Bearer``."""
