"""Vehicle profile, capability map, and garage-entry shapes."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from fordpass.typing.common import EngineType, UserAuthStatus, VehicleBrand

__all__ = ('GarageVehicle', 'VehicleCapabilities', 'VehicleProfile', 'VehicleUserRoles')


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

    capabilities: VehicleCapabilities
    """Per-feature capability map."""
    color: str
    """Marketing colour name."""
    licensePlate: str | None
    """User-supplied licence plate; ``None`` when unset."""
    nickName: str
    """User-supplied display name."""
    preferredDealer: str
    """PA code of the user's preferred dealer."""
    profile: VehicleProfile
    """Static vehicle profile (year, model, make, …)."""
    sourceOfPreferredDealer: str
    """How the preferred dealer was set (``'Customer'``, ``'OEM'``, …)."""
    userAuthStatus: UserAuthStatus
    """User's authorisation status on the vehicle (``'Authorized'`` / ``'Pending'`` / …)."""
    userRoles: VehicleUserRoles
    """User-role metadata."""
    vin: str
    """VIN of the vehicle."""
