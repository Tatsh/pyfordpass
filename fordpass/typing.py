"""Shared typing helpers for the FordPass package."""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = (
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
    'CompassDirection',
    'Config',
    'DealerResponse',
    'DistanceUnit',
    'DriverEntry',
    'DriversCountResponse',
    'DriversListResponse',
    'EngineType',
    'GPSPosition',
    'GarageVehicle',
    'IDNameEntry',
    'IDNameListResponse',
    'InviteResponse',
    'MessageEntry',
    'MessagesResponse',
    'MessagesResultEnvelope',
    'MetricEntry',
    'MetricValue',
    'OutputConfig',
    'OutputFormat',
    'ProfileAddress',
    'ProfileCountry',
    'ProfileEmails',
    'ProfileLanguages',
    'ProfileNames',
    'ProfileNamesExtension',
    'ProfilePhoneNumbers',
    'ProfileResponse',
    'ProfileUnitsOfMeasure',
    'ReleaseNotesResponse',
    'RoadsideActiveResponse',
    'ScheduleEntry',
    'SchedulesEnvelope',
    'SchedulesResponse',
    'Secrets',
    'SecretsAuth',
    'SecretsB2C',
    'SecretsHosts',
    'SecretsRoadside',
    'SecretsTMC',
    'ServicePlannerResponse',
    'TMCTokenResponse',
    'TelemetryResponse',
    'TemperatureUnit',
    'TirePressureEntry',
    'TokenType',
    'UnitsConfig',
    'UserAuthStatus',
    'VehicleBrand',
    'VehicleCapabilities',
    'VehicleConfig',
    'VehicleProfile',
    'VehicleUserRoles',
)

DistanceUnit: TypeAlias = Literal['km', 'mi']
"""Preferred distance unit.

:meta hide-value:
"""

CompassDirection: TypeAlias = Literal['NORTH', 'NORTHEAST', 'EAST', 'SOUTHEAST', 'SOUTH',
                                      'SOUTHWEST', 'WEST', 'NORTHWEST']
"""One of the eight cardinal/intercardinal directions reported by ``compassDirection``.

:meta hide-value:
"""

AlertUrgency: TypeAlias = Literal['N', 'M', 'H']
"""Alert urgency code: ``N`` (normal), ``M`` (medium), or ``H`` (high).

:meta hide-value:
"""

AlertColorCode: TypeAlias = Literal['A', 'Y', 'R']
"""Display colour code for an alert tile: amber, yellow, or red.

:meta hide-value:
"""

AlertCategory: TypeAlias = Literal['Prognostics', 'Diagnostics']
"""Top-level alert category.

:meta hide-value:
"""

UserAuthStatus: TypeAlias = Literal['Authorized', 'Pending', 'Declined']
"""User-authorisation status on a vehicle.

:meta hide-value:
"""

EngineType: TypeAlias = Literal['ICE', 'BEV', 'PHEV', 'HEV', 'FCV']
"""Powertrain category: internal-combustion, battery EV, plug-in hybrid, etc.

:meta hide-value:
"""

VehicleBrand: TypeAlias = Literal['Ford', 'Lincoln']
"""Marketing brand of a vehicle.

:meta hide-value:
"""

TokenType: TypeAlias = Literal['Bearer']
"""OAuth-style ``token_type`` echoed in token responses.

:meta hide-value:
"""

OutputFormat: TypeAlias = Literal['json', 'pretty']
"""Preferred output format for multi-value command responses.

:meta hide-value:
"""

TemperatureUnit: TypeAlias = Literal['C', 'F']
"""Preferred temperature unit (Celsius / Fahrenheit).

:meta hide-value:
"""


class UnitsConfig(TypedDict, total=False):
    """Unit preferences read from the user's ``config.toml``."""

    distance: DistanceUnit
    """Preferred distance unit: ``'mi'`` (miles) or ``'km'`` (kilometres)."""
    temperature: TemperatureUnit
    """Preferred temperature unit: ``'F'`` (Fahrenheit) or ``'C'`` (Celsius)."""


class VehicleConfig(TypedDict, total=False):
    """Vehicle-related preferences read from ``[vehicle]``."""

    default_vin: str
    """Fallback VIN used when the CLI ``VIN`` argument is omitted."""


class OutputConfig(TypedDict, total=False):
    """Output-format preferences read from ``[output]``."""

    format: OutputFormat
    """``'pretty'`` (Rich tables; default) or ``'json'`` (machine-readable)."""


class Config(TypedDict, total=False):
    """Persistent CLI configuration loaded from ``~/.config/fordpass/config.toml``."""

    output: OutputConfig
    """Output-format preferences."""
    units: UnitsConfig
    """Display-unit preferences."""
    vehicle: VehicleConfig
    """Vehicle-related defaults (such as the fallback VIN)."""


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


class SecretsTMC(TypedDict):
    """TMC token-exchange parameters."""

    client_id: str
    """OAuth2 ``client_id`` sent on RFC 8693 token-exchange to mint the TMC bearer."""


class SecretsAuth(TypedDict):
    """OAuth / token-exchange parameter groups."""

    b2c: SecretsB2C
    """Azure AD B2C settings."""
    tmc: SecretsTMC
    """TMC settings."""


class SecretsRoadside(TypedDict):
    """Roadside-assistance per-brand parameters."""

    x_source: dict[str, str]
    """Brand name (lowercase) → ``x-source`` header value."""


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


# ---- API response shapes ---------------------------------------------------


class B2CTokenResponse(TypedDict, total=False):
    """Body returned by the Azure AD B2C ``/oauth2/v2.0/token`` endpoint."""

    access_token: str
    """B2C access token (used as the ``idpToken`` for the CAT mint)."""
    refresh_token: str
    """B2C refresh token."""
    id_token: str
    """OpenID Connect ID token."""
    expires_in: int
    """Access-token lifetime in seconds."""
    not_before: int
    """Token validity start time (epoch seconds)."""
    expires_on: int
    """Token expiry time (epoch seconds)."""
    resource: str
    """Audience the token was issued for."""
    token_type: TokenType
    """Always ``Bearer``."""
    scope: str
    """Space-separated scope list."""


class CATTokenResponse(TypedDict, total=False):
    """Body returned by the CAT-mint and CAT-refresh endpoints."""

    access_token: str
    """Newly-minted CAT access token (EdDSA JWT, ``token_type=A``)."""
    refresh_token: str
    """Newly-minted CAT refresh token (EdDSA JWT, ``token_type=R``)."""
    expires_in: int
    """Access-token lifetime in seconds."""


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


class GPSPosition(TypedDict, total=False):
    """Normalised GPS payload returned by :py:func:`fordpass.utils.extract_position`."""

    lat: float
    """Latitude in decimal degrees."""
    lon: float
    """Longitude in decimal degrees."""
    alt: float
    """Altitude in metres above the WGS-84 ellipsoid."""
    heading: float
    """Heading in degrees (``0`` = north, ``90`` = east)."""
    compass: CompassDirection
    """Cardinal direction (``'NORTH'``, ``'NORTHEAST'``, …)."""
    update_time: str
    """ISO-8601 timestamp of the fix."""


class TirePressureEntry(TypedDict, total=False):
    """One entry in the per-wheel tire-pressure list."""

    oemCorrelationId: str
    """Upstream correlation id."""
    updateTime: str
    """ISO-8601 timestamp of the reading."""
    value: float
    """Current pressure in kilopascals."""
    vehicleWheel: str
    """Wheel identifier (``'FRONT_LEFT'``, ``'REAR_RIGHT'``, …)."""
    wheelPlacardFront: float
    """Manufacturer-recommended front pressure (kPa)."""
    wheelPlacardRear: float
    """Manufacturer-recommended rear pressure (kPa)."""


MetricValue: TypeAlias = (
    'str | int | float | bool | Mapping[str, "MetricValue"] | Sequence["MetricValue"] | None')
"""Recursive type for one telemetry metric's ``value`` field.

The TMC service emits primitives, nested objects (position, heading,
acceleration, configurations, indicators), and lists (per-wheel tire data,
per-door / per-seat status). This union exhaustively models the shape without
falling back to :py:class:`Any`.

:meta hide-value:
"""


class MetricEntry(TypedDict, total=False):
    """Shared envelope around a single telemetry metric's value + provenance."""

    value: MetricValue
    """The metric's value (scalar, nested object, or list — see :data:`MetricValue`)."""
    updateTime: str
    """ISO-8601 timestamp of the reading."""
    oemCorrelationId: str
    """Upstream correlation id."""
    tags: list[str]
    """Optional tags attached to the reading."""


class TelemetryResponse(TypedDict, total=False):
    """Top-level shape of the telemetry-query response.

    Only the always-present envelope keys are listed; ``metrics`` is keyed by
    metric name and the value side follows :py:class:`MetricEntry` (most metrics)
    or :py:class:`list[MetricEntry]` (per-instance metrics like tires, doors,
    seats).
    """

    vin: str
    """The queried VIN."""
    vehicleId: str
    """TMC-internal vehicle identifier."""
    updateTime: str
    """ISO-8601 timestamp of the snapshot."""
    metrics: Mapping[str, MetricEntry | Sequence[MetricEntry]]
    """Per-metric values (e.g. ``odometer``, ``fuelLevel``, ``tirePressure``)."""
    events: Mapping[str, MetricEntry]
    """Per-event values (e.g. ``automaticSoftwareUpdateUserSettingsEvent``)."""
    states: Mapping[str, MetricEntry]
    """Per-state values (e.g. ``vehicleLifeCycleMode``)."""


class VehicleProfile(TypedDict, total=False):
    """Static vehicle-profile block on a garage entry (~34 fields)."""

    activationType: str | None
    """How the vehicle was activated (``'HMI'``, ``'CUSTOMER'`` …)."""
    bodyStyle: str | None
    """Body style (``'SUV'``, ``'TRUCK'`` …); often ``None`` for cars."""
    cabinCargoUnlock: str | None
    """Cabin cargo-unlock capability marker."""
    canopyOnboardingComplete: bool | None
    """Whether the canopy onboarding flow has been completed (truck-only)."""
    digitalKey: str | None
    """Digital-key enrolment state."""
    digitalKeyType: str | None
    """Digital-key technology (``'PAAK'``, ``'NFC'`` …)."""
    displayRecommendedTirePressure: bool
    """Whether the HMI shows the recommended-pressure placard."""
    doubleLocking: bool
    """Whether the vehicle supports double-locking."""
    driverHeatedSeat: str
    """Driver-seat heating capability (``'Heat with Vent'`` …)."""
    engineType: EngineType
    """Powertrain category."""
    externalSecurityCameras: str
    """External-security-camera capability (``'On'`` / ``'Unavailable'`` / …)."""
    frontCargoArea: str
    """Front-cargo configuration (``'None'``, ``'Frunk'`` …)."""
    globalChargeSettings: str
    """Global charge-settings capability marker."""
    heatedSteeringWheel: bool
    """Whether the vehicle has a heated steering wheel."""
    highVoltageBatteryPackType: str
    """HV battery pack identifier (``'None'`` for ICE)."""
    iapIdentifier: str | None
    """In-app-purchase identifier; usually ``None``."""
    isFordPassActivated: str
    """``'On'`` when FordPass services are activated on the vehicle."""
    make: VehicleBrand
    """Vehicle make (``'Ford'`` / ``'Lincoln'``)."""
    model: str
    """Vehicle model (``'Mustang'``, ``'F-150'`` …)."""
    nonRecallCount: int
    """Outstanding non-recall service item count."""
    numberOfLightingZones: int
    """Number of programmable lighting zones."""
    numberOfTires: str
    """Tire count as a word (``'Four'``, ``'Six'``)."""
    paakPairingType: str
    """Phone-as-a-key pairing flow (``'PinCode'`` …)."""
    paintDescription: str
    """Manufacturer paint description."""
    proPowerWattage: str
    """ProPower-OnBoard wattage tier (``'None'``, ``'2.4kW'`` …)."""
    productType: str
    """Internal product-type code."""
    rearCargoArea: str
    """Rear-cargo configuration (``'None'``, ``'Bed'`` …)."""
    rearCargoClosureType: str
    """Rear-cargo closure mechanism (``'None'``, ``'Tailgate'`` …)."""
    recallCount: int
    """Outstanding recall count."""
    sdn: str
    """Service Delivery Network code (``'TMC'``, …)."""
    supportsStatusRefresh: bool
    """Whether on-demand status-refresh commands are supported."""
    transmissionIndicator: str
    """Transmission type code (``'A'``, ``'M'``, ``'E'``)."""
    vehicleImage: str
    """URL of the marketing vehicle image."""
    year: int
    """Model year."""


class VehicleCapabilities(TypedDict, total=False):
    """Per-feature capability map (~41 keys, most string-valued tri-state)."""

    bidirectionalPowerTransferRemoteControl: str
    """V2X power-transfer remote control capability (``'Display'`` / ``'NoDisplay'``)."""
    ccsConnectivity: str
    """Connected-car-services connectivity feature."""
    ccsDrivingCharacteristics: str
    """Connected-car-services driving-characteristics feature."""
    ccsLocation: str
    """Connected-car-services location feature."""
    ccsVehicleData: str
    """Connected-car-services vehicle-data feature."""
    comprehensiveStatus: str
    """Comprehensive-status feature capability."""
    departureTimes: str
    """Departure-times feature (EV/PHEV only)."""
    dieselExhaustFluid: str
    """Diesel-exhaust-fluid monitoring (diesel only)."""
    displayOTAStatusReport: str
    """OTA status-report display capability."""
    displayPreferredChargeTimes: str
    """Preferred-charge-times display (EV/PHEV only)."""
    electricVehicleOnDemandConditioning: str
    """On-demand cabin conditioning (EV/PHEV only)."""
    extendRemoteStart: bool
    """Whether the vehicle supports extending a running remote-start."""
    globalStartStopCharge: str
    """Global start/stop-charge feature (EV/PHEV only)."""
    guardMode: str
    """Guard-mode capability (selected trucks)."""
    offPlugConditioning: str
    """Off-plug conditioning capability (EV/PHEV only)."""
    oilLife: str
    """Oil-life display capability (ICE/PHEV)."""
    onetimeChargeLimit: str
    """One-time-charge-limit feature (EV/PHEV only)."""
    otaRemoteCommands: str
    """OTA remote-command capability."""
    paak: str
    """Phone-as-a-key feature capability."""
    payForCharge: str
    """Pay-for-charge feature capability (EV/PHEV only)."""
    payForChargeUserSubscription: str | None
    """User's active pay-for-charge subscription, or ``None``."""
    plugAndCharge: str
    """Plug-and-charge feature (EV only)."""
    plugAndChargeUserSubscription: str | None
    """User's active plug-and-charge subscription, or ``None``."""
    proPowerOnBoard: str
    """ProPower-OnBoard feature (selected trucks)."""
    remoteClimateControl: str
    """Remote climate-control feature."""
    remoteLock: str
    """Remote-lock command feature."""
    remotePanicAlarm: str
    """Remote panic-alarm command feature."""
    remoteStart: str
    """Remote-start command feature."""
    remoteWindowCapability: str
    """Remote-window command feature."""
    scheduleStart: str
    """Recurring remote-start schedule feature."""
    showEVBatteryLevel: bool
    """Whether to show the EV battery level."""
    stolenVehicleServices: str
    """Stolen-vehicle services feature."""
    stolenVehicleStatus: str
    """Current stolen-vehicle status (``'Normal'`` / ``'Reported'`` / …)."""
    tirePressureMonitoring: str
    """TPMS feature capability."""
    trailerLightCheck: str
    """Trailer-light-check feature (selected trucks)."""
    tripAndChargeLogs: str
    """Trip-and-charge-logs feature (EV/PHEV only)."""
    userAuthFlow: str
    """User-authorisation flow state on the vehicle (``'Authorized'`` / …)."""
    vehicleChargingStatusExtended: str
    """Extended charging-status feature (EV/PHEV only)."""
    vehicleLifeCycleMode: str
    """Reported life-cycle mode (``'NORMAL'``, ``'TRANSPORT'`` …)."""
    vehicleStartInhibit: str
    """Start-inhibit capability."""
    zoneLighting: str
    """Zone-lighting feature (selected trucks)."""


class VehicleUserRoles(TypedDict, total=False):
    """User-role metadata block."""

    role: str | None
    """The signed-in user's role on the vehicle (``'PRIMARY'``, …) or ``None``."""


class GarageVehicle(TypedDict, total=False):
    """One vehicle entry in the user-garage response."""

    vin: str
    """VIN of the vehicle."""
    nickName: str
    """User-supplied display name."""
    licensePlate: str | None
    """User-supplied licence plate; ``None`` when unset."""
    color: str
    """Marketing colour name."""
    preferredDealer: str
    """PA code of the user's preferred dealer."""
    sourceOfPreferredDealer: str
    """How the preferred dealer was set (``'Customer'``, ``'OEM'``, …)."""
    userAuthStatus: UserAuthStatus
    """User's authorisation status on the vehicle (``'Authorized'`` / ``'Pending'`` / …)."""
    profile: VehicleProfile
    """Static vehicle profile (year, model, make, …)."""
    capabilities: VehicleCapabilities
    """Per-feature capability map."""
    userRoles: VehicleUserRoles
    """User-role metadata."""


class ScheduleEntry(TypedDict, total=False):
    """One recurring remote-start schedule entry."""

    startScheduleId: str
    """Server-assigned schedule identifier."""
    name: str
    """User-supplied schedule name."""
    startTime: str
    """Local time-of-day (``'HH:MM'``) when the engine should fire."""
    requestDateTime: str
    """Originally-requested start datetime."""
    timeZone: int
    """Internal time-zone code."""
    status: str
    """``'1'`` for active, ``'0'`` for disabled (strings from upstream)."""
    sun: str
    """``'1'`` if the schedule fires on Sunday."""
    mon: str
    """``'1'`` if the schedule fires on Monday."""
    tue: str
    """``'1'`` if the schedule fires on Tuesday."""
    wed: str
    """``'1'`` if the schedule fires on Wednesday."""
    thu: str
    """``'1'`` if the schedule fires on Thursday."""
    fri: str
    """``'1'`` if the schedule fires on Friday."""
    sat: str
    """``'1'`` if the schedule fires on Saturday."""


class SchedulesEnvelope(TypedDict, total=False):
    """Inner ``startSchedule`` envelope wrapping the schedule list.

    ``$values`` (the actual list) is not a valid Python identifier; consumers
    access it via ``envelope['$values']`` at runtime.
    """

    schemaName: str
    """Newtonsoft.Json schema sentinel."""
    schemaVersion: str
    """Newtonsoft.Json schema-version sentinel."""


class SchedulesResponse(TypedDict, total=False):
    """Top-level shape of the ``getschedules`` SRSM response."""

    startSchedule: SchedulesEnvelope
    """Schedule list, wrapped in a Newtonsoft.Json ``$values`` envelope."""
    status: int
    """HTTP-style status code echoed in the body."""


class AlertPrognostics(TypedDict, total=False):
    """Detail block for prognostics-type alert entries (11 known fields)."""

    dtsMessage: str | None
    """Diagnostic-trouble-symptom message body."""
    estDistanceKM: float | None
    """Estimated distance to service in kilometres."""
    estDistanceMiles: float | None
    """Estimated distance to service in miles."""
    estServiceDate: str | None
    """ISO-8601 estimated service date."""
    featureData: str | None
    """Feature-specific freeform data."""
    featureType: str | None
    """Prognostics feature category (``'SM'`` = scheduled maintenance, ``'OL'`` = oil life, …)."""
    nextIntervalKMs: float | None
    """Next service interval in kilometres."""
    nextIntervalMiles: float | None
    """Next service interval in miles."""
    oilRemaining: float | None
    """Oil-life percentage remaining."""
    shouldShow: bool
    """Whether the HMI should surface this row."""
    tireWithSlowLeak: str | None
    """Wheel identifier (``'FRONT_LEFT'``, …) when a slow-leak alert fired."""


class AlertEntry(TypedDict, total=False):
    """One entry in the active-alerts list.

    Most string-typed fields are nullable; the upstream returns ``null`` rather
    than omitting the key when no value is set.
    """

    alertDescription: str | None
    """Human-readable description; ``None`` when the alert has no description."""
    alertIdentifier: str | None
    """Stable identifier (e.g. ``'E19-374-43'``); ``None`` for some prognostics."""
    alertTraceId: str | None
    """Upstream trace identifier; commonly ``None``."""
    alertType: AlertCategory
    """Category (``'Prognostics'`` / ``'Diagnostics'``)."""
    colorCode: AlertColorCode
    """Display colour code: ``'A'`` (amber), ``'Y'`` (yellow), or ``'R'`` (red)."""
    eventTimeStamp: str
    """Timestamp when the alert was raised."""
    iconName: str
    """Icon asset name."""
    urgency: AlertUrgency
    """``'N'`` (normal), ``'M'`` (medium), or ``'H'`` (high)."""
    wilCode: str
    """Warning-indicator-lamp code (``'None'`` when there is no WIL)."""
    prognostics: AlertPrognostics | None
    """Detail block for prognostics-type alerts; ``None`` for other alert types."""
    vha: Mapping[str, object] | None
    """Detail block for vehicle-health-alert-type alerts; ``None`` otherwise. Shape not yet
    fully catalogued — populate field-by-field once a non-``None`` sample is captured."""
    sortOrder: int | None
    """Display-ordering hint; ``None`` when upstream did not score the row."""


class AlertsResponse(TypedDict, total=False):
    """Top-level shape of the current-alerts response."""

    VIN: str
    """Echoed VIN."""
    alerts: list[AlertEntry]
    """Currently-active alerts."""


class AlertHistoryEntry(TypedDict, total=False):
    """One entry in the alert-history list."""

    alertType: str
    """Category (``'prognostics'``, ``'diagnostics'``)."""
    eventTime: str
    """Local-time timestamp when the alert was raised."""
    messageBody: str
    """Full message text."""
    messageSubject: str
    """Short subject line."""
    messageTypeId: int
    """Upstream message-type identifier."""


class AlertHistoryResponse(TypedDict, total=False):
    """Top-level shape of the alert-history response."""

    error: object
    """``None`` on success; otherwise the upstream error envelope."""
    messages: list[AlertHistoryEntry]
    """Historical alert entries."""


class MessageEntry(TypedDict, total=False):
    """One entry in the message-centre inbox."""

    id: str
    """Server-assigned message identifier (string form)."""
    messageId: str
    """Numeric message identifier (string form). Required for delete / mark-read."""
    messageType: str
    """Upstream message-type name (``'EXTERNALNOTIFICATIONREQUEST'``, …)."""
    messageTypeId: int
    """Upstream numeric message-type identifier."""
    messageSubject: str
    """Subject line."""
    messageBody: str
    """Body text."""
    contentType: str
    """``'Html'`` or ``'Text'``."""
    createdDate: str
    """Local-time timestamp the message was created."""
    isRead: bool
    """Whether the message has been read."""
    highlighted: bool
    """Whether the HMI should highlight the message."""
    priority: int
    """Upstream priority hint (1 = highest)."""
    relevantVin: str
    """VIN the message relates to, if any."""
    templateID: str | None
    """Upstream template identifier; commonly ``None``."""
    metadata: str
    """Per-template metadata as a JSON-encoded string."""


class MessagesResultEnvelope(TypedDict, total=False):
    """Inner ``result`` envelope of the message-centre response."""

    lastFetchedTime: str
    """ISO-8601 timestamp when the server last refreshed the inbox."""
    messages: list[MessageEntry]
    """The inbox entries."""


class MessagesResponse(TypedDict, total=False):
    """Top-level shape of the message-centre inbox response."""

    result: MessagesResultEnvelope
    """Wrapper containing ``lastFetchedTime`` and ``messages``."""


class ProfileNames(TypedDict, total=False):
    """First / middle / last name block on a profile response."""

    firstName: str | None
    """User's first name."""
    middleName: str | None
    """User's middle name."""
    lastName: str | None
    """User's last name."""


class ProfileNamesExtension(TypedDict, total=False):
    """One entry in the ``namesExtensions`` list (title, suffix, secondLastName)."""

    fieldName: str
    """Name of the auxiliary field (``'title'``, ``'suffix'``, …)."""
    value: str | None
    """Value of the field, or ``None`` when unset."""


class ProfileAddress(TypedDict, total=False):
    """Postal-address block on a profile response."""

    addressLine1: str | None
    """First address line."""
    addressLine2: str | None
    """Second address line."""
    addressLine3: str | None
    """Third address line."""
    addressLine4: str | None
    """Fourth address line."""
    neighbourhood: str | None
    """Neighbourhood."""
    district: str | None
    """District / state district."""
    city: str | None
    """City."""
    state: str | None
    """State / province / region."""
    postalCode: str | None
    """Postal / ZIP code."""


class ProfilePhoneNumbers(TypedDict, total=False):
    """Phone-numbers block on a profile response."""

    phoneNumber: str | None
    """Primary phone number."""
    alternatePhoneNumber: str | None
    """Alternate phone number."""
    mobilePhoneNumber: str | None
    """Mobile phone number."""


class ProfileEmails(TypedDict, total=False):
    """Email-addresses block on a profile response."""

    email: str | None
    """Primary email address."""


class ProfileCountry(TypedDict, total=False):
    """Country block on a profile response."""

    countryCode: str
    """ISO-3166 alpha-3 country code (e.g. ``'USA'``)."""


class ProfileLanguages(TypedDict, total=False):
    """Languages block on a profile response."""

    preferredLanguage: str
    """BCP-47 locale tag (e.g. ``'en-US'``)."""


class ProfileUnitsOfMeasure(TypedDict, total=False):
    """Units-of-measure block on a profile response."""

    distance: str | None
    """Preferred distance unit (``'MI'`` / ``'KM'``)."""
    pressure: str | None
    """Preferred pressure unit (``'PSI'`` / ``'KPA'`` / ``'BAR'``)."""
    speed: str | None
    """Preferred speed unit (``'MPH'`` / ``'KPH'``)."""
    temperature: str | None
    """Preferred temperature unit (``'F'`` / ``'C'``); often ``None``."""


class ProfileResponse(TypedDict, total=False):
    """Top-level shape of the user-profile lookup response.

    Field presence follows the ``profileGroups`` query parameter; every section
    may be absent.
    """

    userGuid: str
    """Globally-unique user identifier."""
    names: ProfileNames
    """First / middle / last name."""
    namesExtensions: list[ProfileNamesExtension]
    """Auxiliary name fields (title, suffix, …)."""
    address: ProfileAddress
    """Postal address."""
    phoneNumbers: ProfilePhoneNumbers
    """Phone numbers."""
    emails: ProfileEmails
    """Email addresses."""
    country: ProfileCountry
    """Country code."""
    languages: ProfileLanguages
    """Preferred language."""
    unitsOfMeasure: ProfileUnitsOfMeasure
    """User's preferred units (distance, pressure, speed, temperature)."""


class IDNameEntry(TypedDict):
    """An ``{id, name}`` pair used by several catalogue endpoints."""

    id: str
    """Upstream identifier."""
    name: str
    """Display label."""


class IDNameListResponse(TypedDict, total=False):
    """Envelope around an ID/name list (roadside symptoms / location types)."""

    symptoms: list[IDNameEntry]
    """Populated by the roadside-symptoms endpoint."""
    locationTypes: list[IDNameEntry]
    """Populated by the roadside-location-types endpoint."""


class RoadsideActiveResponse(TypedDict, total=False):
    """Top-level shape of the active-roadside-event response."""

    eventId: str
    """Identifier of the active roadside event, if any."""


class DriverEntry(TypedDict, total=False):
    """One entry in the authorised + pending drivers list."""

    GUID: str
    """User's GUID."""
    displayName: str
    """Display name."""
    inviteId: str | None
    """Pending-invite id; ``None`` when the driver is already authorised."""
    userAuthStatus: str
    """``'Authorized'`` / ``'Pending'``."""


class DriversListResponse(TypedDict, total=False):
    """Top-level shape of the drivers-list response."""

    authAndPendingUsers: list[DriverEntry]
    """Combined authorised + pending list."""
    code: object
    """Upstream status code (``None`` on success)."""
    message: object
    """Upstream message (``None`` on success)."""
    status: dict[str, object]
    """Status envelope."""


class DriversCountResponse(TypedDict, total=False):
    """Top-level shape of the authorised-user count response."""

    count: int
    """Number of currently authorised secondary drivers."""


class DealerResponse(TypedDict, total=False):
    """Top-level shape of the dealer-by-PA-code response."""

    request_time: str
    """ISO-8601 timestamp the upstream service stamped the response with."""
    status: dict[str, object]
    """Upstream status envelope."""


class ServicePlannerResponse(TypedDict, total=False):
    """Top-level shape of the service-planner upcoming / history response."""

    response: dict[str, object]
    """Per-service detail block."""


class ReleaseNotesResponse(TypedDict, total=False):
    """Top-level shape of the OTA release-notes response."""

    response: str
    """Release-notes text."""


class AckResponse(TypedDict, total=False):
    """Generic acknowledgement envelope from a TMC command POST."""

    commandId: str
    """Server-assigned command identifier."""
    status: str
    """Initial command status (``'QUEUED'``, ``'PENDING'``, …)."""


class InviteResponse(TypedDict, total=False):
    """Response envelope for the secondary-driver invite endpoint."""

    errorCode: str | None
    """Upstream error code; ``None`` (or absent) on success."""
    errorMessage: str | None
    """Upstream error message; ``None`` (or absent) on success."""
    inviteId: str
    """Server-assigned invite identifier (present on success)."""
