"""Message-centre inbox response shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ('MessageEntry', 'MessagesResponse', 'MessagesResultEnvelope')


class MessageEntry(TypedDict, total=False):
    """One entry in the message-centre inbox."""

    contentType: str
    """``'Html'`` or ``'Text'``."""
    createdDate: str
    """Local-time timestamp the message was created."""
    highlighted: bool
    """Whether the HMI should highlight the message."""
    id: str
    """Server-assigned message identifier (string form)."""
    isRead: bool
    """Whether the message has been read."""
    messageBody: str
    """Body text."""
    messageId: str
    """Numeric message identifier (string form). Required for delete / mark-read."""
    messageSubject: str
    """Subject line."""
    messageType: str
    """Upstream message-type name (``'EXTERNALNOTIFICATIONREQUEST'``, …)."""
    messageTypeId: int
    """Upstream numeric message-type identifier."""
    metadata: str
    """Per-template metadata as a JSON-encoded string."""
    priority: int
    """Upstream priority hint (1 = highest)."""
    relevantVin: str
    """VIN the message relates to, if any."""
    templateID: str | None
    """Upstream template identifier; commonly ``None``."""


class MessagesResponse(TypedDict, total=False):
    """Top-level shape of the message-centre inbox response."""

    result: MessagesResultEnvelope
    """Wrapper containing ``lastFetchedTime`` and ``messages``."""


class MessagesResultEnvelope(TypedDict, total=False):
    """Inner ``result`` envelope of the message-centre response."""

    lastFetchedTime: str
    """ISO-8601 timestamp when the server last refreshed the inbox."""
    messages: Sequence[MessageEntry]
    """The inbox entries."""
