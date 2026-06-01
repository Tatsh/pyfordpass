"""Remote Climate Control (RCC) profile shapes (EV/PHEV and supported ICE)."""
from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict

__all__ = ('RCC_PREFERENCE_KEYS', 'RCCPreference', 'RCCPreferenceKey', 'RCCProfile', 'RCCSeatLevel',
           'RCCToggle')

RCCPreferenceKey: TypeAlias = Literal['RccHeatedWindshield_Rq', 'RccRearDefrost_Rq',
                                      'RccHeatedSteeringWheel_Rq', 'RccLeftFrontClimateSeat_Rq',
                                      'RccLeftRearClimateSeat_Rq', 'RccRightFrontClimateSeat_Rq',
                                      'RccRightRearClimateSeat_Rq', 'SetPointTemp_Rq']
"""Closed set of ``preferenceType`` keys the RCC profile recognises.

``SetPointTemp_Rq`` carries a temperature encoded as ``XX_Y`` (see
:py:func:`fordpass.utils.encode_rcc_temperature`); every other key carries either an
:py:data:`RCCToggle` or an :py:data:`RCCSeatLevel` string.

:meta hide-value:
"""

RCCSeatLevel: TypeAlias = Literal['Off', 'Low', 'Medium', 'High']
"""Intensity for the four heated/cooled climate-seat keys.

:meta hide-value:
"""

RCCToggle: TypeAlias = Literal['Off', 'On']
"""Binary value for the heated-windshield, rear-defrost, and heated-steering-wheel keys.

ha-fordpass treats these three keys as ``On`` / ``Off`` rather than the four-level seat scale.

:meta hide-value:
"""

RCC_PREFERENCE_KEYS: tuple[RCCPreferenceKey,
                           ...] = ('RccHeatedWindshield_Rq', 'RccRearDefrost_Rq',
                                   'RccHeatedSteeringWheel_Rq', 'RccLeftFrontClimateSeat_Rq',
                                   'RccLeftRearClimateSeat_Rq', 'RccRightFrontClimateSeat_Rq',
                                   'RccRightRearClimateSeat_Rq', 'SetPointTemp_Rq')
"""Every recognised :py:data:`RCCPreferenceKey`, used to validate a sparse write.

:meta hide-value:
"""


class RCCPreference(TypedDict):
    """One saved Remote Climate Control preference pair."""

    preferenceType: str
    """Closed-set key naming the preference (an :py:data:`RCCPreferenceKey` value)."""
    preferenceValue: str
    """String-encoded value; an enum string, a toggle, or an ``XX_Y`` temperature."""


class RCCProfile(TypedDict, total=False):
    """Body returned by the RCC status endpoint."""

    rccUserProfiles: list[RCCPreference]
    """The saved preference pairs; empty or absent when no profile has been created."""
