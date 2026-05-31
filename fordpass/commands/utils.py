"""
Command-layer helpers.

Async/sync bridge, token storage, PKCE, sign-in, input validation, locale-aware formatting, and
the remote-command readiness gate.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import asyncio
import base64
import functools
import hashlib
import json
import re
import secrets
import string
import urllib.parse
import webbrowser  # noqa: F401

from bascom import setup_logging
from fordpass.client import AsyncFordPassClient
from fordpass.config import CONFIG_FILE, load_config, resolve_output_format
from fordpass.timezone_map import FORD_ZONE_BY_IANA
from fordpass.utils import scalar_metric_value, walk_mapping
from platformdirs import user_state_dir
from rich.console import Console
import click
import tomlkit

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Iterable
    from logging.config import _LoggerConfiguration

    from click.decorators import FC
    import niquests

__all__ = ('STATE_DIR', 'TOKEN_FILE', 'UOM_CHOICE', 'Readiness', 'ack', 'assert_ready_or_abort',
           'check_readiness', 'console', 'debug_option', 'delete_toml_file', 'delete_toml_key',
           'dump_json', 'duration_range', 'ensure_signed_in', 'force_option',
           'format_ford_request_date', 'format_iso_date', 'format_iso_datetime', 'format_iso_time',
           'install_loop', 'interactive_signin', 'json_option', 'load_tokens', 'make_client',
           'parse_user_datetime', 'parse_user_days', 'parse_user_timezone', 'persist_tokens',
           'render_config', 'run_async', 'save_tokens', 'set_toml_key', 'should_emit_json',
           'validate_message_ids_exist', 'validate_vin', 'vin_argument', 'vin_option',
           'with_client')

_LOGGERS: dict[str, _LoggerConfiguration] = {
    'curl_cffi': {},
    'fordpass': {},
    'niquests': {},
    'quic': {
        'level': 'CRITICAL'
    },
    'urllib3': {},
    'urllib3.util.retry': {
        'level': 'WARNING'
    }
}
"""
Logger configuration applied when ``-d/--debug`` is set on any leaf command.

:meta hide-value:
"""


def debug_option(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Attach ``-d/--debug`` to a leaf command and route it through :py:func:`setup_logging`.

    The wrapped command must be a Click callback. The decorator pops ``debug`` from the keyword
    arguments before delegating, so the wrapped callback does not need to declare it.

    Parameters
    ----------
    func : Callable[..., Any]
        The Click callback to decorate.

    Returns
    -------
    Callable[..., Any]
        A new Click callback that adds ``-d/--debug`` to the command.
    """
    @click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
    @functools.wraps(func)
    def wrapper(*args: Any, debug: bool = False, **kwargs: Any) -> Any:
        setup_logging(debug=debug, loggers=_LOGGERS)
        return func(*args, **kwargs)

    return wrapper


console = Console()
"""
Shared Rich :py:class:`~rich.console.Console` used by command-side pretty printouts.

:meta hide-value:
"""

_LOOP: asyncio.AbstractEventLoop | None = None


def install_loop(loop: asyncio.AbstractEventLoop) -> None:
    """
    Install the running event loop so :func:`run_async` can dispatch onto it.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The loop returned by :func:`asyncio.get_running_loop` from inside
        :func:`fordpass.commands.main`.
    """
    global _LOOP  # noqa: PLW0603
    _LOOP = loop


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Schedule ``coro`` on the loop installed by :func:`install_loop`.

    Parameters
    ----------
    coro : Coroutine[Any, Any, Any]
        The awaitable to run.

    Returns
    -------
    Any
        Whatever the coroutine returns.

    Raises
    ------
    RuntimeError
        If :func:`install_loop` has not been called yet.
    """
    if _LOOP is None:
        msg = 'Event loop is not running. Did you call run_async outside main()?'
        raise RuntimeError(msg)
    fut = asyncio.run_coroutine_threadsafe(coro, _LOOP)
    return fut.result()


STATE_DIR = Path(user_state_dir(appname='pyfordpass', appauthor=False))
"""
Directory used for token storage, located via :mod:`platformdirs`.

Resolves to ``~/.local/state/pyfordpass`` on Linux (XDG state-home), matching
``~/.local/state/...`` convention for short-lived runtime credentials.

:meta hide-value:
"""

TOKEN_FILE = STATE_DIR / 'tokens.json'
"""
Path to the persisted CAT/CAT-refresh/TMC token JSON file.

:meta hide-value:
"""


def load_tokens() -> dict[str, Any]:
    """
    Load the saved token bundle.

    Returns
    -------
    dict[str, Any]
        The bundle ``{cat, cat_refresh, tmc}`` if present; empty dict otherwise.
    """
    if TOKEN_FILE.exists():
        return cast('dict[str, Any]', json.loads(TOKEN_FILE.read_text()))
    return {}


def save_tokens(d: dict[str, Any]) -> None:
    """
    Persist the token bundle to :data:`TOKEN_FILE`.

    Parameters
    ----------
    d : dict[str, Any]
        The bundle to write. File mode is set to ``0o600`` after write.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(d, indent=2, sort_keys=True))
    TOKEN_FILE.chmod(0o600)


def persist_tokens(client: AsyncFordPassClient) -> None:
    """
    Snapshot the current ``(cat, cat_refresh, tmc)`` triple from ``client`` to disk.

    The sole way the CLI persists token state, used after every command (the :func:`with_client`
    ``finally`` hook) and after explicit sign-in / refresh flows. Centralising the dict shape here
    keeps the on-disk schema in one place.

    Parameters
    ----------
    client : AsyncFordPassClient
        The client whose current credentials should be persisted.
    """
    save_tokens({'cat': client.cat, 'cat_refresh': client.cat_refresh, 'tmc': client.tmc})


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()
    challenge = (base64.urlsafe_b64encode(hashlib.sha256(
        verifier.encode()).digest()).rstrip(b'=').decode())
    # Self-check: SHA-256(verifier) must round-trip to the challenge we hand B2C.
    re_hash = (base64.urlsafe_b64encode(hashlib.sha256(
        verifier.encode()).digest()).rstrip(b'=').decode())
    if re_hash != challenge:  # pragma: no cover - logic check
        msg = 'PKCE self-check failed: hash(verifier) does not match challenge.'
        raise RuntimeError(msg)
    return verifier, challenge


def _decode_b2c_code_kid(code: str) -> str | None:
    try:
        header_b64 = code.split('.', 1)[0]
        header_b64 += '=' * (-len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64.encode()).decode())
    except (ValueError, json.JSONDecodeError):
        return None
    kid = header.get('kid')
    return kid if isinstance(kid, str) else None


async def interactive_signin(client: AsyncFordPassClient) -> None:
    """
    Drive the PKCE WebView sign-in flow end-to-end.

    Prints the ``code_challenge``, a ``code_verifier`` prefix, and the JWE ``kid`` of the returned
    code so users can detect a stale browser session. On success persists the CAT, CAT refresh, and
    TMC tokens via :func:`save_tokens`.

    Parameters
    ----------
    client : AsyncFordPassClient
        The client whose tokens are populated on success.

    Raises
    ------
    click.ClickException
        If the pasted redirect URL is missing ``code=`` or the B2C exchange returns no
        ``access_token``.
    """
    verifier, challenge = _pkce_pair()
    url = client.b2c_authorize_url(code_challenge=challenge)
    click.echo()
    click.secho('Opening your browser to sign in to FordPass...', fg='cyan')
    click.echo()
    click.secho(
        'Tip: use a PRIVATE / INCOGNITO window so a previous B2C session cookie '
        'does not silently SSO you back to a stale `code_challenge`.',
        fg='yellow')
    click.echo()
    click.echo(f'PKCE code_challenge (S256): {challenge}')
    click.echo(f'PKCE code_verifier prefix:  {verifier[:8]}...{verifier[-8:]}')
    click.echo()
    click.echo('If the browser does not open, copy this URL:')
    click.echo(f'  {url}')
    click.echo()
    click.echo('After signing in your browser will try to load a URL starting with\n'
               '`fordapp://userauthorized?code=...`. The browser will say the page\n'
               "can't be reached - that's expected; the URL bar still has the code.\n")
    redirect = click.prompt('Paste the FULL fordapp:// URL from your address bar', type=str).strip()
    parsed = urllib.parse.urlparse(redirect)
    code = urllib.parse.parse_qs(parsed.query).get('code', [None])[0]
    if not code:
        msg = ('No `code=` found in pasted URL. Make sure you pasted the entire '
               'redirect URL including the query string.')
        raise click.ClickException(msg)

    kid = _decode_b2c_code_kid(code)
    if kid is not None:
        click.echo(f'Received code session kid:  {kid}')
    click.echo('Exchanging authorization code...')
    b2c = await client.exchange_b2c_code(code=code, code_verifier=verifier)
    b2c_token = b2c.get('access_token')
    if not b2c_token:
        msg_0 = f'B2C exchange returned no access_token: {b2c!r}.'
        raise click.ClickException(msg_0)

    click.echo('Minting Ford CAT...')
    await client.mint_cat_from_b2c(b2c_access_token=b2c_token)
    click.echo('Exchanging CAT for TMC bearer...')
    await client.exchange_cat_for_tmc()

    persist_tokens(client)
    click.secho('Signed in.', fg='green')


async def ensure_signed_in(client: AsyncFordPassClient, ctx: click.Context) -> None:
    """
    Ensure the client has a CAT; prompt the user to sign in if not.

    Parameters
    ----------
    client : AsyncFordPassClient
        The client to check and (optionally) populate.
    ctx : click.Context
        The current Click context (used to exit cleanly on user decline).
    """
    if client.cat:
        return
    click.echo('No saved token found.')
    if not click.confirm('Sign in now?', default=True):
        ctx.exit(1)
    await interactive_signin(client)


def make_client() -> AsyncFordPassClient:
    """
    Construct an :class:`AsyncFordPassClient` pre-populated from disk.

    Returns
    -------
    AsyncFordPassClient
        The client; tokens may be ``None`` if no bundle exists.
    """
    tokens = load_tokens()
    return AsyncFordPassClient(cat=tokens.get('cat'),
                               cat_refresh=tokens.get('cat_refresh'),
                               tmc=tokens.get('tmc'))


def dump_json(obj: object) -> None:
    """
    Pretty-print a JSON-serialisable object to stdout.

    Parameters
    ----------
    obj : Any
        Any object accepted by :func:`json.dumps`.
    """
    click.echo(json.dumps(obj, default=str, indent=2, sort_keys=True))


def _toml_ordered(data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return ``data`` with scalar keys ordered before nested tables, recursively.

    TOML requires bare key/value pairs to precede ``[table]`` headers at a given level; emitting a
    plain dictionary whose tables come first would otherwise produce a document that re-parses
    incorrectly.

    Parameters
    ----------
    data : Mapping[str, Any]
        The mapping to reorder.

    Returns
    -------
    dict[str, Any]
        A new dictionary with scalars first and nested mappings last.
    """
    scalars = {k: v for k, v in data.items() if not isinstance(v, Mapping)}
    tables = {k: _toml_ordered(v) for k, v in data.items() if isinstance(v, Mapping)}
    return {**scalars, **tables}


def render_config(data: Mapping[str, Any], *, as_json: bool) -> None:
    """
    Print a configuration mapping as TOML or, when requested, JSON.

    Parameters
    ----------
    data : Mapping[str, Any]
        The configuration to render.
    as_json : bool
        Emit JSON instead of TOML.
    """
    if should_emit_json(as_json):
        dump_json(data)
    else:
        click.echo(tomlkit.dumps(_toml_ordered(data)).rstrip('\n'))


def set_toml_key(path: Path, dotted_key: str, value: str) -> None:
    """
    Set ``dotted_key`` to ``value`` in the TOML file at ``path``, creating it if needed.

    The key is a dot-separated path through nested tables (for example ``hosts.login``); missing
    intermediate tables are created. The value is stored as a string.

    Parameters
    ----------
    path : Path
        The TOML file to edit.
    dotted_key : str
        Dot-separated key path.
    value : str
        The value to store.
    """
    data = tomlkit.loads(path.read_text(encoding='utf-8')).unwrap() if path.exists() else {}
    *parents, leaf = dotted_key.split('.')
    cursor = data
    for part in parents:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[leaf] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(_toml_ordered(data)), encoding='utf-8')


def delete_toml_key(path: Path, dotted_key: str) -> None:
    """
    Delete ``dotted_key`` from the TOML file at ``path``.

    Parameters
    ----------
    path : Path
        The TOML file to edit.
    dotted_key : str
        Dot-separated key path to remove.

    Raises
    ------
    KeyError
        If the file does not exist or the key is absent.
    """
    if not path.exists():
        raise KeyError(dotted_key)
    data = tomlkit.loads(path.read_text(encoding='utf-8')).unwrap()
    *parents, leaf = dotted_key.split('.')
    cursor = data
    for part in parents:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            raise KeyError(dotted_key)
        cursor = nxt
    if leaf not in cursor:
        raise KeyError(dotted_key)
    del cursor[leaf]
    path.write_text(tomlkit.dumps(_toml_ordered(data)), encoding='utf-8')


def delete_toml_file(path: Path) -> bool:
    """
    Delete the TOML file at ``path`` if it exists.

    Parameters
    ----------
    path : Path
        The file to remove.

    Returns
    -------
    bool
        ``True`` when a file was removed, ``False`` when there was nothing to delete.
    """
    if path.exists():
        path.unlink()
        return True
    return False


def with_client(async_impl: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
    """
    Wrap ``async def(client, ctx, *args, **kwargs)`` into a sync Click callback.

    The wrapped function handles :py:class:`fordpass.client.AsyncFordPassClient` construction,
    interactive sign-in, and dispatch through :py:func:`run_async`.

    Parameters
    ----------
    async_impl : Callable[..., Awaitable[Any]]
        Async implementation accepting ``(client, ctx, *args, **kwargs)``.

    Returns
    -------
    Callable[..., Any]
        A synchronous Click callback ready to be attached as a command.
    """
    async def _runner(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        async with make_client() as client:
            await ensure_signed_in(client, ctx)
            before = (client.cat, client.cat_refresh, client.tmc)
            try:
                return await async_impl(client, ctx, *args, **kwargs)
            finally:
                if (client.cat, client.cat_refresh, client.tmc) != before:
                    persist_tokens(client)

    @functools.wraps(async_impl)
    def sync_callback(*args: Any, **kwargs: Any) -> Any:
        ctx = click.get_current_context()
        return run_async(_runner(ctx, *args, **kwargs))

    return sync_callback


def ack(resp: niquests.Response, name: str) -> None:
    """Print a green "<name> accepted" line for command responses."""
    click.secho(f'{name} accepted (status {resp.status_code}).', fg='green')


_VIN_RE = re.compile(r'^[A-HJ-NPR-Z0-9][FL][A-HJ-NPR-Z0-9]{15}$')
"""
ISO 3779 VIN charset: 17 alphanumerics (no ``I`` / ``O`` / ``Q``), with the constraint that
position 2 must be ``F`` (Ford) or ``L`` (Lincoln).

:meta hide-value:
"""

_VIN_TRANSLITERATE: dict[str, int] = {
    **{
        c: i
        for i, c in enumerate(string.digits)
    }, 'A': 1,
    'B': 2,
    'C': 3,
    'D': 4,
    'E': 5,
    'F': 6,
    'G': 7,
    'H': 8,
    'J': 1,
    'K': 2,
    'L': 3,
    'M': 4,
    'N': 5,
    'P': 7,
    'R': 9,
    'S': 2,
    'T': 3,
    'U': 4,
    'V': 5,
    'W': 6,
    'X': 7,
    'Y': 8,
    'Z': 9
}
"""
ISO 3779 VIN-character-to-digit table for the check-digit algorithm.

:meta hide-value:
"""

_VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)
"""
Position weights for the VIN check-digit algorithm (position 9 is the check itself).

:meta hide-value:
"""

_VIN_CHECK_REMAINDER_X = 10
"""
Position-9 remainder value that maps to the literal ``'X'`` rather than a digit.

:meta hide-value:
"""


def _vin_check_digit(vin: str) -> str:
    total = sum(_VIN_TRANSLITERATE[c] * w for c, w in zip(vin, _VIN_WEIGHTS, strict=True))
    remainder = total % 11
    return 'X' if remainder == _VIN_CHECK_REMAINDER_X else str(remainder)


def validate_vin(_ctx: click.Context, _param: click.Parameter, value: str | None) -> str | None:
    """
    Validate a VIN against the ISO 3779 structure and check-digit algorithm.

    Designed as a Click parameter callback; ``None`` passes through so that the no-value-yet case
    can be handled by an outer default-resolver.

    Parameters
    ----------
    _ctx : click.Context
        Unused.
    _param : click.Parameter
        Unused.
    value : str | None
        Raw input value, or ``None`` to defer to a default-resolver such as
        :py:func:`_resolve_vin`.

    Returns
    -------
    str | None
        The upper-cased VIN, or ``None`` when ``value`` is ``None``.

    Raises
    ------
    click.BadParameter
        If the VIN is not 17 chars, contains illegal characters, or fails the ISO 3779 check-digit
        verification (rare manufacturer exemptions excepted).
    """
    if value is None:
        return None
    vin = value.strip().upper()
    if not _VIN_RE.match(vin):
        msg = (f'{value!r} is not a valid Ford/Lincoln VIN - expected 17 alphanumeric characters '
               f'with no I, O, or Q, and position 2 must be F (Ford) or L (Lincoln).')
        raise click.BadParameter(msg)
    expected = _vin_check_digit(vin)
    if vin[8] != expected:
        msg = (f'{vin} failed the VIN check-digit verification (position 9 is {vin[8]!r}, '
               f'expected {expected!r}). Double-check the VIN was copied correctly.')
        raise click.BadParameter(msg)
    return vin


def _resolve_vin(ctx: click.Context, param: click.Parameter, value: str | None) -> str:
    """
    Resolve a ``VIN`` argument: CLI value first, then ``[vehicle] default_vin``.

    Both the CLI value and the configured default are run through :py:func:`validate_vin`, which
    enforces the ISO 3779 structure (17 alphanumerics minus ``I`` / ``O`` / ``Q``) plus the
    check-digit verification - so we never send a request we know the gateway will reject.

    Parameters
    ----------
    ctx : click.Context
        The current Click context.
    param : click.Parameter
        The parameter descriptor.
    value : str | None
        The CLI-provided VIN, or ``None`` if omitted.

    Returns
    -------
    str
        The resolved, validated VIN.

    Raises
    ------
    click.UsageError
        If no CLI value was passed and no ``default_vin`` is configured.
    """
    if value:
        return validate_vin(ctx, param, value) or ''
    cfg_vin = (load_config().get('vehicle') or {}).get('default_vin')
    if cfg_vin:
        return validate_vin(ctx, param, cfg_vin) or ''
    msg = ('VIN is required: pass it as a command argument or set '
           f'`[vehicle] default_vin` in {CONFIG_FILE}.')
    raise click.UsageError(msg)


vin_argument = click.argument('vin', required=False, callback=_resolve_vin)
"""
Reusable ``VIN`` positional-argument decorator that falls back to ``[vehicle] default_vin``.

:meta hide-value:
"""

vin_option = click.option(
    '-V',
    '--vin',
    default=None,
    callback=_resolve_vin,
    help='Target VIN. Falls back to `[vehicle] default_vin` from `config.toml`.')
"""
Reusable ``VIN`` option decorator for commands whose positional slot is taken by another value.

:meta hide-value:
"""

json_option = click.option('--json',
                           'as_json',
                           is_flag=True,
                           default=False,
                           help='Emit machine-readable JSON instead of a pretty table.')
"""
Reusable ``--json`` flag decorator paired with :py:func:`should_emit_json`.

:meta hide-value:
"""


def should_emit_json(as_json: bool) -> bool:  # noqa: FBT001
    """
    Decide whether a multi-value command should emit JSON.

    Wraps :py:func:`fordpass.config.resolve_output_format` so callers can write a single boolean
    check at the top of the callback.

    Parameters
    ----------
    as_json : bool
        Value of the caller's ``--json`` flag (from :data:`json_option`).

    Returns
    -------
    bool
        ``True`` when the effective format is JSON.
    """
    return resolve_output_format(cli_json=as_json) == 'json'


def duration_range(min_seconds: int, max_seconds: int) -> click.IntRange:
    """
    Return a :py:class:`click.IntRange` clamped to ``[min_seconds, max_seconds]``.

    Parameters
    ----------
    min_seconds : int
        Inclusive lower bound.
    max_seconds : int
        Inclusive upper bound.

    Returns
    -------
    click.IntRange
        The bounded integer type, suitable for use as ``type=...`` on a Click option.
    """
    return click.IntRange(min=min_seconds, max=max_seconds, clamp=False)


UOM_CHOICE = click.Choice(['mi', 'km'], case_sensitive=False)
"""
Case-insensitive ``mi`` / ``km`` choice for service-planner odometer-units options.

:meta hide-value:
"""


async def validate_message_ids_exist(client: Any, message_ids: Iterable[int]) -> None:
    """
    Pre-flight inbox lookup that aborts before a delete/mark-read request fires.

    Saves the user an opaque 4xx from the message-center backend when they pass stale or wrong IDs.
    Trade: one extra ``GET /api/messagecenter/v3/messages``.

    Parameters
    ----------
    client : Any
        Signed-in :py:class:`fordpass.client.AsyncFordPassClient`.
    message_ids : Iterable[int]
        IDs to look up. Validated as a set; raises with all missing IDs at once.

    Raises
    ------
    click.ClickException
        If any of ``message_ids`` is not present in the inbox at lookup time.
    """
    wanted = {str(m) for m in message_ids}
    resp = await client.get_messages()
    result = resp.get('result') if isinstance(resp, Mapping) else None
    items = (result.get('messages') if isinstance(result, Mapping) else None) or []
    seen: set[str] = set()
    for m in items:
        if not isinstance(m, Mapping):
            continue
        for key in ('messageId', 'id'):
            v = m.get(key)
            if v is not None:
                seen.add(str(v))
    missing = sorted(wanted - seen, key=lambda x: int(x) if x.isdigit() else 0)
    if missing:
        joined = ', '.join(missing)
        msg = (f'Message {joined} not in inbox.'
               if len(missing) == 1 else f'Messages not in inbox: {joined}.')
        raise click.ClickException(msg)


def parse_user_datetime(value: str) -> datetime:
    """
    Parse an ISO 8601 datetime or a few common locale shorthands into a tz-aware datetime.

    Accepted inputs:

    - ``2026-05-30T07:00:00-04:00`` (full ISO 8601)
    - ``2026-05-30T07:00:00Z`` (UTC)
    - ``2026-05-30 07:00`` (date + time, naive - assumed system local)
    - ``2026-05-30`` (date only, midnight in system local)

    Parameters
    ----------
    value : str
        Raw user input.

    Returns
    -------
    datetime
        Timezone-aware datetime (system local when the input was naive).

    Raises
    ------
    click.BadParameter
        If the input matches none of the accepted forms.
    """
    raw = value.strip().replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as e:
        msg = (f'{value!r} is not a recognised datetime. Use ISO 8601, e.g. '
               f'2026-05-30T07:00:00-04:00 or 2026-05-30T07:00:00Z.')
        raise click.BadParameter(msg) from e
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt


def format_iso_datetime(iso: object) -> str:
    """
    Convert an ISO-8601 string to a system-local human-readable rendering.

    Parameters
    ----------
    iso : Any
        Anything sourced from an API response. Non-string / unparseable inputs return ``'-'`` so
        call sites don't need their own guard.

    Returns
    -------
    str
        ``'YYYY-MM-DD HH:MM'`` in the user's system timezone, or ``'-'`` on failure.
    """
    if not isinstance(iso, str) or not iso:
        return '-'
    raw = iso.strip().replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return iso
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime('%Y-%m-%d %H:%M')


_DATE_TIME_TOKEN_COUNT = 2
"""
Number of space-separated tokens expected from :py:func:`format_iso_datetime` (date + time).

:meta hide-value:
"""


def format_iso_date(iso: object) -> str:
    """
    Convert an ISO-8601 string to a system-local ``YYYY-MM-DD`` rendering.

    Parameters
    ----------
    iso : object
        Anything sourced from an API response.

    Returns
    -------
    str
        The ``YYYY-MM-DD`` date in the user's system timezone, or ``'-'`` on failure.
    """
    text = format_iso_datetime(iso)
    return text.split(' ', 1)[0] if text != '-' else '-'


def format_iso_time(iso: object) -> str:
    """
    Convert an ISO-8601 string to a system-local ``HH:MM`` rendering.

    Parameters
    ----------
    iso : object
        Anything sourced from an API response.

    Returns
    -------
    str
        The ``HH:MM`` time in the user's system timezone, or ``'-'`` on failure.
    """
    text = format_iso_datetime(iso)
    parts = text.split(' ', 1)
    return parts[1] if len(parts) == _DATE_TIME_TOKEN_COUNT else '-'


_DAY_NAMES: dict[str, str] = {
    'su': 'sun',
    'sun': 'sun',
    'sunday': 'sun',
    'u': 'sun',
    'm': 'mon',
    'mo': 'mon',
    'mon': 'mon',
    'monday': 'mon',
    't': 'tue',
    'tu': 'tue',
    'tue': 'tue',
    'tues': 'tue',
    'tuesday': 'tue',
    'w': 'wed',
    'we': 'wed',
    'wed': 'wed',
    'wednesday': 'wed',
    'th': 'thu',
    'thu': 'thu',
    'thur': 'thu',
    'thurs': 'thu',
    'thursday': 'thu',
    'f': 'fri',
    'fr': 'fri',
    'fri': 'fri',
    'friday': 'fri',
    'sa': 'sat',
    'sat': 'sat',
    'saturday': 'sat'
}
"""
Tolerant English-day-name aliases recognised by :py:func:`parse_user_days`.

:meta hide-value:
"""

_DAY_FIELDS: tuple[str, ...] = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
"""
Canonical day keys in Ford's wire-format order, sun to sat.

:meta hide-value:
"""


def parse_user_days(value: str) -> dict[str, int]:
    """
    Convert a flexible day-list string into Ford's ``{sun: 0|1, ..., sat: 0|1}`` mapping.

    Accepts any subset of full names, common abbreviations, and one-letter shortcuts;
    case-insensitive; tolerant of commas, spaces, slashes and ``+`` as separators. Examples
    accepted: ``'mon,tue,thu'``, ``'M T Th'``, ``'monday/wednesday/friday'``, ``'mwf'``.

    Parameters
    ----------
    value : str
        Raw user input.

    Returns
    -------
    dict[str, int]
        All seven keys present, each ``1`` if enabled and ``0`` otherwise.

    Raises
    ------
    click.BadParameter
        If a token doesn't match any known day name or letter.
    """
    enabled: dict[str, int] = dict.fromkeys(_DAY_FIELDS, 0)
    if not value or not value.strip():
        return enabled
    raw = re.sub(r'[,\s/+]+', ',', value.strip().lower()).strip(',')
    tokens: list[str] = []
    for chunk in raw.split(','):
        if not chunk:  # pragma: no cover
            continue
        if chunk in _DAY_NAMES:
            tokens.append(chunk)
        elif all(c in _DAY_NAMES for c in chunk):
            tokens.extend(chunk)
        else:
            tokens.append(chunk)
    for token in tokens:
        canonical = _DAY_NAMES.get(token)
        if canonical is None:
            msg = (f'{token!r} is not a recognised day. Use English day names, abbreviations, or '
                   f'one-letter shortcuts (e.g. monday, mon, m).')
            raise click.BadParameter(msg)
        enabled[canonical] = 1
    return enabled


def _parse_offset_tz(value: str) -> ZoneInfo | None:
    match = re.fullmatch(r'([+-])(\d{2}):?(\d{2})', value.strip())
    if not match:
        return None
    sign, hh, mm = match.group(1), int(match.group(2)), int(match.group(3))
    if mm != 0:
        return None
    posix_sign = '-' if sign == '+' else '+'
    try:
        return ZoneInfo(f'Etc/GMT{posix_sign}{hh}')
    except ZoneInfoNotFoundError:
        return None


def parse_user_timezone(value: str | None) -> int:
    """
    Resolve a user-supplied timezone string to a Ford internal zone-code integer.

    Accepted inputs (priority order):

    1. Bare integer (e.g. ``'85'``) - passed straight through.
    2. IANA name (e.g. ``'America/New_York'``) - looked up in
       :py:data:`fordpass.timezone_map.FORD_ZONE_BY_IANA`.
    3. ``'local'`` / ``None`` - uses the system's IANA timezone (typically from :envvar:`TZ` or
       ``/etc/localtime``), looked up the same way.

    UTC offsets like ``'+05:00'`` are rejected because Ford zone codes distinguish DST-observing
    from DST-fixed zones at the same offset, so the mapping is not 1-to-1.

    Parameters
    ----------
    value : str | None
        Raw user input; ``None`` means "use the system local timezone".

    Returns
    -------
    int
        Ford internal zone code suitable for placing into the schedule body.

    Raises
    ------
    click.BadParameter
        If no Ford code is known for the resolved IANA name.
    """
    if value is None or value.strip().lower() in {'', 'local', 'system'}:
        local_tz = datetime.now().astimezone().tzinfo
        iana = getattr(local_tz, 'key', None)
        if iana is None:
            msg = ('Could not resolve the system timezone to an IANA name. '
                   'Pass --tz <Ford zone code as integer> or --tz <IANA name>.')
            raise click.BadParameter(msg)
        return _ford_code_for_iana(iana)
    raw = value.strip()
    if raw.isdigit() or (raw.startswith('-') and raw[1:].isdigit()):
        return int(raw)
    if _parse_offset_tz(raw) is not None:
        msg = (f"A bare UTC offset ({raw!r}) doesn't uniquely identify a Ford zone code "
               f'(DST-observing and DST-fixed zones share offsets). Pass an IANA name like '
               f'"America/New_York" or an integer Ford code.')
        raise click.BadParameter(msg)
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError as e:
        msg = (f'{value!r} is not a recognised IANA timezone name. Examples: "America/New_York", '
               f'"Europe/London". Or pass an integer Ford zone code.')
        raise click.BadParameter(msg) from e
    return _ford_code_for_iana(raw)


def _ford_code_for_iana(iana: str) -> int:
    code = FORD_ZONE_BY_IANA.get(iana)
    if code is not None:
        return code
    msg = f'No Ford zone code is mapped for IANA timezone {iana!r}.'
    raise click.BadParameter(msg)


def format_ford_request_date(dt: datetime) -> str:
    """
    Render a tz-aware datetime in Ford's ``M-D-YYYY h:mm:ss AM/PM`` schedule format.

    No leading zeros on month, day, or hour - that's the format Ford's SRSM endpoint expects
    (example: ``'5-28-2026 1:50:00 PM'``).

    Parameters
    ----------
    dt : datetime
        Timezone-aware datetime. The local component (hour / minute / second / month / day / year
        in the input timezone) is what gets serialised; the offset is dropped.

    Returns
    -------
    str
        Ford-formatted schedule timestamp.
    """
    hours_per_half_day = 12
    hour_12 = dt.hour % hours_per_half_day or hours_per_half_day
    suffix = 'AM' if dt.hour < hours_per_half_day else 'PM'
    return f'{dt.month}-{dt.day}-{dt.year} {hour_12}:{dt.minute:02d}:{dt.second:02d} {suffix}'


_PRECLUSION_CAUSES: tuple[tuple[str, str, str],
                          ...] = (('deepSleepCommandPreclusionState',
                                   'COMMANDS_PRECLUDED_BY_DEEP_SLEEP',
                                   'Battery Saver mode (deep sleep)'),
                                  ('firmwareUpgradeCommandPreclusionState',
                                   'COMMANDS_PRECLUDED_BY_FIRMWARE_UPDATE',
                                   'Firmware update in progress'),
                                  ('regulatoryCommandPreclusionState',
                                   'COMMANDS_PRECLUDED_BY_REGULATORY_COMMAND', 'Regulatory block'),
                                  ('temperatureThresholdCommandPreclusionState',
                                   'COMMANDS_PRECLUDED_BY_TEMPERATURE_THRESHOLD',
                                   'Temperature threshold exceeded'),
                                  ('carrierRegistrationCommandPreclusionState',
                                   'COMMANDS_PRECLUDED_BY_CARRIER_REGISTRATION',
                                   'Carrier registration pending'))
"""
The five ``commandPreclusionCauses`` enums the FordPass app inspects, paired with the sentinel
value that marks them active and a short user-facing label.

The mobile app walks
:code:`states.commandPreclusion.value.data.commandPreclusionCauses.<field>` and compares against
the matching :code:`COMMANDS_PRECLUDED_BY_*` sentinel.

:meta hide-value:
"""


class Readiness(NamedTuple):
    """Pre-flight readiness verdict for remote commands."""

    battery_conditions: tuple[str, ...]
    """Active ``events.batteryEvent.conditions`` keys (e.g. ``('lowBatteryCharge',)``)."""
    life_cycle_mode: str | None
    """Vehicle life-cycle-mode enum, or ``None`` if not reported."""
    load_status: str | None
    """Battery-load-status enum, or ``None`` if not reported."""
    ok: bool
    """``True`` if remote commands should be expected to succeed."""
    raw: dict[str, Any]
    """Inspected raw telemetry fragments - useful for diagnosing why the gate did or didn't trip."""
    reasons: tuple[str, ...]
    """Human-readable blockers; empty when :py:attr:`ok` is ``True``."""
    state_of_charge: float | None
    """12V battery state-of-charge percent, or ``None`` if not reported."""
    voltage: float | None
    """12V battery voltage in volts, or ``None`` if not reported."""


async def check_readiness(client: AsyncFordPassClient, vin: str) -> Readiness:
    """
    Query telemetry and compute the remote-command readiness verdict for ``vin``.

    Parameters
    ----------
    client : AsyncFordPassClient
        Signed-in client.
    vin : str
        Target VIN.

    Returns
    -------
    Readiness
        The verdict; :py:attr:`Readiness.ok` is ``True`` when none of the known blockers are
        tripped.
    """
    # Unfiltered call: passing some metric names to ``includeMetrics`` makes the gateway 502 (same
    # root cause as the earlier ota-status issue), and the filter would only save a few KB anyway.
    resp = await client.query_telemetry(vin)
    metrics_block = (resp.get('metrics') if isinstance(resp, Mapping) else None) or {}
    states_block = (resp.get('states') if isinstance(resp, Mapping) else None) or {}
    events_block = (resp.get('events') if isinstance(resp, Mapping) else None) or {}
    voltage = scalar_metric_value(metrics_block.get('batteryVoltage'))
    soc = scalar_metric_value(metrics_block.get('batteryStateOfCharge'))
    load_status = scalar_metric_value(metrics_block.get('batteryLoadStatus'))
    life_cycle = (scalar_metric_value(states_block.get('vehicleLifeCycleMode'))
                  or scalar_metric_value(metrics_block.get('vehicleLifeCycleMode')))
    # Canonical signal - mirror of the FordPass app's deep-sleep / preclusion-cause check. The app
    # walks the same path; we use the same sentinel comparison.
    preclusion_causes = walk_mapping(states_block, 'commandPreclusion', 'value', 'data',
                                     'commandPreclusionCauses')
    reasons: list[str] = []
    if isinstance(preclusion_causes, Mapping):
        for field, sentinel, label in _PRECLUSION_CAUSES:
            if preclusion_causes.get(field) == sentinel:
                reasons.append(f'{label} ({field} == {sentinel}).')
    # Battery-event conditions are kept around for diagnostics - they correlate with deep sleep
    # but are not the authoritative gate signal.
    battery_event = events_block.get('batteryEvent') if isinstance(events_block, Mapping) else None
    conditions = (battery_event.get('conditions') if isinstance(battery_event, Mapping) else None)
    # Compact diagnostic payload - only the fields actually load-bearing for the gate.
    interesting: dict[str, Any] = {}
    if isinstance(preclusion_causes, Mapping):
        interesting['states.commandPreclusion'] = preclusion_causes
    if isinstance(conditions, Mapping):
        interesting['events.batteryEvent.conditions'] = list(conditions)
    battery_conditions = (tuple(sorted(conditions)) if isinstance(conditions, Mapping) else ())
    return Readiness(battery_conditions=battery_conditions,
                     life_cycle_mode=str(life_cycle) if isinstance(life_cycle, str) else None,
                     load_status=str(load_status) if isinstance(load_status, str) else None,
                     ok=not reasons,
                     raw=interesting,
                     reasons=tuple(reasons),
                     state_of_charge=float(soc) if isinstance(soc, (int, float)) else None,
                     voltage=float(voltage) if isinstance(voltage, (int, float)) else None)


async def assert_ready_or_abort(client: AsyncFordPassClient, vin: str, *, force: bool) -> None:
    """
    Run the readiness check; abort the command if ``vin`` is not ready.

    Parameters
    ----------
    client : AsyncFordPassClient
        Signed-in client.
    vin : str
        Target VIN.
    force : bool
        When ``True``, skip the check entirely.

    Raises
    ------
    click.Abort
        If the vehicle is in Battery Saver mode or otherwise not ready, and ``force`` is ``False``.
    """
    if force:
        return
    readiness = await check_readiness(client, vin)
    if readiness.ok:
        return
    for reason in readiness.reasons:
        console.print(f'[red]Remote command blocked:[/red] {reason}')
    console.print('[dim]Pass --force to send the command anyway, or start the vehicle to clear '
                  'Battery Saver mode.[/dim]')
    raise click.Abort


def force_option(func: FC) -> FC:
    """
    Attach a ``--force/-f`` flag for bypassing the readiness gate.

    Parameters
    ----------
    func : FC
        Click callback (or :py:class:`click.Command`) to decorate.

    Returns
    -------
    FC
        The decorated callback with ``--force/-f`` added; same concrete type as ``func``.
    """
    return click.option(
        '-f',
        '--force',
        is_flag=True,
        default=False,
        help='Send the command even if the vehicle reports Battery Saver mode.')(func)
