"""
Sans-I/O Python client for the FordPass API.

"Sans-I/O" means this module never opens a socket. Every operation returns a :class:`RequestDict` -
a plain ``TypedDict`` carrying ``method``, ``url``, ``headers``, and ``data`` - designed to be
splatted directly into the ``requests``-family of HTTP libraries::

    import requests  # or niquests / urllib3.request
    from fordpass_sansio import FordPassClient

    client = FordPassClient(cat=ford_cat, tmc=tmc_bearer)
    r = requests.request(**client.remote_start(vin='VIN1234'))
    print(r.status_code)

The same dict works with ``niquests.request``, ``urllib3.request``, and any other library whose
request signature accepts ``method=, url=, headers=, data=`` keyword arguments. For ``httpx``,
rename ``data`` → ``content`` (or post-process) before splatting; its constructor uses ``content``
for raw bytes.

The class holds NO HTTP state - no sessions, no cookies. Tokens are public attributes so the caller
controls refresh logic.

The protocol matches ``docs/openapi.json`` for FordPass APK v6.13.0. See that spec for field-level
documentation; this module is the executable companion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast
import json
import urllib.parse

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from typing_extensions import Unpack

    from .typing.common import CountryHeaderCasing, DistanceUnit
    from .typing.profile import SaveProfileFields
    from .typing.secrets import Secrets

# Nothing in this module reads disk, env, or the network at import time. The
# :py:class:`FordPassClient` constructor receives a :py:class:`Secrets` bundle which the caller
# (typically :py:mod:`fordpass.client`) supplies after loading ``~/.config/pyfordpass/abcdef.toml``
# via :py:func:`fordpass.abcdef.load_secrets`.


class RequestDict(TypedDict):
    """
    HTTP request descriptor designed to be splatted into ``requests`` / ``niquests``.

    Usage: ``requests.request(**my_request_dict)``. Works the same with ``niquests.request``
    (drop-in replacement for requests) and ``urllib3.request``.

    For ``httpx``: rename the ``data`` key to ``content`` before splatting; its constructor uses
    ``content=`` for the body parameter.

    ``data`` is ``str`` (UTF-8) because every body this client produces is text - JSON or
    URL-encoded form data, both of which the HTTP clients auto-encode on send. It's ``None`` for
    GETs and the auth-flow URL builders. All four keys are required so static type checkers see the
    dict as "complete".
    """

    data: str | None
    headers: dict[str, str]
    method: str
    url: str


class FordPassClient:  # noqa: PLR0904
    """
    Sans-I/O FordPass protocol client.

    Stateful only in the sense that it holds tokens + per-user config (country, locale, app id).
    Every public method either returns a :class:`RequestDict` or parses already-fetched data. No
    method opens a socket.
    """
    def __init__(self,
                 *,
                 secrets: Secrets,
                 cat: str | None = None,
                 cat_refresh: str | None = None,
                 tmc: str | None = None,
                 country: str = 'USA',
                 locale: str = 'en-US',
                 brand: str = 'ford') -> None:
        """
        Build a sans-I/O FordPass client with optional pre-seeded tokens.

        Parameters
        ----------
        secrets : Secrets
            API constants (hosts, B2C identifiers, user-agent, roadside ``x-source`` lookup, …) -
            see :py:func:`fordpass.abcdef.load_secrets`.
        cat : str | None
            Ford CAT access token. Sent as ``auth-token`` on ``*.ford.com`` calls.
        cat_refresh : str | None
            Ford CAT refresh token. Used as the ``subject_token`` when minting a TMC bearer.
        tmc : str | None
            TMC bearer (RS256 JWT). Required by every TMC command and telemetry call.
        country : str
            ISO-3166 alpha-3 country code sent in the ``country-code`` header.
        locale : str
            BCP-47 locale tag sent in the ``locale`` header.
        brand : str
            Sub-brand identifier (``ford``, ``lincoln``); used in query strings of multi-brand
            endpoints.
        """
        self._secrets: Secrets = secrets
        """
        API constants bundle.

        Private - call sites use it via the convenience helpers below or the public
        ``application_id`` attribute.
        """
        self.cat: str | None = cat
        """
        Ford CAT access token (EdDSA JWT, ``token_type=A``, ~30 min TTL).

        Sent as the ``auth-token`` header on ``*.ford.com`` calls.
        """
        self.cat_refresh: str | None = cat_refresh
        """
        Ford CAT refresh token (EdDSA JWT, ``token_type=R``, ~6 month TTL).

        Used as the ``subject_token`` when exchanging for the TMC bearer.
        """
        self.tmc: str | None = tmc
        """TMC bearer (RS256 JWT). Refresh every ~5 min via :meth:`exchange_cat_for_tmc`."""
        self.country = country
        """ISO-3166 alpha-3 country code (e.g. ``'USA'``)."""
        self.locale = locale
        """BCP-47 locale tag (e.g. ``'en-US'``)."""
        self.brand = brand
        """Sub-brand identifier (``'ford'`` / ``'lincoln'``)."""
        self.application_id = secrets['application_id']
        """NGSDN ``application-id`` header value (sourced from the constants bundle)."""

    def _roadside_x_source(self) -> Literal['FORD', 'LINCOLN']:
        """
        Look up the ``x-source`` header value for the configured brand.

        Returns
        -------
        Literal['FORD', 'LINCOLN']
            ``'FORD'`` for the Ford brand, ``'LINCOLN'`` for Lincoln.

        Raises
        ------
        RuntimeError
            If :attr:`brand` is not recognised by the roadside service.
        """
        try:
            value = self._secrets['roadside']['x_source'][self.brand.lower()]
        except KeyError as exc:
            known = sorted(self._secrets['roadside']['x_source'])
            msg = (f'Unsupported brand for roadside endpoints: {self.brand!r}. '
                   f'Known brands: {known}.')
            raise RuntimeError(msg) from exc
        # ``cast`` is required because ``dict[str, str]`` widens the literal.
        return cast('Literal["FORD", "LINCOLN"]', value)

    def _ford_headers(self,
                      *,
                      country_header: CountryHeaderCasing = 'country-code',
                      extra_headers: Mapping[str, str] | None = None) -> dict[str, str]:
        """
        Build the header dictionary for ``*.ford.com`` endpoints.

        Per RFC 7230 HTTP headers are case-insensitive; in practice Ford's gateway is strict about
        the exact spelling on a per-endpoint basis. Four casings have been observed across the API
        surface, each used by a different microservice:

        - ``country-code`` (kebab-lowercase, the default) - most endpoints.
        - ``countryCode`` (camelCase) - alerts, alert-history, MMOTA dashboard, release-notes.
        - ``countrycode`` (all-lowercase, no dash) - service-planner endpoints.
        - ``Country-Code`` (Title-Case kebab) - vehicle-details update / delete.

        Parameters
        ----------
        country_header : CountryHeaderCasing
            Exact spelling of the country header to send. Defaults to ``'country-code'``.
        extra_headers : Mapping[str, str] | None
            Additional headers to merge into the result, overriding the defaults.

        Returns
        -------
        dict[str, str]
            Mapping containing ``auth-token``, ``application-id``, country header, ``locale``,
            ``user-agent``, and any ``extra_headers``.

        Raises
        ------
        RuntimeError
            If :attr:`cat` has not been set (the caller has not signed in yet).
        """
        if self.cat is None:
            msg = 'FordPassClient.cat is unset - sign in first.'
            raise RuntimeError(msg)
        h = {
            'auth-token': self.cat,
            'application-id': self.application_id,
            country_header: self.country,
            'locale': self.locale,
            'user-agent': self._secrets['user_agent']
        }
        h.update(extra_headers or {})
        return h

    def _tmc_headers(self, **extras: str) -> dict[str, str]:
        """
        Build the header dictionary for TMC-plane endpoints.

        Parameters
        ----------
        **extras : str
            Additional headers to merge into the result, overriding the defaults.

        Returns
        -------
        dict[str, str]
            Mapping containing ``authorization`` plus any ``extras``.

        Raises
        ------
        RuntimeError
            If :attr:`tmc` has not been set (the caller has not exchanged the CAT yet).
        """
        if self.tmc is None:
            msg = 'FordPassClient.tmc is unset - exchange CAT for TMC first.'
            raise RuntimeError(msg)
        h = {'authorization': f'Bearer {self.tmc}', 'user-agent': self._secrets['user_agent']}
        h.update(extras)
        return h

    @staticmethod
    def _json_body(obj: Any) -> str:
        """
        Serialise ``obj`` as a compact JSON string.

        Parameters
        ----------
        obj : Any
            Any value accepted by :py:func:`json.dumps`.

        Returns
        -------
        str
            The serialised JSON without whitespace separators.
        """
        return json.dumps(obj, separators=(',', ':'))

    def b2c_authorize_url(self,
                          *,
                          code_challenge: str,
                          policy: str | None = None,
                          country: str | None = None,
                          locale: str | None = None) -> str:
        """
        Return the Azure AD B2C ``/authorize`` URL for interactive sign-in.

        Open this URL in a WebView or browser and capture the redirect to
        ``fordapp://userauthorized?code=<auth_code>`` to obtain the ``authorization_code`` for
        :py:meth:`exchange_b2c_code`.

        Parameters
        ----------
        code_challenge : str
            The PKCE S256 code challenge (base64url-encoded SHA-256 of the verifier).
        policy : str | None
            B2C user-flow / custom-policy name. Defaults to ``B2C_1A_SignInSignUp_<locale>``.
        country : str | None
            Override the instance ``country`` for this URL only.
        locale : str | None
            Override the instance ``locale`` for this URL only.

        Returns
        -------
        str
            The fully-formed authorisation URL.
        """
        b2c = self._secrets['auth']['b2c']
        locale = locale or self.locale
        policy = policy or b2c['policy_template'].format(locale=locale)
        params = {
            'redirect_uri': b2c['redirect_uri'],
            'response_type': 'code',
            'scope': f'{b2c["client_id"]} openid',
            'max_age': '3600',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'client_id': b2c['client_id'],
            'language_code': locale,
            'ford_application_id': self.application_id,
            'country_code': country or self.country
        }
        # Spaces in `scope` must be `%20`, not `+` - some WAFs (Akamai EdgeSuite) flag form-encoded
        # `+` in query strings as anomalous for browser-generated requests.
        qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        login = self._secrets['hosts']['login']
        return f'{login}/{b2c["tenant_id"]}/{policy}/oauth2/v2.0/authorize?{qs}'

    def exchange_b2c_code(self,
                          *,
                          code: str,
                          code_verifier: str,
                          policy: str | None = None) -> RequestDict:
        """
        Build the request that exchanges a B2C authorisation code for an access token.

        Parameters
        ----------
        code : str
            The ``code`` query-string value captured from the ``fordapp://userauthorized``
            redirect.
        code_verifier : str
            The PKCE code verifier paired with the ``code_challenge`` originally sent to
            :py:meth:`b2c_authorize_url`.
        policy : str | None
            B2C user-flow / custom-policy name. Defaults to ``B2C_1A_SignInSignUp_<locale>``.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST /oauth2/v2.0/token`` call.
        """
        b2c = self._secrets['auth']['b2c']
        login = self._secrets['hosts']['login']
        policy = policy or b2c['policy_template'].format(locale=self.locale)
        url = f'{login}/{b2c["tenant_id"]}/{policy}/oauth2/v2.0/token'
        body = urllib.parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': b2c['redirect_uri'],
            'client_id': b2c['client_id'],
            'code_verifier': code_verifier,
            'scope': f'{b2c["client_id"]} openid'
        })
        return RequestDict(method='POST',
                           url=url,
                           headers={
                               'content-type': 'application/x-www-form-urlencoded',
                               'user-agent': self._secrets['user_agent']
                           },
                           data=body)

    def mint_cat_from_b2c(self, *, b2c_access_token: str) -> RequestDict:
        """
        Build the request that mints a Ford CAT from a B2C access token.

        The ``application-id`` header is required (server rejects with HTTP 400 ``errorCode 432``
        "Invalid ApplicationId" otherwise). The body field is ``idpToken``, not ``ciToken``.

        Parameters
        ----------
        b2c_access_token : str
            The ``access_token`` returned by :py:meth:`exchange_b2c_code`.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST /api/token/v2/cat-with-b2c-access-token`` call.
        """
        return RequestDict(
            method='POST',
            url=f'{self._secrets["hosts"]["foundational"]}/api/token/v2/cat-with-b2c-access-token',
            headers={
                'application-id': self.application_id,
                'content-type': 'application/json',
                'user-agent': self._secrets['user_agent']
            },
            data=self._json_body({'idpToken': b2c_access_token}))

    def refresh_cat(self) -> RequestDict:
        """
        Build the request that swaps the current CAT refresh token for a fresh CAT pair.

        Mirrors the official ``refreshCustomerAuthTokens`` call:
        ``POST /api/token/v2/cat-with-refresh-token`` with body
        ``{"refresh_token": <cat_refresh>}``. The response carries a new ``access_token`` (the CAT)
        and usually a rotated ``refresh_token``.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST /api/token/v2/cat-with-refresh-token`` call.

        Raises
        ------
        RuntimeError
            If :attr:`cat_refresh` is unset.
        """
        if self.cat_refresh is None:
            msg = 'FordPassClient.cat_refresh is unset - cannot refresh the CAT.'
            raise RuntimeError(msg)
        return RequestDict(
            method='POST',
            url=f'{self._secrets["hosts"]["foundational"]}/api/token/v2/cat-with-refresh-token',
            headers={
                'application-id': self.application_id,
                'content-type': 'application/json',
                'user-agent': self._secrets['user_agent']
            },
            data=self._json_body({'refresh_token': self.cat_refresh}))

    def exchange_cat_for_tmc(self) -> RequestDict:
        """
        Build the RFC 8693 token-exchange request that mints a TMC bearer from the CAT refresh.

        The official app posts the CAT **refresh** token (``token_type=R``, ~6 month TTL), not the
        access token. It also includes ``subject_issuer=fordpass``.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST /v1/auth/oidc/token`` call.

        Raises
        ------
        RuntimeError
            If :attr:`cat_refresh` is unset.
        """
        if self.cat_refresh is None:
            msg = 'FordPassClient.cat_refresh is unset - mint a CAT first.'
            raise RuntimeError(msg)
        body = urllib.parse.urlencode({
            'client_id': self._secrets['auth']['tmc']['client_id'],
            'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
            'subject_issuer': 'fordpass',
            'subject_token': self.cat_refresh,
            'subject_token_type': 'urn:ietf:params:oauth:token-type:jwt'
        })
        return RequestDict(method='POST',
                           url=f'{self._secrets["hosts"]["tmc_accounts"]}/v1/auth/oidc/token',
                           headers={
                               'content-type': 'application/x-www-form-urlencoded',
                               'user-agent': self._secrets['user_agent']
                           },
                           data=body)

    def _tmc_command(self,
                     vin: str,
                     type_: str,
                     *,
                     properties: Mapping[str, object] | None = None,
                     wake_up: bool = True,
                     beta: bool = False,
                     version: str | None = None) -> RequestDict:
        """
        Build a TMC ``POST /commands`` request for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        type_ : str
            The command identifier (for example ``remoteStart``, ``lock``).
        properties : Mapping[str, object] | None
            Optional command payload merged under the ``properties`` key.
        wake_up : bool
            Whether to wake the TCU before delivering the command.
        beta : bool
            If ``True``, route the request through the ``/v1beta`` endpoint.
        version : str | None
            Optional command-schema version (required by some beta commands).

        Returns
        -------
        RequestDict
            Descriptor for the TMC ``POST /commands`` call.
        """
        path = '/v1beta/command' if beta else '/v1/command'
        body: dict[str, Any] = {
            'properties': properties or {},
            'tags': {},
            'type': type_,
            'wakeUp': wake_up
        }
        if version is not None:
            body['version'] = version
        return RequestDict(method='POST',
                           url=f'{self._secrets["hosts"]["tmc"]}{path}/vehicles/{vin}/commands',
                           headers={
                               **self._tmc_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body(body))

    def remote_start(self, vin: str) -> RequestDict:
        """
        Build the request that starts the engine remotely for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``remoteStart`` TMC command.
        """
        return self._tmc_command(vin, 'remoteStart')

    def cancel_remote_start(self, vin: str) -> RequestDict:
        """
        Build the request that cancels an active remote-start session for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``cancelRemoteStart`` TMC command.
        """
        return self._tmc_command(vin, 'cancelRemoteStart')

    def extend_remote_start(self, vin: str) -> RequestDict:
        """
        Build the request that extends an active remote-start session for ``vin``.

        Wire body is identical to :py:meth:`remote_start` - the server distinguishes start
        vs. extend from current vehicle state.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the extend command.
        """
        return self._tmc_command(vin, 'remoteStart')

    def lock(self, vin: str) -> RequestDict:
        """
        Build the request that locks the doors of ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``lock`` TMC command.
        """
        return self._tmc_command(vin, 'lock')

    def unlock(self, vin: str) -> RequestDict:
        """
        Build the request that unlocks the doors of ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``unlock`` TMC command.
        """
        return self._tmc_command(vin, 'unlock')

    def status_refresh(self, vin: str) -> RequestDict:
        """
        Build the request that forces the TCU to push fresh state to the server.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``statusRefresh`` TMC command.
        """
        return self._tmc_command(vin, 'statusRefresh')

    def panic_alarm(self, vin: str, duration_s: int = 3) -> RequestDict:
        """
        Build the request that sounds the horn and flashes the lights.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        duration_s : int
            How long, in seconds, to keep the panic cue active.

        Returns
        -------
        RequestDict
            Descriptor for the ``startPanicCue`` TMC command.
        """
        return self._tmc_command(vin, 'startPanicCue', properties={'duration': duration_s})

    def get_asu_settings(self, vin: str) -> RequestDict:
        """
        Build the request that reads current Automatic Software Update settings.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``getASUSettingsCommand`` beta TMC command.
        """
        return self._tmc_command(vin, 'getASUSettingsCommand', beta=True, version='1.0.0')

    def set_asu_enabled(self, vin: str, *, enabled: bool) -> RequestDict:
        """
        Build the request that toggles automatic software updates.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        enabled : bool
            ``True`` to enable automatic updates, ``False`` to disable them.

        Returns
        -------
        RequestDict
            Descriptor for the ``publishASUSettingsCommand`` beta TMC command.
        """
        return self._tmc_command(vin,
                                 'publishASUSettingsCommand',
                                 properties={'ASUState': 'ON' if enabled else 'OFF'},
                                 beta=True,
                                 version='1.0.0')

    def set_asu_schedule(self, vin: str, *, day_schedules: Sequence[Mapping[str, object]],
                         activation_setting: str) -> RequestDict:
        """
        Build the request that sets the day-of-week / time window for automatic updates.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        day_schedules : list[Any]
            The per-day schedule blocks for the ``OTAActivationDaySchedule`` field.
        activation_setting : str
            The wire value for ``activationScheduleSetting``.

        Returns
        -------
        RequestDict
            Descriptor for the ``scheduleASUActivationCommand`` beta TMC command.
        """
        return self._tmc_command(vin,
                                 'scheduleASUActivationCommand',
                                 properties={
                                     'OTAActivationDaySchedule': day_schedules,
                                     'activationScheduleSetting': activation_setting
                                 },
                                 beta=True,
                                 version='1.0.0')

    def query_telemetry(self, vin: str, metrics: Iterable[str] | None = None) -> RequestDict:
        """
        Build the request that fetches a one-shot snapshot of vehicle telemetry.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        metrics : Iterable[str] | None
            ``None`` or empty returns all 58 fields. Otherwise filter to the listed metric keys
            (for example ``['fuelLevel', 'odometer']``).

        Returns
        -------
        RequestDict
            Descriptor for the ``POST .../vehicles/{vin}:query`` telemetry call.
        """
        body: dict[str, Any] = {}
        if metrics:
            body['includeMetrics'] = list(metrics)
        host = self._secrets['hosts']['tmc']
        return RequestDict(method='POST',
                           url=f'{host}/v1beta/telemetry/sources/fordpass/vehicles/{vin}:query',
                           headers={
                               **self._tmc_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body(body))

    # convenience: single-metric shortcuts
    def get_fuel_level(self, vin: str) -> RequestDict:
        """
        Build a telemetry request that returns only the fuel-level and range metrics.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the telemetry query.
        """
        return self.query_telemetry(vin, ['fuelLevel', 'fuelRange'])

    def get_odometer(self, vin: str) -> RequestDict:
        """
        Build a telemetry request that returns only the odometer metric and its display unit.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the telemetry query.
        """
        return self.query_telemetry(vin, ['odometer', 'displaySystemOfMeasure'])

    def get_position(self, vin: str) -> RequestDict:
        """
        Build a telemetry request that returns only the GPS position metric.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the telemetry query.
        """
        return self.query_telemetry(vin, ['position', 'heading', 'compassDirection'])

    def get_tire_pressure(self, vin: str) -> RequestDict:
        """
        Build a telemetry request that returns only the tyre-pressure metrics.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the telemetry query.
        """
        return self.query_telemetry(
            vin, ['tirePressure', 'tirePressureStatus', 'tirePressureSystemStatus'])

    def get_oil_life(self, vin: str) -> RequestDict:
        """
        Build a telemetry request that returns only the remaining-oil-life metric.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the telemetry query.
        """
        return self.query_telemetry(vin, ['oilLifeRemaining'])

    def get_next_departure(self, vin: str) -> RequestDict:
        """
        Build a telemetry request for the next-departure schedule tree (EV/PHEV only).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the telemetry query.
        """
        return self.query_telemetry(vin,
                                    ['xevDepartureSchedules', 'xevNextDepartureTimeScheduleId'])

    def list_remote_start_schedules(self, vin: str) -> RequestDict:
        """
        Build the request that lists the recurring remote-start schedules for ``vin``.

        Despite being a read-only fetch the upstream service uses a ``POST`` with a
        ``{"vin": <vin>}`` JSON body.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST .../getschedules`` call.
        """
        return RequestDict(
            method='POST',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/srsm/vehicles/v3/getschedules',
            headers={
                **self._ford_headers(), 'content-type': 'application/json'
            },
            data=self._json_body({'vin': vin}))

    def add_remote_start_schedule(self,
                                  vin: str,
                                  *,
                                  start_time: str,
                                  request_start_date: str,
                                  time_zone: int,
                                  days: Mapping[str, int],
                                  status: int = 1) -> RequestDict:
        """
        Build the request that creates a new recurring remote-start schedule.

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
            Mapping such as ``{'mon': 1, 'tue': 0, ...}``; keys for all seven days are
            required by the wire format.
        status : int
            ``1`` for active, ``0`` for disabled.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST .../startschedules`` call.
        """
        body = {
            'vin': vin,
            'requestStartDate': request_start_date,
            'startTime': start_time,
            'timeZone': time_zone,
            'status': status,
            **{
                d: days.get(d, 0)
                for d in ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
            }
        }
        return RequestDict(
            method='POST',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/srsm/vehicles/v3/startschedules',
            headers={
                **self._ford_headers(), 'content-type': 'application/json'
            },
            data=self._json_body(body))

    def delete_remote_start_schedule(self, schedule_id: int, *, vin: str) -> RequestDict:
        """
        Build the request that deletes a remote-start schedule by ID.

        This is a ``DELETE`` with a body. Some HTTP transports (older HttpClient, certain
        proxies/CDNs) strip ``DELETE`` bodies; if you see 4xx errors, check that your
        transport preserves them. The VIN is required server-side even though the schedule
        ID is in the path - the server validates the ``(vin, schedule_id)`` pair.

        Parameters
        ----------
        schedule_id : int
            Server-assigned identifier of the schedule entry.
        vin : str
            The VIN that owns the schedule.

        Returns
        -------
        RequestDict
            Descriptor for the ``DELETE .../startschedules/{schedule_id}`` call.
        """
        host = self._secrets['hosts']['vehicle']
        return RequestDict(method='DELETE',
                           url=f'{host}/api/srsm/vehicles/v3/startschedules/{schedule_id}',
                           headers={
                               **self._ford_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body({'vin': vin}))

    def toggle_remote_start_schedule(self, schedule_id: int, *,
                                     schedule_body: Mapping[str, str | int | None]) -> RequestDict:
        """
        Build the request that PUTs an updated remote-start schedule.

        Typically used to flip ``status`` between ``0`` and ``1``.

        Parameters
        ----------
        schedule_id : int
            Server-assigned identifier of the schedule entry.
        schedule_body : Mapping[str, Any]
            Full body as returned by the read-side ``getschedules`` call, with ``status``
            toggled.

        Returns
        -------
        RequestDict
            Descriptor for the ``PUT .../startschedules/{schedule_id}`` call.
        """
        host = self._secrets['hosts']['vehicle']
        return RequestDict(method='PUT',
                           url=f'{host}/api/srsm/vehicles/v3/startschedules/{schedule_id}',
                           headers={
                               **self._ford_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body(dict(schedule_body)))

    def list_garage(self) -> RequestDict:
        """
        Build the request that lists all vehicles in the user's garage.

        Includes nickname, plate, preferred-dealer code, vehicle image URL, and capabilities.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/fpcpl-user-garage-service/v1/user/garage`` call.
        """
        return RequestDict(
            method='GET',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/fpcpl-user-garage-service/v1/user/garage',
            headers=self._ford_headers(),
            data=None)

    def update_vehicle_details(self,
                               vin: str,
                               *,
                               nick_name: str | None = None,
                               license_plate: str | None = None,
                               mileage: int | None = None,
                               preferred_dealer: str | None = None) -> RequestDict:
        """
        Build the request that updates nickname / plate / mileage / preferred dealer.

        Note the wire JSON keys differ from intuitive camelCase: ``licenseplate`` is all-lowercase
        and ``mileage`` is the wire name for odometer.

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
        RequestDict
            Descriptor for the ``PUT /api/user/garage/auth/{vin}`` call.
        """
        body: dict[str, Any] = {}
        if nick_name is not None:
            body['nickName'] = nick_name
        if license_plate is not None:
            body['licenseplate'] = license_plate
        if mileage is not None:
            body['mileage'] = mileage
        if preferred_dealer is not None:
            body['preferredDealer'] = preferred_dealer
        # The update endpoint lives on the Foundational host, not the vehicle host - despite
        # living under ``/api/user/garage/...`` (which superficially looks like a vehicle-service
        # path). Empirically: ``vehicle.ford.com`` returns 404, ``foundational.ford.com`` returns
        # 200.
        return RequestDict(method='PUT',
                           url=(f'{self._secrets["hosts"]["foundational"]}'
                                f'/api/user/garage/auth/{vin}'),
                           headers={
                               **self._ford_headers(country_header='Country-Code'), 'content-type':
                                   'application/json'
                           },
                           data=self._json_body(body))

    def get_profile(self, *, profile_groups: str | None = None) -> RequestDict:
        """
        Build the request that fetches user account information.

        The upstream gateway treats ``profileGroups`` as effectively required - omitting it
        returns HTTP 400 ``ERR-4014`` - and rejects the bareword ``'all'``. Each section name must
        be listed explicitly. This builder defaults to every known section.

        Parameters
        ----------
        profile_groups : str | None
            Comma-separated subset of profile sections (for example ``'names,address'``). Defaults
            to the full known section list.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/user-profile-lookup/v1/users/me`` call.
        """
        groups = profile_groups or self._secrets['profile_groups_default']
        qs = f'?profileGroups={urllib.parse.quote(groups)}'
        return RequestDict(
            method='GET',
            url=f'{self._secrets["hosts"]["foundational"]}/api/user-profile-lookup/v1/users/me{qs}',
            headers=self._ford_headers(),
            data=None)

    def save_profile(self, **fields: Unpack[SaveProfileFields]) -> RequestDict:
        """
        Build the request that PATCHes user account information.

        Pass any subset of the :py:class:`SaveProfileFields` keys. See the OpenAPI
        ``UpdateUserProfileV2Request`` schema for full sub-shapes.

        Parameters
        ----------
        **fields : Unpack[SaveProfileFields]
            Profile section objects keyed by section name.

        Returns
        -------
        RequestDict
            Descriptor for the ``PATCH /api/user-profile-management/v1/users/me`` call.
        """
        return RequestDict(
            method='PATCH',
            url=f'{self._secrets["hosts"]["foundational"]}/api/user-profile-management/v1/users/me',
            headers={
                **self._ford_headers(), 'content-type': 'application/json'
            },
            data=self._json_body(dict(fields)))

    def get_messages(self) -> RequestDict:
        """
        Build the request that fetches the user's message-centre inbox.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/messagecenter/v3/messages`` call.
        """
        return RequestDict(
            method='GET',
            url=f'{self._secrets["hosts"]["foundational"]}/api/messagecenter/v3/messages',
            headers=self._ford_headers(),
            data=None)

    def delete_messages(self, message_ids: Iterable[int]) -> RequestDict:
        """
        Build the request that bulk-deletes message-centre entries.

        ``DELETE /api/messagecenter/v3/user/messages`` with body ``{"messageIds": [<int>, ...]}``.

        Parameters
        ----------
        message_ids : Iterable[int]
            Numeric IDs from the inbox ``messageId`` field. String values are accepted and coerced.

        Returns
        -------
        RequestDict
            Descriptor for the ``DELETE /api/messagecenter/v3/user/messages`` call.
        """
        ids = [int(i) for i in message_ids]
        return RequestDict(
            method='DELETE',
            url=f'{self._secrets["hosts"]["foundational"]}/api/messagecenter/v3/user/messages',
            headers={
                **self._ford_headers(), 'content-type': 'application/json'
            },
            data=self._json_body({'messageIds': ids}))

    def mark_messages_read(self, message_ids: Iterable[int]) -> RequestDict:
        """
        Build the request that bulk-marks message-centre entries as read.

        Same body shape as :py:meth:`delete_messages`, but delivered with ``PUT`` against
        ``/messages/read``.

        Parameters
        ----------
        message_ids : Iterable[int]
            Numeric IDs from the inbox ``messageId`` field. String values are accepted and coerced.

        Returns
        -------
        RequestDict
            Descriptor for the ``PUT /api/messagecenter/v3/user/messages/read`` call.
        """
        ids = [int(i) for i in message_ids]
        return RequestDict(
            method='PUT',
            url=f'{self._secrets["hosts"]["foundational"]}/api/messagecenter/v3/user/messages/read',
            headers={
                **self._ford_headers(), 'content-type': 'application/json'
            },
            data=self._json_body({'messageIds': ids}))

    def get_alerts(self, vin: str, *, trace_id: str | None = None) -> RequestDict:
        """
        Build the request that fetches current vehicle alerts.

        ``trace_id`` is a UUID; if omitted the caller should supply one (kept as caller
        responsibility because UUID generation is mild I/O).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        trace_id : str | None
            Optional value for the ``trace-id`` header.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST /api/expvehiclealerts/v3/details`` call.
        """
        extras: dict[str, str] = {}
        if trace_id is not None:
            extras['Trace-id'] = trace_id
        # The xapi-alerts service is strict about header field-name casing - it requires
        # ``countryCode`` (camelCase) rather than the kebab-case ``country-code`` used elsewhere.
        # Mismatched names cause the gateway to return 404 on the otherwise-valid POST.
        base = self._ford_headers(country_header='countryCode', extra_headers=extras)
        return RequestDict(
            method='POST',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/expvehiclealerts/v3/details',
            headers={
                **base, 'content-type': 'application/json'
            },
            data=self._json_body({'VIN': vin}))

    def get_alert_history(self, vin: str, *, brand: str | None = None) -> RequestDict:
        """
        Build the request that fetches the fully hydrated alert history for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.
        brand : str | None
            Brand override (defaults to the instance ``brand``).

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /vehicle-alert-history/v1/getAlertHistory`` call.
        """
        params = {'brand': brand or self.brand, 'vin': vin}
        # getAlertHistory requires ``countryCode`` (camelCase); other casings return 404.
        host = self._secrets['hosts']['vehicle']
        return RequestDict(
            method='GET',
            url=f'{host}/vehicle-alert-history/v1/getAlertHistory?{urllib.parse.urlencode(params)}',
            headers=self._ford_headers(country_header='countryCode'),
            data=None)

    def _service_planner(self, path: str, *, vin: str, odometer: int | None,
                         uom: DistanceUnit) -> RequestDict:
        """
        Build a service-planner ``GET`` request to ``path`` with the canonical wire shape.

        The service-planner endpoints share an unusual contract: the VIN goes in a ``vin`` header
        (not the URL or query), the country header is the all-lowercase ``countrycode`` (not the
        conventional ``country-code`` or camelCase ``countryCode``), and ``odometer`` is a
        *nullable* query parameter - the server tolerates its absence.

        Parameters
        ----------
        path : str
            Service-planner endpoint path under
            :data:`self._secrets['hosts']['vehicle']`.
        vin : str
            VIN of the target vehicle (sent as the ``vin`` request header).
        odometer : int | None
            Current odometer reading in ``uom``. Pass ``None`` to omit the query
            parameter - the upstream endpoint accepts the call without it.
        uom : DistanceUnit
            Unit of measure (``'mi'`` or ``'km'``) for ``odometer``.

        Returns
        -------
        RequestDict
            Descriptor for the configured ``GET`` call.
        """
        params: dict[str, str | int] = {
            'locale': self.locale.lower(),
            'uom': uom,
            'brand': self.brand
        }
        if odometer is not None:
            params['odometer'] = odometer
        return RequestDict(method='GET',
                           url=(f'{self._secrets["hosts"]["vehicle"]}{path}'
                                f'?{urllib.parse.urlencode(params)}'),
                           headers=self._ford_headers(country_header='countrycode',
                                                      extra_headers={'vin': vin}),
                           data=None)

    def get_service_planner_upcoming(self,
                                     *,
                                     vin: str,
                                     odometer: int | None = None,
                                     uom: DistanceUnit = 'mi') -> RequestDict:
        """
        Build the request that fetches the upcoming-services planner summary.

        Parameters
        ----------
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``. ``None`` omits the query parameter;
            the server will still compute the summary but cannot enrich rows with
            "miles since" / "due in" context.
        uom : DistanceUnit
            Unit of measure for ``odometer`` (``'mi'`` or ``'km'``).

        Returns
        -------
        RequestDict
            Descriptor for the planner-summary call.
        """
        return self._service_planner('/fpcpl-service-planner/service-actions/planner-summary',
                                     vin=vin,
                                     odometer=odometer,
                                     uom=uom)

    def get_service_planner_history(self,
                                    *,
                                    vin: str,
                                    odometer: int | None = None,
                                    uom: DistanceUnit = 'mi') -> RequestDict:
        """
        Build the request that fetches the completed-services planner summary.

        Parameters
        ----------
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``. ``None`` omits the query parameter;
            the completed-summary endpoint is unlikely to need it (the official app
            sends it for parity with the upcoming endpoint).
        uom : DistanceUnit
            Unit of measure for ``odometer`` (``'mi'`` or ``'km'``).

        Returns
        -------
        RequestDict
            Descriptor for the completed-service-actions summary call.
        """
        return self._service_planner(
            '/fpcpl-service-planner/v1/completed-service-actions/planner-summary',
            vin=vin,
            odometer=odometer,
            uom=uom)

    def get_service_action_detail(self,
                                  service_action_id: str,
                                  *,
                                  vin: str,
                                  odometer: int | None = None,
                                  uom: DistanceUnit = 'mi') -> RequestDict:
        """
        Build the request that fetches detail for one upcoming service action.

        Parameters
        ----------
        service_action_id : str
            Identifier of the upcoming service action (returned by
            :py:meth:`get_service_planner_upcoming`).
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``.
        uom : DistanceUnit
            Unit of measure for ``odometer``.

        Returns
        -------
        RequestDict
            Descriptor for the upcoming-service-action detail call.
        """
        return self._service_planner(
            f'/fpcpl-service-planner/service-actions/{urllib.parse.quote(service_action_id)}',
            vin=vin,
            odometer=odometer,
            uom=uom)

    def get_completed_service_action_detail(self,
                                            service_event_id: str,
                                            *,
                                            vin: str,
                                            odometer: int | None = None,
                                            uom: DistanceUnit = 'mi') -> RequestDict:
        """
        Build the request that fetches detail for one completed service event.

        Parameters
        ----------
        service_event_id : str
            Identifier of the completed service event (returned by
            :py:meth:`get_service_planner_history`).
        vin : str
            VIN of the target vehicle.
        odometer : int | None
            Current odometer reading in ``uom``.
        uom : DistanceUnit
            Unit of measure for ``odometer``.

        Returns
        -------
        RequestDict
            Descriptor for the completed-service-action detail call.
        """
        return self._service_planner(
            f'/fpcpl-service-planner/v1/completed-service-actions/'
            f'{urllib.parse.quote(service_event_id)}',
            vin=vin,
            odometer=odometer,
            uom=uom)

    def get_mmota_details(self, vin: str) -> RequestDict:
        """
        Build the request for step 1 of the release-notes fetch.

        The response carries ``mmotaAlertsDetails[].releaseNotesUrl``, which is then passed
        to :py:meth:`get_release_notes`.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/mmota/v2/details`` call.
        """
        # MmotaDashboardService declares ``@Header("countryCode")`` (camelCase).
        host = self._secrets['hosts']['vehicle']
        return RequestDict(method='GET',
                           url=f'{host}/api/mmota/v2/details?vin={urllib.parse.quote(vin)}',
                           headers=self._ford_headers(country_header='countryCode'),
                           data=None)

    def get_release_notes(self, release_notes_url: str) -> RequestDict:
        """
        Build the request for step 2 of the release-notes fetch.

        Fetches the notes through Ford's proxy. The URL goes into a ``release-notes-url``
        header (not a query parameter - this is unusual and easy to miss).

        Parameters
        ----------
        release_notes_url : str
            The URL captured from :py:meth:`get_mmota_details`.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/expvsureleasenotes/v2/details`` call.
        """
        # ``@Header("countryCode")`` per OtaService; the URL travels in a
        # ``releaseNotesUrl`` header rather than a query parameter.
        return RequestDict(
            method='GET',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/expvsureleasenotes/v2/details',
            headers=self._ford_headers(country_header='countryCode',
                                       extra_headers={'releaseNotesUrl': release_notes_url}),
            data=None)

    def get_dealer_by_pa_code(self, pa_code: str, *, brand: str | None = None) -> RequestDict:
        """
        Build the request that hydrates a dealer PA code into the full dealer object.

        Parameters
        ----------
        pa_code : str
            Dealer PA code, typically pulled from ``UserGarageVehicle.preferredDealer``.
        brand : str | None
            Brand override (defaults to the instance ``brand``).

        Returns
        -------
        RequestDict
            Descriptor for the ``POST /api/dealersearch/v2/dealer`` call.
        """
        # The dealer-search endpoint requires every field name in snake_case; the gateway rejects
        # camelCase variants with HTTP 400. ``countrycode`` (all lowercase) is intentional, not a
        # typo. The ``language`` field needs the ISO 639-1 two-letter form (``'en'``); the full
        # BCP-47 ``'en-US'`` triggers ``2412400 invalid or missing languagecode``.
        body = {
            'brand': brand or self.brand,
            'countrycode': self.country,
            'cupid': '',
            'dealer_id': '',
            'device': {},
            'input_echo': True,
            'language': self.locale.split('-', 1)[0],
            'pa_code': pa_code
        }
        return RequestDict(method='POST',
                           url=f'{self._secrets["hosts"]["vehicle"]}/api/dealersearch/v2/dealer',
                           headers={
                               **self._ford_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body(body))

    def get_roadside_symptoms(self, *, is_bev: bool = False) -> RequestDict:
        """
        Build the request that lists the roadside-assistance symptom catalogue.

        Parameters
        ----------
        is_bev : bool
            ``True`` to fetch BEV-specific symptoms; ``False`` for the general catalogue.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/roadsideassistancena/v1/symptoms`` call.
        """
        extras: dict[str, str] = {'x-source': self._roadside_x_source()}
        host = self._secrets['hosts']['vehicle']
        is_bev_param = 'true' if is_bev else 'false'
        return RequestDict(method='GET',
                           url=f'{host}/api/roadsideassistancena/v1/symptoms?isBEV={is_bev_param}',
                           headers=self._ford_headers(extra_headers=extras),
                           data=None)

    def get_roadside_location_types(self) -> RequestDict:
        """
        Build the request that lists roadside-assistance location-type choices.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/roadsideassistancena/v1/locationtypes`` call.
        """
        extras: dict[str, str] = {'x-source': self._roadside_x_source()}
        return RequestDict(
            method='GET',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/roadsideassistancena/v1/locationtypes',
            headers=self._ford_headers(extra_headers=extras),
            data=None)

    def get_roadside_active_event(self, vins: str | Iterable[str]) -> RequestDict:
        """
        Build the request that fetches any currently active roadside-assistance event.

        Parameters
        ----------
        vins : str | Iterable[str]
            A single VIN, a comma-separated VIN string, or any iterable of VINs to query.

        Returns
        -------
        RequestDict
            Descriptor for the ``GET /api/roadsideassistancena/v1/event/active`` call.
        """
        if not isinstance(vins, str):
            vins = ','.join(vins)
        extras: dict[str, str] = {'x-source': self._roadside_x_source()}
        host = self._secrets['hosts']['vehicle']
        quoted = urllib.parse.quote(vins)
        return RequestDict(method='GET',
                           url=f'{host}/api/roadsideassistancena/v1/event/active?vins={quoted}',
                           headers=self._ford_headers(extra_headers=extras),
                           data=None)

    def predraft_roadside_event(self,
                                vin: str,
                                *,
                                customer_name: str,
                                customer_phone: str = '') -> RequestDict:
        """
        Build the request that pre-drafts a roadside-assistance event for ``vin``.

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
        RequestDict
            Descriptor for the ``PUT /api/roadsideassistancena/v1/event/predraft`` call.
        """
        return RequestDict(
            method='PUT',
            url=f'{self._secrets["hosts"]["vehicle"]}/api/roadsideassistancena/v1/event/predraft',
            headers={
                **self._ford_headers(), 'content-type': 'application/json'
            },
            data=self._json_body({
                'vin': vin,
                'customer': {
                    'name': customer_name,
                    'phone': customer_phone
                }
            }))

    def list_drivers(self, vin: str) -> RequestDict:
        """
        Build the request that lists secondary drivers (both authorised and pending).

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST .../getAuthorizedUsers`` call.
        """
        host = self._secrets['hosts']['vehicle']
        return RequestDict(method='POST',
                           url=f'{host}/api/fpcpl-secondary-auth-service/v2/getAuthorizedUsers',
                           headers={
                               **self._ford_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body({'vin': vin}))

    def get_authorized_user_count(self, vin: str) -> RequestDict:
        """
        Build the request that returns the authorised-user count for ``vin``.

        Parameters
        ----------
        vin : str
            The target vehicle VIN.

        Returns
        -------
        RequestDict
            Descriptor for the ``POST .../authorized-user-count`` call.
        """
        host = self._secrets['hosts']['vehicle']
        return RequestDict(method='POST',
                           url=f'{host}/api/fpcpl-secondary-auth-service/v1/authorized-user-count',
                           headers={
                               **self._ford_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body({'vin': vin}))

    def invite_driver(self,
                      vin: str,
                      *,
                      secondary_email: str,
                      inviter_first_name: str,
                      vehicle_display_name: str,
                      brand: str | None = None) -> RequestDict:
        """
        Build the request that emails a secondary-driver invitation for ``vin``.

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
            Brand override (defaults to the instance ``brand``).

        Returns
        -------
        RequestDict
            Descriptor for the ``POST .../sendInvite`` call.
        """
        body = {
            'vin': vin,
            'brand': brand or self.brand,
            'secondaryEmail': secondary_email,
            'userFirstName': inviter_first_name,
            'vehicleName': vehicle_display_name
        }
        host = self._secrets['hosts']['vehicle']
        return RequestDict(method='POST',
                           url=f'{host}/api/fpcpl-secondary-auth-service/v1/sendInvite',
                           headers={
                               **self._ford_headers(), 'content-type': 'application/json'
                           },
                           data=self._json_body(body))
