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
from fordpass.typing.drivers import (
    DriverEntry,
    DriversCountResponse,
    DriversListResponse,
    InviteResponse,
)
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
from fordpass.typing.release import ReleaseNotesResponse
from fordpass.typing.roadside import IDNameEntry, IDNameListResponse, RoadsideActiveResponse
from fordpass.typing.schedule import ScheduleEntry, SchedulesEnvelope, SchedulesResponse
from fordpass.typing.secrets import (
    Secrets,
    SecretsAuth,
    SecretsB2C,
    SecretsHosts,
    SecretsRoadside,
    SecretsTMC,
)
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

__all__ = ('AckResponse', 'AlertCategory', 'AlertColorCode', 'AlertEntry', 'AlertHistoryEntry',
           'AlertHistoryResponse', 'AlertPrognostics', 'AlertUrgency', 'AlertsResponse',
           'B2CTokenResponse', 'CATTokenResponse', 'CompassDirection',
           'CompletedServiceActionDetail', 'Config', 'CountryHeaderCasing', 'DealerResponse',
           'DepartureSchedule', 'DistanceUnit', 'DriverEntry', 'DriversCountResponse',
           'DriversListResponse',
           'EngineType', 'GPSPosition', 'GarageVehicle', 'HTTPConfig', 'IDNameEntry',
           'IDNameListResponse', 'InviteResponse', 'MaintenanceDetails', 'MaintenanceItem',
           'MessageEntry', 'MessagesResponse', 'MessagesResultEnvelope', 'MetricEntry',
           'MetricValue', 'OutputConfig', 'OutputFormat', 'ProfileAddress', 'ProfileCountry',
           'ProfileEmails', 'ProfileLanguages', 'ProfileNames', 'ProfileNamesExtension',
           'ProfilePhoneNumbers', 'ProfileResponse', 'ProfileUnitsOfMeasure', 'RecallItem',
           'ReleaseNotesResponse', 'RoadsideActiveResponse', 'SaveProfileFields', 'ScheduleEntry',
           'SchedulesEnvelope', 'SchedulesResponse', 'Secrets', 'SecretsAuth', 'SecretsB2C',
           'SecretsHosts', 'SecretsRoadside', 'SecretsTMC', 'ServiceActionDetail',
           'ServicePerformed', 'ServicePlannerResponse', 'TMCTokenResponse', 'TelemetryResponse',
           'TemperatureUnit', 'TirePressureEntry', 'TokenType', 'UnitsConfig', 'UserAuthStatus',
           'VehicleBrand', 'VehicleCapabilities', 'VehicleConfig', 'VehicleProfile',
           'VehicleUserRoles')
