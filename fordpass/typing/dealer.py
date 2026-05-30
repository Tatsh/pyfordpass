"""Dealer-lookup response shape."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ('DealerResponse',)


class DealerResponse(TypedDict, total=False):
    """Top-level shape of the dealer-by-PA-code response."""

    paCode: str
    """Dealer PA code. Populated even when the upstream returns no hydrated detail."""
    request_time: str
    """ISO-8601 timestamp the upstream service stamped the response with."""
    status: Mapping[str, object]
    """Upstream status envelope."""
