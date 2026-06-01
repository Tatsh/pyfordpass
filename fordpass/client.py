"""
FordPass async client.

Wraps :class:`fordpass.sansio.FordPassClient` and dispatches each
:class:`fordpass.sansio.RequestDict` through one of two transports:

- :class:`curl_cffi.requests.AsyncSession` (Chrome-impersonated TLS/HTTP-2
  fingerprint) for the OAuth/token endpoints. These hosts sit behind a fingerprinting CDN that
  RST_STREAMs non-browser HTTP/2 clients (the symptom: ``Stream 1 was reset by remote peer. Reason:
  0x2.``).
- :class:`niquests.AsyncSession` for everything else - data-plane endpoints
  that authenticate via Bearer/CAT and don't fingerprint.

Usage::

    async with AsyncFordPassClient(cat=..., tmc=...) as client:
        pct, _ = await client.get_fuel_level('VIN1234')
        await client.remote_start('VIN1234')
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast
import asyncio
import contextlib
import json as _json
import uuid

from curl_cffi.requests import AsyncSession as CurlAsyncSession
from typing_extensions import Self
import niquests

from .api_config import load_api_config
from .config import DEFAULT_IMPERSONATE, load_config
from .sansio import FordPassClient
from .typing.lighting import ZONE_LIGHT_OFF
from .utils import (
    extract_fuel,
    extract_odometer,
    extract_oil_life,
    extract_position,
    find_next_departure,
    find_preferred_dealer_code,
    is_washer_fluid_low,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from typing_extensions import Unpack

    from .sansio import RequestDict
    from .typing.alerts import AlertHistoryResponse, AlertsResponse
    from .typing.api_config import APIConfig
    from .typing.auth import B2CTokenResponse, CATTokenResponse, TMCTokenResponse
    from .typing.commands import AckResponse
    from .typing.common import DistanceUnit, GPSPosition
    from .typing.dealer import DealerResponse
    from .typing.drivers import DriversCountResponse, DriversListResponse, InviteResponse
    from .typing.electrification import (
        EnergyTransferLogsResponse,
        EnergyTransferStatusResponse,
        PreferredChargeTimesResponse,
    )
    from .typing.guard import GuardModeResponse
    from .typing.lighting import ZoneLightZone
    from .typing.messages import MessagesResponse
    from .typing.profile import ProfileResponse, SaveProfileFields
    from .typing.release import ReleaseNotesResponse
    from .typing.roadside import IDNameListResponse, RoadsideActiveResponse
    from .typing.schedule import ScheduleEntry, SchedulesResponse
    from .typing.service import (
        CompletedServiceActionDetail,
        ServiceActionDetail,
        ServicePlannerResponse,
    )
    from .typing.telemetry import DepartureSchedule, TelemetryResponse, TirePressureEntry
    from .typing.vehicle import GarageVehicle

_ZONE_LIGHT_ON_SETTLE_S = 5
"""
Seconds to wait after turning the zone lighting on before selecting a zone.

Mirrors ha-fordpass: when the lights start from off, the activation must settle before a
mode change is accepted.

:meta hide-value:
"""


class AsyncFordPassClient:  # noqa: PLR0904
    """Async FordPass client (niquests for data, curl-cffi for auth)."""
    def __init__(self,
                 *,
                 api_config: APIConfig | None = None,
                 cat: str | None = None,
                 cat_refresh: str | None = None,
                 tmc: str | None = None,
                 country: str = 'USA',
                 locale: str = 'en-US',
                 brand: str = 'ford',
                 session: niquests.AsyncSession | None = None,
                 auth_session: CurlAsyncSession[Any] | None = None) -> None:
        """
        Build the async client, optionally re-using callers' HTTP sessions.

        Parameters
        ----------
        api_config : APIConfig | None
            API constants bundle (hosts, B2C identifiers, user-agent, …). When ``None`` (the
            default), the bundle is loaded via :py:func:`fordpass.api_config.load_api_config` -
            this is the only place in the package that performs that I/O.
        cat : str | None
            Ford CAT access token forwarded to the underlying
            :py:class:`fordpass.sansio.FordPassClient`.
        cat_refresh : str | None
            Ford CAT refresh token forwarded to the underlying core client.
        tmc : str | None
            TMC bearer forwarded to the underlying core client.
        country : str
            ISO-3166 alpha-3 country code.
        locale : str
            BCP-47 locale tag.
        brand : str
            Sub-brand identifier (``ford``, ``lincoln``).
        session : niquests.AsyncSession | None
            Pre-existing niquests session for data-plane traffic. If ``None`` (the default), a
            new session is created and closed in :py:meth:`aclose`.
        auth_session : curl_cffi.requests.AsyncSession | None
            Pre-existing curl-cffi session for auth-plane traffic. If ``None`` (the default), a
            new Chrome-impersonating session is created and closed in :py:meth:`aclose`.
        """
        self.core = FordPassClient(
            api_config=api_config if api_config is not None else load_api_config(),
            cat=cat,
            cat_refresh=cat_refresh,
            tmc=tmc,
            country=country,
            locale=locale,
            brand=brand)
        self.session = session or niquests.AsyncSession()
        # Versioned chrome profile (``chromeNNN``) pins a specific Chrome release's
        # JA3/JA4 + HTTP-2 SETTINGS fingerprint - the unversioned ``chrome`` alias
        # drifts between curl-cffi releases.
        impersonate = (load_config().get('http') or {}).get('impersonate') or DEFAULT_IMPERSONATE
        self.auth_session = auth_session or CurlAsyncSession(impersonate=cast('Any', impersonate))
        self._owns_session = session is None
        self._owns_auth_session = auth_session is None

    @property
    def cat(self) -> str | None:
        """CAT access token (sent as ``auth-token`` on ``*.ford.com`` calls)."""
        return self.core.cat

    @cat.setter
    def cat(self, value: str | None) -> None:
        """Forward the new CAT access token to the underlying core client."""
        self.core.cat = value

    @property
    def cat_refresh(self) -> str | None:
        """CAT refresh token (used as the ``subject_token`` for the TMC exchange)."""
        return self.core.cat_refresh

    @cat_refresh.setter
    def cat_refresh(self, value: str | None) -> None:
        """Forward the new CAT refresh token to the underlying core client."""
        self.core.cat_refresh = value

    @property
    def tmc(self) -> str | None:
        """
        Return the TMC bearer.

        Returns
        -------
        str | None
            The token used as the ``Authorization: Bearer`` header on TMC-plane calls.
        """
        return self.core.tmc

    @tmc.setter
    def tmc(self, value: str | None) -> None:
        """Forward the new TMC bearer to the underlying core client."""
        self.core.tmc = value

    @property
    def locale(self) -> str:
        """BCP-47 locale tag the client was configured with (e.g. ``'en-US'``)."""
        return self.core.locale

    @property
    def country(self) -> str:
        """ISO 3166-1 alpha-2 country code (e.g. ``'USA'`` / ``'GBR'``)."""
        return self.core.country

    async def _send(self, req: RequestDict) -> niquests.Response:
        """
        Send a sans-I/O request descriptor via niquests and raise on 4xx/5xx.

        Fires the request, and on a single HTTP 401 hands off to
        :py:meth:`_refresh_credentials_for` to rotate whichever credential the original request was
        carrying - then replays the request once. Any further failure propagates.

        Parameters
        ----------
        req : RequestDict
            The descriptor produced by the sans-I/O core.

        Returns
        -------
        niquests.Response
            The niquests response after a successful ``raise_for_status`` check.
        """
        r = await self.session.request(**req)
        if r.status_code == HTTPStatus.UNAUTHORIZED and await self._refresh_credentials_for(req):
            r = await self.session.request(**req)
        r.raise_for_status()
        return r

    async def _refresh_credentials_for(self, req: RequestDict) -> bool:
        """
        Refresh whichever credential ``req`` was carrying and rewrite its header.

        * ``authorization: Bearer …`` (TMC plane) → :py:meth:`exchange_cat_for_tmc`.
        * ``auth-token: <CAT>`` (Ford plane) → :py:meth:`refresh_cat`; the dependent TMC bearer is
          also rotated as best-effort so a subsequent TMC-plane call in the same command reuses a
          matching pair.

        Parameters
        ----------
        req : RequestDict
            The descriptor whose ``headers`` are mutated in place.

        Returns
        -------
        bool
            ``True`` when a refresh ran and the request is ready to retry; ``False`` when no
            refresh path applies (so the original 401 should propagate).
        """
        if self.cat_refresh is None:
            return False
        headers = req['headers']
        if headers.get('authorization', '').startswith('Bearer '):
            await self.exchange_cat_for_tmc()
            headers['authorization'] = f'Bearer {self.tmc}'
            return True
        cat_header = next((k for k in ('auth-token', 'Auth-Token') if k in headers), None)
        if cat_header is None:  # pragma: no cover
            return False
        await self.refresh_cat()
        headers[cat_header] = self.cat or ''
        with contextlib.suppress(niquests.HTTPError, RuntimeError):
            await self.exchange_cat_for_tmc()
        return True

    async def _send_json(self, req: RequestDict) -> Any:
        """
        Send via niquests and decode the response body as JSON.

        Parameters
        ----------
        req : RequestDict
            The descriptor produced by the sans-I/O core.

        Returns
        -------
        Any
            The parsed JSON body.
        """
        r = await self._send(req)
        if r.status_code == HTTPStatus.NO_CONTENT or not r.content:
            return None
        return r.json()

    async def _send_auth_json(self, req: RequestDict) -> Any:
        """
        Send via the curl-cffi (Chrome-impersonating) session and parse JSON.

        Used for OAuth/token endpoints that fingerprint non-browser HTTP/2 clients. curl-cffi's
        signature differs from niquests', so the ``RequestDict`` keys are unpacked individually.

        Parameters
        ----------
        req : RequestDict
            The descriptor produced by the sans-I/O core.

        Returns
        -------
        Any
            The parsed JSON body.

        Raises
        ------
        RuntimeError
            If the response status is 400 or higher.
        """
        method = req['method']
        url = req['url']
        headers = req['headers']
        data = req['data']
        r = await self.auth_session.request(method=cast('Any', method),
                                            url=url,
                                            headers=headers,
                                            data=data)
        if r.status_code >= HTTPStatus.BAD_REQUEST:
            msg = f'auth request failed: {method} {url} -> HTTP {r.status_code}: {r.text[:300]}'
            raise RuntimeError(msg)
        body = r.content.decode('utf-8') if isinstance(r.content, (bytes, bytearray)) else r.text
        return _json.loads(body)

    def b2c_authorize_url(self, **kwargs: Any) -> str:
        """
        Build the B2C ``/authorize`` URL synchronously (no I/O - just URL building).

        Parameters
        ----------
        **kwargs : Any
            Forwarded verbatim to :py:meth:`fordpass.sansio.FordPassClient.b2c_authorize_url`.

        Returns
        -------
        str
            The fully-formed authorisation URL.
        """
        return self.core.b2c_authorize_url(**kwargs)

    async def exchange_b2c_code(self,
                                *,
                                code: str,
                                code_verifier: str,
                                policy: str | None = None) -> B2CTokenResponse:
        """
        Exchange a B2C authorisation code for an access token.

        Parameters
        ----------
        code : str
            The ``code`` query-string value captured from the ``fordapp://userauthorized``
            redirect.
        code_verifier : str
            The PKCE code verifier paired with the original ``code_challenge``.
        policy : str | None
            B2C user-flow / custom-policy name; defaults to ``B2C_1A_SignInSignUp_<locale>``.

        Returns
        -------
        B2CTokenResponse
            The parsed token-endpoint response.
        """
        return cast(
            'B2CTokenResponse', await self._send_auth_json(
                self.core.exchange_b2c_code(code=code, code_verifier=code_verifier, policy=policy)))

    async def mint_cat_from_b2c(self, *, b2c_access_token: str) -> CATTokenResponse:
        """
        Mint a Ford CAT from a B2C access token and stash the resulting tokens.

        Updates :attr:`cat` and :attr:`cat_refresh` in place when the response carries them.

        Parameters
        ----------
        b2c_access_token : str
            The ``access_token`` returned by :py:meth:`exchange_b2c_code`.

        Returns
        -------
        CATTokenResponse
            The parsed CAT-mint response.
        """
        data = cast(
            'CATTokenResponse', await self._send_auth_json(
                self.core.mint_cat_from_b2c(b2c_access_token=b2c_access_token)))
        access = data.get('access_token')
        if isinstance(access, str):
            self.cat = access
        refresh = data.get('refresh_token')
        if isinstance(refresh, str):
            self.cat_refresh = refresh
        return data

    async def refresh_cat(self) -> CATTokenResponse:
        """
        Swap the stored CAT refresh token for a fresh CAT pair.

        Updates :attr:`cat` (and :attr:`cat_refresh` when the response rotates it) in place.

        Returns
        -------
        CATTokenResponse
            The parsed ``cat-with-refresh-token`` response.
        """
        data = cast('CATTokenResponse', await self._send_auth_json(self.core.refresh_cat()))
        access = data.get('access_token')
        if isinstance(access, str):
            self.cat = access
        refresh = data.get('refresh_token')
        if isinstance(refresh, str):
            self.cat_refresh = refresh
        return data

    async def exchange_cat_for_tmc(self) -> TMCTokenResponse:
        """
        Exchange the CAT refresh token for a TMC bearer and stash it.

        Updates :attr:`tmc` in place when the response carries ``access_token``.

        Returns
        -------
        TMCTokenResponse
            The parsed token-exchange response.
        """
        data = cast('TMCTokenResponse', await
                    self._send_auth_json(self.core.exchange_cat_for_tmc()))
        token = data.get('access_token')
        if isinstance(token, str):
            self.tmc = token
        return data

    async def remote_start(self, vin: str) -> niquests.Response:
        """
        Send the remote-start command for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.remote_start(vin))

    async def cancel_remote_start(self, vin: str) -> niquests.Response:
        """
        Cancel an active remote-start session for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.cancel_remote_start(vin))

    async def extend_remote_start(self, vin: str) -> niquests.Response:
        """
        Extend an active remote-start session for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.extend_remote_start(vin))

    async def lock(self, vin: str) -> niquests.Response:
        """
        Lock the doors of ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.lock(vin))

    async def unlock(self, vin: str) -> niquests.Response:
        """
        Unlock the doors of ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.unlock(vin))

    async def status_refresh(self, vin: str) -> niquests.Response:
        """
        Force the TCU of ``vin`` to push fresh state to the server.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.status_refresh(vin))

    async def panic_alarm(self, vin: str, duration_s: int = 3) -> niquests.Response:
        """
        Sound the horn and flash the lights of ``vin`` for ``duration_s`` seconds.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        duration_s : int
            How long, in seconds, to keep the panic cue active.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.panic_alarm(vin, duration_s))

    async def get_asu_settings(self, vin: str) -> niquests.Response:
        """
        Read current Automatic Software Update settings for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.get_asu_settings(vin))

    async def set_asu_enabled(self, vin: str, *, enabled: bool) -> niquests.Response:
        """
        Toggle automatic software updates for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        enabled : bool
            ``True`` to enable updates, ``False`` to disable them.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.set_asu_enabled(vin, enabled=enabled))

    async def set_asu_schedule(self, vin: str, *, day_schedules: Sequence[Mapping[str, object]],
                               activation_setting: str) -> niquests.Response:
        """
        Set the day-of-week / time window for automatic updates for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        day_schedules : list[Any]
            Per-day schedule blocks for the ``OTAActivationDaySchedule`` field.
        activation_setting : str
            Wire value for ``activationScheduleSetting``.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(
            self.core.set_asu_schedule(vin,
                                       day_schedules=day_schedules,
                                       activation_setting=activation_setting))

    async def start_global_charge(self, vin: str) -> niquests.Response:
        """
        Start an EV charge session for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.start_global_charge(vin))

    async def cancel_global_charge(self, vin: str) -> niquests.Response:
        """
        Cancel an active EV charge session for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.cancel_global_charge(vin))

    async def pause_global_charge(self, vin: str) -> niquests.Response:
        """
        Pause an active EV charge session for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.pause_global_charge(vin))

    async def update_charge_settings(self, vin: str, *,
                                     settings: Mapping[str, object]) -> niquests.Response:
        """
        Update EV charge settings for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        settings : Mapping[str, object]
            The ``chargeSettings`` payload; see
            :py:class:`fordpass.typing.electrification.ChargeSettings` for recognised keys.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.update_charge_settings(vin, settings=settings))

    async def get_preferred_charge_times(self, vin: str) -> PreferredChargeTimesResponse:
        """
        Fetch the preferred-charge-times profile for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        PreferredChargeTimesResponse
            The parsed preferred-charge-times response.
        """
        return cast('PreferredChargeTimesResponse', await self._send_json(
            self.core.get_preferred_charge_times(vin)))

    async def set_preferred_charge_times(
            self, vin: str, *, location_id: str,
            body: Mapping[str, object]) -> PreferredChargeTimesResponse | None:
        """
        Write a preferred-charge-times profile for one location of ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        location_id : str
            Identifier of the charge location.
        body : Mapping[str, object]
            The preferred-charge-times request payload, forwarded verbatim.

        Returns
        -------
        PreferredChargeTimesResponse | None
            The parsed server response, or ``None`` if the call returns 204.
        """
        return cast(
            'PreferredChargeTimesResponse | None', await self._send_json(
                self.core.set_preferred_charge_times(vin, location_id=location_id, body=body)))

    async def get_energy_transfer_status(self, vin: str) -> EnergyTransferStatusResponse | None:
        """
        Fetch the live energy-transfer status for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        EnergyTransferStatusResponse | None
            The parsed status response, or ``None`` when the vehicle is not at a charge location.
        """
        return cast('EnergyTransferStatusResponse | None', await self._send_json(
            self.core.get_energy_transfer_status(vin)))

    async def get_energy_transfer_logs(self,
                                       vin: str,
                                       *,
                                       max_records: int = 20) -> EnergyTransferLogsResponse:
        """
        Fetch recent energy-transfer logs for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        max_records : int
            Maximum number of log records to request.

        Returns
        -------
        EnergyTransferLogsResponse
            The parsed logs response.
        """
        return cast(
            'EnergyTransferLogsResponse', await self._send_json(
                self.core.get_energy_transfer_logs(vin, max_records=max_records)))

    async def query_telemetry(self,
                              vin: str,
                              metrics: Iterable[str] | None = None) -> TelemetryResponse:
        """
        Run a one-shot telemetry query for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        metrics : Iterable[str] | None
            Optional iterable of metric keys; ``None`` or empty returns all 58 fields.

        Returns
        -------
        TelemetryResponse
            The parsed telemetry response.
        """
        return cast('TelemetryResponse', await self._send_json(
            self.core.query_telemetry(vin, metrics)))

    async def get_fuel_level(self, vin: str) -> tuple[float | None, float | None]:
        """
        Fetch the fuel level and range for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        tuple[float | None, float | None]
            The ``(fuel_percent, fuel_range)`` pair; either may be ``None`` if absent.
        """
        data = await self._send_json(self.core.get_fuel_level(vin))
        return extract_fuel(data.get('metrics') or {})

    async def get_odometer(self, vin: str) -> float | None:
        """
        Fetch the odometer reading for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        float | None
            The odometer value, or ``None`` if absent.
        """
        data = await self._send_json(self.core.get_odometer(vin))
        return extract_odometer(data.get('metrics') or {})

    async def get_position(self, vin: str) -> GPSPosition | None:
        """
        Fetch the current GPS position for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        GPSPosition | None
            A dict with ``lat``, ``lon`` (always present), plus optional ``alt``, ``heading``,
            ``compass``, and ``update_time`` fields; ``None`` when no position is reported.
        """
        data = await self._send_json(self.core.get_position(vin))
        return extract_position(data.get('metrics') or {})

    async def get_oil_life(self, vin: str) -> float | None:
        """
        Fetch the remaining oil-life percentage for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        float | None
            The oil-life value, or ``None`` if absent.
        """
        data = await self._send_json(self.core.get_oil_life(vin))
        return extract_oil_life(data.get('metrics') or {})

    async def get_tire_pressure(self, vin: str) -> list[TirePressureEntry]:
        """
        Fetch the per-tyre pressure readings for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        list[TirePressureEntry]
            The list of tyre-pressure entries, or an empty list if absent.
        """
        data = await self._send_json(self.core.get_tire_pressure(vin))
        return (data.get('metrics') or {}).get('tirePressure') or []

    async def get_next_departure(self, vin: str) -> DepartureSchedule | None:
        """
        Fetch the next-up departure schedule for ``vin`` (EV/PHEV only).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        DepartureSchedule | None
            The matching schedule, or ``None`` if no schedule was identified.
        """
        data = await self._send_json(self.core.get_next_departure(vin))
        return find_next_departure(data.get('metrics') or {})

    async def list_remote_start_schedules(self, vin: str) -> SchedulesResponse:
        """
        Fetch the recurring remote-start schedules currently set for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        SchedulesResponse
            The parsed ``getschedules`` response (typically ``{"schedules": [...]}``).
        """
        return cast('SchedulesResponse', await self._send_json(
            self.core.list_remote_start_schedules(vin)))

    async def add_remote_start_schedule(self,
                                        vin: str,
                                        *,
                                        start_time: str,
                                        request_start_date: str,
                                        time_zone: int,
                                        days: Mapping[str, int],
                                        status: int = 1) -> ScheduleEntry:
        """
        Create a new recurring remote-start schedule for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        start_time : str
            Local time-of-day (for example ``'07:30'``) when the engine should fire.
        request_start_date : str
            ISO-8601 date when the schedule becomes active.
        time_zone : int
            UTC offset in minutes for the vehicle's local time.
        days : Mapping[str, int]
            Mapping such as ``{'mon': 1, ...}``; keys for all seven days are required.
        status : int
            ``1`` for active, ``0`` for disabled.

        Returns
        -------
        ScheduleEntry
            The parsed server response (the persisted schedule entry).
        """
        return cast(
            'ScheduleEntry', await self._send_json(
                self.core.add_remote_start_schedule(vin,
                                                    start_time=start_time,
                                                    request_start_date=request_start_date,
                                                    time_zone=time_zone,
                                                    days=days,
                                                    status=status)))

    async def toggle_remote_start_schedule(
            self, schedule_id: int, *, schedule_body: Mapping[str,
                                                              str | int | None]) -> ScheduleEntry:
        """
        PUT an updated remote-start schedule (typically to flip ``status``).

        Parameters
        ----------
        schedule_id : int
            Server-assigned identifier of the schedule entry.
        schedule_body : Mapping[str, Any]
            Full body as returned by the read-side ``getschedules`` call, with ``status`` toggled.

        Returns
        -------
        ScheduleEntry
            The parsed server response.
        """
        return cast(
            'ScheduleEntry', await self._send_json(
                self.core.toggle_remote_start_schedule(schedule_id, schedule_body=schedule_body)))

    async def delete_remote_start_schedule(self, schedule_id: int, *, vin: str) -> AckResponse:
        """
        Delete a remote-start schedule entry.

        Parameters
        ----------
        schedule_id : int
            Server-assigned identifier of the schedule entry.
        vin : str
            The VIN that owns the schedule.

        Returns
        -------
        AckResponse
            The parsed server response.
        """
        return cast(
            'AckResponse', await self._send_json(
                self.core.delete_remote_start_schedule(schedule_id, vin=vin)))

    async def list_garage(self) -> list[GarageVehicle]:
        """
        List all vehicles in the signed-in user's garage.

        Returns
        -------
        list[GarageVehicle]
            The parsed garage response (vehicle list with nickname, plate, capabilities, etc.).
        """
        return cast('list[GarageVehicle]', await self._send_json(self.core.list_garage()))

    async def update_vehicle_details(self,
                                     vin: str,
                                     *,
                                     nick_name: str | None = None,
                                     license_plate: str | None = None,
                                     mileage: int | None = None,
                                     preferred_dealer: str | None = None) -> AckResponse:
        """
        Update one or more of nickname / plate / mileage / preferred dealer for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        nick_name : str | None
            New nickname, or ``None`` to leave unchanged.
        license_plate : str | None
            New licence-plate string, or ``None`` to leave unchanged.
        mileage : int | None
            New manual odometer reading in the user's display unit, or ``None`` to leave unchanged.
        preferred_dealer : str | None
            New dealer PA code, or ``None`` to leave unchanged.

        Returns
        -------
        AckResponse
            The parsed server response.
        """
        return cast(
            'AckResponse', await self._send_json(
                self.core.update_vehicle_details(vin,
                                                 nick_name=nick_name,
                                                 license_plate=license_plate,
                                                 mileage=mileage,
                                                 preferred_dealer=preferred_dealer)))

    async def get_profile(self, *, profile_groups: str | None = None) -> ProfileResponse:
        """
        Fetch the signed-in user's account profile.

        Parameters
        ----------
        profile_groups : str | None
            Comma-separated subset of profile sections to include, or ``None`` for all.

        Returns
        -------
        ProfileResponse
            The parsed profile response.
        """
        return cast('ProfileResponse', await self._send_json(
            self.core.get_profile(profile_groups=profile_groups)))

    async def save_profile(self, **fields: Unpack[SaveProfileFields]) -> niquests.Response:
        """
        PATCH the signed-in user's account profile.

        Parameters
        ----------
        **fields : Unpack[SaveProfileFields]
            Profile section objects keyed by section name (``names``, ``address``, etc.).

        Returns
        -------
        niquests.Response
            The raw HTTP response from the profile-management endpoint.
        """
        return await self._send(self.core.save_profile(**fields))

    async def get_messages(self) -> MessagesResponse:
        """
        Fetch the signed-in user's message-centre inbox.

        Returns
        -------
        MessagesResponse
            The parsed messages response.
        """
        return cast('MessagesResponse', await self._send_json(self.core.get_messages()))

    async def delete_messages(self, message_ids: Iterable[int]) -> AckResponse | None:
        """
        Bulk-delete inbox messages by ID.

        Parameters
        ----------
        message_ids : Iterable[int]
            Numeric IDs from the inbox ``messageId`` field.

        Returns
        -------
        AckResponse | None
            The parsed server response, or ``None`` if the call returns 204.
        """
        return cast('AckResponse | None', await self._send_json(
            self.core.delete_messages(message_ids)))

    async def mark_messages_read(self, message_ids: Iterable[int]) -> AckResponse | None:
        """
        Bulk-mark inbox messages as read by ID.

        Parameters
        ----------
        message_ids : Iterable[int]
            Numeric IDs from the inbox ``messageId`` field.

        Returns
        -------
        AckResponse | None
            The parsed server response, or ``None`` if the call returns 204.
        """
        return cast('AckResponse | None', await self._send_json(
            self.core.mark_messages_read(message_ids)))

    async def get_alerts(self, vin: str, *, trace_id: str | None = None) -> AlertsResponse:
        """
        Fetch the active alerts for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        trace_id : str | None
            Optional value for the ``trace-id`` header; a fresh UUID is generated if omitted.

        Returns
        -------
        AlertsResponse
            The parsed alerts response.
        """
        return cast(
            'AlertsResponse', await self._send_json(
                self.core.get_alerts(vin, trace_id=trace_id or str(uuid.uuid4()))))

    async def is_washer_fluid_low(self, vin: str) -> bool:
        """
        Test whether the washer-fluid-low alert (``E19-374-43``) is active for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        bool
            ``True`` if the alert is present; ``False`` otherwise.
        """
        alerts = await self.get_alerts(vin)
        return is_washer_fluid_low(alerts)

    async def get_alert_history(self,
                                vin: str,
                                *,
                                brand: str | None = None) -> AlertHistoryResponse:
        """
        Fetch the fully hydrated alert history for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        brand : str | None
            Brand override (defaults to the core client's brand).

        Returns
        -------
        AlertHistoryResponse
            The parsed alert-history response.
        """
        return cast('AlertHistoryResponse', await self._send_json(
            self.core.get_alert_history(vin, brand=brand)))

    async def get_service_planner_upcoming(self,
                                           vin: str,
                                           *,
                                           odometer: int | None = None,
                                           uom: DistanceUnit = 'mi') -> ServicePlannerResponse:
        """
        Fetch the upcoming-services planner summary for ``vin``.

        Parameters
        ----------
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``; ``None`` omits the query parameter.
        uom : DistanceUnit
            Unit of measure for ``odometer`` (``'mi'`` or ``'km'``).

        Returns
        -------
        ServicePlannerResponse
            The parsed planner-summary response.
        """
        return cast(
            'ServicePlannerResponse', await self._send_json(
                self.core.get_service_planner_upcoming(vin=vin, odometer=odometer, uom=uom)))

    async def get_service_planner_history(self,
                                          vin: str,
                                          *,
                                          odometer: int | None = None,
                                          uom: DistanceUnit = 'mi') -> ServicePlannerResponse:
        """
        Fetch the completed-services planner summary for ``vin``.

        Parameters
        ----------
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``; ``None`` omits the query parameter.
        uom : DistanceUnit
            Unit of measure for ``odometer``.

        Returns
        -------
        ServicePlannerResponse
            The parsed completed-actions response.
        """
        return cast(
            'ServicePlannerResponse', await self._send_json(
                self.core.get_service_planner_history(vin=vin, odometer=odometer, uom=uom)))

    async def get_service_action_detail(self,
                                        service_action_id: str,
                                        *,
                                        vin: str,
                                        odometer: int | None = None,
                                        uom: DistanceUnit = 'mi') -> ServiceActionDetail:
        """
        Fetch detail for one upcoming service action.

        Parameters
        ----------
        service_action_id : str
            Identifier of the upcoming service action.
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``.
        uom : DistanceUnit
            Unit of measure for ``odometer``.

        Returns
        -------
        ServiceActionDetail
            The parsed upcoming-service-action detail (polymorphic by ``serviceType``).
        """
        return cast(
            'ServiceActionDetail', await self._send_json(
                self.core.get_service_action_detail(service_action_id,
                                                    vin=vin,
                                                    odometer=odometer,
                                                    uom=uom)))

    async def get_completed_service_action_detail(
            self,
            service_event_id: str,
            *,
            vin: str,
            odometer: int | None = None,
            uom: DistanceUnit = 'mi') -> CompletedServiceActionDetail:
        """
        Fetch detail for one completed service event.

        Parameters
        ----------
        service_event_id : str
            Identifier of the completed service event.
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``.
        uom : DistanceUnit
            Unit of measure for ``odometer``.

        Returns
        -------
        CompletedServiceActionDetail
            The parsed completed-service-event detail response.
        """
        return cast(
            'CompletedServiceActionDetail', await self._send_json(
                self.core.get_completed_service_action_detail(service_event_id,
                                                              vin=vin,
                                                              odometer=odometer,
                                                              uom=uom)))

    async def get_release_notes(self, vin: str) -> ReleaseNotesResponse | None:
        """
        Run the two-step release-notes fetch for ``vin``.

        Calls ``mmota/details`` first, then follows the ``releaseNotesUrl`` through Ford's proxy.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        ReleaseNotesResponse | None
            The parsed release-notes response, or ``None`` if no MMOTA alert / URL is available.
        """
        mmota = await self._send_json(self.core.get_mmota_details(vin))
        details = mmota.get('mmotaAlertsDetails') or []
        if not details:
            return None
        url = details[0].get('releaseNotesUrl')
        if not url:
            return None
        return cast('ReleaseNotesResponse | None', await self._send_json(
            self.core.get_release_notes(url)))

    async def get_dealer_by_pa_code(self,
                                    pa_code: str,
                                    *,
                                    brand: str | None = None) -> DealerResponse | None:
        """
        Hydrate a dealer PA code into a full dealer object.

        Parameters
        ----------
        pa_code : str
            Dealer PA code, typically pulled from ``UserGarageVehicle.preferredDealer``.
        brand : str | None
            Brand override (defaults to the core client's brand).

        Returns
        -------
        DealerResponse | None
            The parsed dealer-search response, or ``None`` when the upstream returns HTTP 204 (no
            hydrated dealer data on file for ``pa_code``).
        """
        return cast('DealerResponse | None', await self._send_json(
            self.core.get_dealer_by_pa_code(pa_code, brand=brand)))

    async def get_preferred_dealer(self, vin: str) -> DealerResponse | None:
        """
        Fetch and hydrate the preferred dealer for ``vin``.

        Looks up the garage, plucks ``preferredDealer``, then calls
        :py:meth:`get_dealer_by_pa_code`. When the dealer-search call returns no body (HTTP 204),
        still surfaces the PA code rather than reporting "no dealer" - the dealer *is* set, the
        upstream service just couldn't hydrate it.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        DealerResponse | None
            The parsed dealer-search response, or ``None`` if no preferred dealer is set on the
            garage entry. When the PA code exists but cannot be hydrated, returns a minimal
            envelope ``{'paCode': <code>}``.
        """
        garage = await self.list_garage()
        pa_code = find_preferred_dealer_code(garage, vin)
        if not pa_code:
            return None
        hydrated = await self.get_dealer_by_pa_code(pa_code)
        if hydrated is None:
            return cast('DealerResponse', {'paCode': pa_code})
        return hydrated

    async def get_roadside_symptoms(self, *, is_bev: bool = False) -> IDNameListResponse:
        """
        Fetch the roadside-assistance symptom catalogue.

        Parameters
        ----------
        is_bev : bool
            ``True`` to fetch BEV-specific symptoms; ``False`` for the general catalogue.

        Returns
        -------
        IDNameListResponse
            The parsed symptoms response.
        """
        return cast('IDNameListResponse', await self._send_json(
            self.core.get_roadside_symptoms(is_bev=is_bev)))

    async def get_roadside_location_types(self) -> IDNameListResponse:
        """
        Fetch the roadside-assistance location-type choices.

        Returns
        -------
        IDNameListResponse
            The parsed location-types response.
        """
        return cast('IDNameListResponse', await
                    self._send_json(self.core.get_roadside_location_types()))

    async def get_roadside_active_event(self,
                                        vins: str | Iterable[str]) -> RoadsideActiveResponse | None:
        """
        Fetch any currently active roadside-assistance events for the given VINs.

        Parameters
        ----------
        vins : str | Iterable[str]
            A single VIN, a comma-separated VIN string, or any iterable of VINs.

        Returns
        -------
        RoadsideActiveResponse | None
            The parsed active-event response.
        """
        return cast('RoadsideActiveResponse | None', await self._send_json(
            self.core.get_roadside_active_event(vins)))

    async def predraft_roadside_event(self,
                                      vin: str,
                                      *,
                                      customer_name: str,
                                      customer_phone: str = '') -> AckResponse:
        """
        Pre-draft a roadside-assistance event for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        customer_name : str
            Name to attach to the draft event.
        customer_phone : str
            Optional callback phone number to attach.

        Returns
        -------
        AckResponse
            The parsed pre-draft response.
        """
        return cast(
            'AckResponse', await self._send_json(
                self.core.predraft_roadside_event(vin,
                                                  customer_name=customer_name,
                                                  customer_phone=customer_phone)))

    async def list_drivers(self, vin: str) -> DriversListResponse:
        """
        List secondary drivers (both authorised and pending) for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        DriversListResponse
            The parsed authorised-users response.
        """
        return cast('DriversListResponse', await self._send_json(self.core.list_drivers(vin)))

    async def get_authorized_user_count(self, vin: str) -> DriversCountResponse:
        """
        Fetch the authorised-user count for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        DriversCountResponse
            The parsed authorised-user-count response.
        """
        return cast('DriversCountResponse', await self._send_json(
            self.core.get_authorized_user_count(vin)))

    async def invite_driver(self,
                            vin: str,
                            *,
                            secondary_email: str,
                            inviter_first_name: str,
                            vehicle_display_name: str,
                            brand: str | None = None) -> InviteResponse:
        """
        Email a secondary-driver invitation for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        secondary_email : str
            Email address of the invitee.
        inviter_first_name : str
            First name of the primary owner sending the invite.
        vehicle_display_name : str
            Name shown for the vehicle in the invitation email.
        brand : str | None
            Brand override (defaults to the core client's brand).

        Returns
        -------
        InviteResponse
            The parsed invite response.
        """
        return cast(
            'InviteResponse', await self._send_json(
                self.core.invite_driver(vin,
                                        secondary_email=secondary_email,
                                        inviter_first_name=inviter_first_name,
                                        vehicle_display_name=vehicle_display_name,
                                        brand=brand)))

    async def start_trailer_light_check(self, vin: str) -> niquests.Response:
        """
        Flash the trailer lights of ``vin`` to verify the connection (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.start_trailer_light_check(vin))

    async def stop_trailer_light_check(self, vin: str) -> niquests.Response:
        """
        Stop an active trailer-light check for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.stop_trailer_light_check(vin))

    async def start_on_demand_preconditioning(self,
                                              vin: str,
                                              *,
                                              duration: int = 0,
                                              setting: int = 2) -> niquests.Response:
        """
        Start cabin preconditioning for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        duration : int
            Value for ``preconditioningDuration``.
        setting : int
            Value for ``vehiclePreconditionSetting`` (``2`` to start).

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(
            self.core.start_on_demand_preconditioning(vin, duration=duration, setting=setting))

    async def extend_on_demand_preconditioning(self,
                                               vin: str,
                                               *,
                                               duration: int = 0,
                                               setting: int = 2) -> niquests.Response:
        """
        Extend an active preconditioning session for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        duration : int
            Value for ``preconditioningDuration``.
        setting : int
            Value for ``vehiclePreconditionSetting`` (``2`` to extend).

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(
            self.core.extend_on_demand_preconditioning(vin, duration=duration, setting=setting))

    async def stop_on_demand_preconditioning(self,
                                             vin: str,
                                             *,
                                             duration: int = 0,
                                             setting: int = 1) -> niquests.Response:
        """
        Stop an active preconditioning session for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        duration : int
            Value for ``preconditioningDuration``.
        setting : int
            Value for ``vehiclePreconditionSetting`` (``1`` to stop).

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(
            self.core.stop_on_demand_preconditioning(vin, duration=duration, setting=setting))

    async def ppo_refresh(self, vin: str) -> niquests.Response:
        """
        Trigger a one-shot Programmable Parameter Override refresh for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.ppo_refresh(vin))

    async def ppo_refresh_continuous(self,
                                     vin: str,
                                     *,
                                     frequency_min: int = 3,
                                     duration_min: int = 10) -> niquests.Response:
        """
        Start a continuous Programmable Parameter Override refresh for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        frequency_min : int
            Refresh frequency in minutes.
        duration_min : int
            Total duration in minutes.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(
            self.core.ppo_refresh_continuous(vin,
                                             frequency_min=frequency_min,
                                             duration_min=duration_min))

    async def ppo_refresh_cancel(self, vin: str) -> niquests.Response:
        """
        Cancel a continuous Programmable Parameter Override refresh for ``vin`` (experimental).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC beta command endpoint.
        """
        return await self._send(self.core.ppo_refresh_cancel(vin))

    async def honk_and_flash(self, vin: str, *, duration_s: int = 3) -> niquests.Response:
        """
        Sound the horn and flash the lights of ``vin`` (alias for :py:meth:`panic_alarm`).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        duration_s : int
            How long, in seconds, to keep the cue active.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the TMC command endpoint.
        """
        return await self._send(self.core.honk_and_flash(vin, duration_s=duration_s))

    async def get_guard_mode(self, vin: str) -> GuardModeResponse:
        """
        Read the Guard Mode session state for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        GuardModeResponse
            The parsed Guard Mode response.
        """
        return cast('GuardModeResponse', await self._send_json(self.core.get_guard_mode(vin)))

    async def set_guard_mode(self, vin: str) -> GuardModeResponse:
        """
        Enable Guard Mode for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        GuardModeResponse
            The parsed Guard Mode response.
        """
        return cast('GuardModeResponse', await self._send_json(self.core.set_guard_mode(vin)))

    async def delete_guard_mode(self, vin: str) -> GuardModeResponse:
        """
        Disable Guard Mode for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        GuardModeResponse
            The parsed Guard Mode response.
        """
        return cast('GuardModeResponse', await self._send_json(self.core.delete_guard_mode(vin)))

    async def turn_zone_lights_on(self, vin: str) -> niquests.Response:
        """
        Turn the zone lighting on for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the MPS zone-lighting endpoint.
        """
        return await self._send(self.core.turn_zone_lights_on(vin))

    async def turn_zone_lights_off(self, vin: str) -> niquests.Response:
        """
        Turn the zone lighting off for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        niquests.Response
            The raw HTTP response from the MPS zone-lighting endpoint.
        """
        return await self._send(self.core.turn_zone_lights_off(vin))

    async def set_zone_lights_mode(self, vin: str, *, zone: str) -> niquests.Response:
        """
        Select which zone(s) the lighting illuminates for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        zone : str
            The wire zone value (see :py:data:`fordpass.typing.lighting.ZoneLightZone`).

        Returns
        -------
        niquests.Response
            The raw HTTP response from the MPS zone-lighting endpoint.
        """
        return await self._send(self.core.set_zone_lights_mode(vin, zone=zone))

    async def set_zone_lighting(self,
                                vin: str,
                                target: ZoneLightZone,
                                *,
                                current: str | None = None) -> niquests.Response | None:
        """
        Set the zone lighting to ``target``, turning the lights on first when required.

        Mirrors the ha-fordpass two-step flow: a request for the ``off`` sentinel turns the lights
        off; otherwise, if ``current`` reports the lights are currently off, they are turned on and
        allowed to settle before the zone is selected. When ``current`` already equals ``target``
        no request is sent.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        target : ZoneLightZone
            The desired wire zone value, or the ``off`` sentinel.
        current : str | None
            The currently selected zone value if known. ``None`` assumes the lights are on, so the
            zone is selected directly.

        Returns
        -------
        niquests.Response | None
            The HTTP response from the final request, or ``None`` when ``current`` already matches
            ``target`` and no request was sent.
        """
        if target == ZONE_LIGHT_OFF:
            return await self.turn_zone_lights_off(vin)
        if current is not None:
            if str(current) == str(target):
                return None
            if str(current) == ZONE_LIGHT_OFF:
                await self.turn_zone_lights_on(vin)
                await asyncio.sleep(_ZONE_LIGHT_ON_SETTLE_S)
        return await self.set_zone_lights_mode(vin, zone=str(target))

    async def aclose(self) -> None:
        """Release both the niquests session and the curl-cffi auth session."""
        if self._owns_session:
            await self.session.close()
        if self._owns_auth_session:
            await self.auth_session.close()

    async def __aenter__(self) -> Self:
        """
        Enter the asynchronous context manager.

        Returns
        -------
        Self
            This client instance.
        """
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the asynchronous context manager and close any owned sessions."""
        await self.aclose()
