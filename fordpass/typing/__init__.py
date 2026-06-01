"""
Public typing surface for FordPass response and config shapes.

Internal pyfordpass code imports from the specific submodule (e.g.
:py:mod:`fordpass.typing.service`); this ``__init__`` exists purely so external consumers can
``from fordpass.typing import X`` without knowing the internal categorisation.
"""
from __future__ import annotations

from fordpass.typing.alerts import (
    AlertCategory,
    AlertColorCode,
    AlertEntry,
    AlertHistoryEntry,
    AlertHistoryResponse,
    AlertPrognostics,
    AlertUrgency,
    AlertsResponse,
)
from fordpass.typing.api_config import (
    APIConfig,
    APIConfigAuth,
    APIConfigB2C,
    APIConfigHosts,
    APIConfigRoadside,
    APIConfigTMC,
)
from fordpass.typing.auth import B2CTokenResponse, CATTokenResponse, TMCTokenResponse
from fordpass.typing.commands import AckResponse
from fordpass.typing.common import (
    CompassDirection,
    CountryHeaderCasing,
    DistanceUnit,
    EngineType,
    GPSPosition,
    TemperatureUnit,
    TokenType,
    UserAuthStatus,
    VehicleBrand,
)
from fordpass.typing.config import (
    Config,
    HTTPConfig,
    OutputConfig,
    OutputFormat,
    UnitsConfig,
    VehicleConfig,
)
from fordpass.typing.dealer import DealerResponse
from fordpass.typing.departure import (
    DepartureDayOfWeek,
    DepartureScheduleDay,
    DepartureScheduleSlot,
    PreconditionTemperature,
    ScheduleStatus,
    TimeOfDay,
)
from fordpass.typing.drivers import (
    DriverEntry,
    DriversCountResponse,
    DriversListResponse,
    InviteResponse,
)
from fordpass.typing.electrification import (
    ChargeMode,
    ChargeSettings,
    EnergyTransferLogsResponse,
    EnergyTransferStatusResponse,
    PreferredChargeTimesResponse,
)
from fordpass.typing.guard import GuardModeResponse
from fordpass.typing.lighting import ZONE_LIGHT_OFF, ZoneLightZone
from fordpass.typing.messages import MessageEntry, MessagesResponse, MessagesResultEnvelope
from fordpass.typing.profile import (
    ProfileAddress,
    ProfileCountry,
    ProfileEmails,
    ProfileLanguages,
    ProfileNames,
    ProfileNamesExtension,
    ProfilePhoneNumbers,
    ProfileResponse,
    ProfileUnitsOfMeasure,
    SaveProfileFields,
)
from fordpass.typing.rcc import (
    RCC_PREFERENCE_KEYS,
    RCCPreference,
    RCCPreferenceKey,
    RCCProfile,
    RCCSeatLevel,
    RCCToggle,
)
from fordpass.typing.release import ReleaseNotesResponse
from fordpass.typing.roadside import IDNameEntry, IDNameListResponse, RoadsideActiveResponse
from fordpass.typing.schedule import ScheduleEntry, SchedulesEnvelope, SchedulesResponse
from fordpass.typing.service import (
    CompletedServiceActionDetail,
    MaintenanceDetails,
    MaintenanceItem,
    RecallItem,
    ServiceActionDetail,
    ServicePerformed,
    ServicePlannerResponse,
)
from fordpass.typing.telemetry import (
    DepartureSchedule,
    MetricEntry,
    MetricValue,
    TelemetryResponse,
    TirePressureEntry,
)
from fordpass.typing.vehicle import (
    GarageVehicle,
    VehicleCapabilities,
    VehicleProfile,
    VehicleUserRoles,
)

__all__ = (
    'RCC_PREFERENCE_KEYS',
    'ZONE_LIGHT_OFF',
    'APIConfig',
    'APIConfigAuth',
    'APIConfigB2C',
    'APIConfigHosts',
    'APIConfigRoadside',
    'APIConfigTMC',
    'AckResponse',
    'AlertCategory',
    'AlertColorCode',
    'AlertEntry',
    'AlertHistoryEntry',
    'AlertHistoryResponse',
    'AlertPrognostics',
    'AlertUrgency',
    'AlertsResponse',
    'B2CTokenResponse',
    'CATTokenResponse',
    'ChargeMode',
    'ChargeSettings',
    'CompassDirection',
    'CompletedServiceActionDetail',
    'Config',
    'CountryHeaderCasing',
    'DealerResponse',
    'DepartureDayOfWeek',
    'DepartureSchedule',
    'DepartureScheduleDay',
    'DepartureScheduleSlot',
    'DistanceUnit',
    'DriverEntry',
    'DriversCountResponse',
    'DriversListResponse',
    'EnergyTransferLogsResponse',
    'EnergyTransferStatusResponse',
    'EngineType',
    'GPSPosition',
    'GarageVehicle',
    'GuardModeResponse',
    'HTTPConfig',
    'IDNameEntry',
    'IDNameListResponse',
    'InviteResponse',
    'MaintenanceDetails',
    'MaintenanceItem',
    'MessageEntry',
    'MessagesResponse',
    'MessagesResultEnvelope',
    'MetricEntry',
    'MetricValue',
    'OutputConfig',
    'OutputFormat',
    'PreconditionTemperature',
    'PreferredChargeTimesResponse',
    'ProfileAddress',
    'ProfileCountry',
    'ProfileEmails',
    'ProfileLanguages',
    'ProfileNames',
    'ProfileNamesExtension',
    'ProfilePhoneNumbers',
    'ProfileResponse',
    'ProfileUnitsOfMeasure',
    'RCCPreference',
    'RCCPreferenceKey',
    'RCCProfile',
    'RCCSeatLevel',
    'RCCToggle',
    'RecallItem',
    'ReleaseNotesResponse',
    'RoadsideActiveResponse',
    'SaveProfileFields',
    'ScheduleEntry',
    'ScheduleStatus',
    'SchedulesEnvelope',
    'SchedulesResponse',
    'ServiceActionDetail',
    'ServicePerformed',
    'ServicePlannerResponse',
    'TMCTokenResponse',
    'TelemetryResponse',
    'TemperatureUnit',
    'TimeOfDay',
    'TirePressureEntry',
    'TokenType',
    'UnitsConfig',
    'UserAuthStatus',
    'VehicleBrand',
    'VehicleCapabilities',
    'VehicleConfig',
    'VehicleProfile',
    'VehicleUserRoles',
    'ZoneLightZone',
)
