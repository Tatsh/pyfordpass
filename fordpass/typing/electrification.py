"""EV charging (electrification) request and response shapes."""
from __future__ import annotations

from typing import Any, Literal, TypeAlias, TypedDict

__all__ = ('ChargeMode', 'ChargeSettings', 'EnergyTransferLogsResponse',
           'EnergyTransferStatusResponse', 'PreferredChargeTimesResponse')

ChargeMode: TypeAlias = Literal['CHARGE_DT', 'CHARGE_DT_COND', 'CHARGE_NOW', 'CHARGE_SOLD',
                                'HOME_CHARGE_DISCHARGE', 'HOME_CHARGE_NOW', 'HOME_STORE_CHARGE',
                                'VALUE_CHARGE']
"""
Charging-mode value accepted by ``chargeMode`` in :py:class:`ChargeSettings`.

:meta hide-value:
"""

PreferredChargeTimesResponse: TypeAlias = dict[str, Any]
"""
Preferred-charge-times response.

Loosely typed: the upstream shape varies by region and firmware, so it is exposed as a plain
mapping rather than a fixed schema.

:meta hide-value:
"""

EnergyTransferStatusResponse: TypeAlias = dict[str, Any]
"""
Energy-transfer status response.

Loosely typed and frequently empty (the endpoint only returns data while the vehicle is at a
known charge location).

:meta hide-value:
"""


class ChargeSettings(TypedDict, total=False):
    """
    EV charge-settings payload sent under ``properties.chargeSettings``.

    All keys are optional; send only those being changed.
    """

    autoChargePortUnlock: str
    """Charge-port auto-unlock toggle (``'ON'`` / ``'OFF'``)."""
    chargeMode: ChargeMode
    """Charging mode (see :py:data:`ChargeMode`)."""
    globalCurrentLimit: int
    """AC current limit in amperes."""
    globalDCPowerLimit: int
    """DC power limit in kilowatts."""
    globalDCTargetSoc: int
    """DC fast-charge target state-of-charge percentage."""
    globalReserveSoc: int
    """Reserve state-of-charge percentage."""
    globalTargetSoc: int
    """AC charge target state-of-charge percentage."""


class EnergyTransferLogsResponse(TypedDict, total=False):
    """Energy-transfer logs response envelope."""

    energyTransferLogs: list[dict[str, Any]]
    """The list of energy-transfer log records (newest first)."""
