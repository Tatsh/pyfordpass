"""Command-layer helpers: async/sync bridge, token storage, PKCE, sign-in."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
import asyncio
import base64
import functools
import hashlib
import json
import secrets
import urllib.parse
import webbrowser  # noqa: F401  # kept for future automated browser launch

from fordpass.client import FordPassNiquestsClient
from fordpass.config import CONFIG_FILE, load_config, resolve_output_format
from platformdirs import user_state_dir
from rich.console import Console
import click

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    import niquests

__all__ = ('STATE_DIR', 'TOKEN_FILE', 'console', 'dump_json', 'ensure_signed_in', 'install_loop',
           'interactive_signin', 'json_option', 'load_tokens', 'make_client', 'persist_tokens',
           'run_async', 'save_tokens', 'should_emit_json', 'vin_argument', 'with_client')

console = Console()
"""Shared Rich :py:class:`~rich.console.Console` used by command-side pretty printouts.

:meta hide-value:
"""

# ---- async/sync bridge -----------------------------------------------------

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


# ---- token persistence -----------------------------------------------------

STATE_DIR = Path(user_state_dir(appname='fordpass', appauthor=False))
"""
Directory used for token storage, located via :mod:`platformdirs`.

Resolves to ``~/.local/state/fordpass`` on Linux (XDG state-home), matching
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


def persist_tokens(client: FordPassNiquestsClient) -> None:
    """
    Snapshot the current ``(cat, cat_refresh, tmc)`` triple from ``client`` to disk.

    The sole way the CLI persists token state, used after every command (the
    :func:`with_client` ``finally`` hook) and after explicit sign-in / refresh
    flows. Centralising the dict shape here keeps the on-disk schema in one place.

    Parameters
    ----------
    client : FordPassNiquestsClient
        The client whose current credentials should be persisted.
    """
    save_tokens({'cat': client.cat, 'cat_refresh': client.cat_refresh, 'tmc': client.tmc})


# ---- PKCE + interactive sign-in -------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    """
    Generate a fresh ``(code_verifier, code_challenge)`` pair per RFC 7636 / S256.

    Returns
    -------
    tuple[str, str]
        The PKCE verifier and matching SHA-256 challenge, both base64url-encoded.

    Raises
    ------
    RuntimeError
        If the internal SHA-256 self-check fails (should never happen in practice).
    """
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
    """
    Decode the JWE header ``kid`` from a B2C authorisation code.

    Parameters
    ----------
    code : str
        The full authorisation code returned in the ``fordapp://userauthorized?code=...``
        redirect.

    Returns
    -------
    str | None
        The ``kid`` claim from the JWE protected header, or ``None`` if the code
        is malformed or cannot be parsed.
    """
    try:
        header_b64 = code.split('.', 1)[0]
        header_b64 += '=' * (-len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64.encode()).decode())
    except (ValueError, json.JSONDecodeError):
        return None
    kid = header.get('kid')
    return kid if isinstance(kid, str) else None


async def interactive_signin(client: FordPassNiquestsClient) -> None:
    """
    Drive the PKCE WebView sign-in flow end-to-end.

    Prints the ``code_challenge``, a ``code_verifier`` prefix, and the JWE
    ``kid`` of the returned code so users can detect a stale browser session.
    On success persists the CAT, CAT refresh, and TMC tokens via
    :func:`save_tokens`.

    Parameters
    ----------
    client : FordPassNiquestsClient
        The client whose tokens will be populated on success.

    Raises
    ------
    click.ClickException
        If the pasted redirect URL is missing ``code=`` or the B2C exchange
        returns no ``access_token``.
    """
    verifier, challenge = _pkce_pair()
    url = client.b2c_authorize_url(code_challenge=challenge)
    click.echo()
    click.secho('Opening your browser to sign in to FordPass...', fg='cyan')
    click.echo()
    click.secho(
        'Tip: use a PRIVATE / INCOGNITO window so a previous B2C session cookie '
        'does not silently SSO you back to a stale `code_challenge`.',
        fg='yellow',
    )
    click.echo()
    click.echo(f'PKCE code_challenge (S256): {challenge}')
    click.echo(f'PKCE code_verifier prefix:  {verifier[:8]}...{verifier[-8:]}')
    click.echo()
    click.echo('If the browser does not open, copy this URL:')
    click.echo(f'  {url}')
    click.echo()
    click.echo('After signing in your browser will try to load a URL starting with\n'
               '`fordapp://userauthorized?code=...`. The browser will say the page\n'
               "can't be reached — that's expected; the URL bar still has the code.\n")
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


async def ensure_signed_in(client: FordPassNiquestsClient, ctx: click.Context) -> None:
    """
    Ensure the client has a CAT; prompt the user to sign in if not.

    Parameters
    ----------
    client : FordPassNiquestsClient
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


def make_client() -> FordPassNiquestsClient:
    """
    Construct a :class:`FordPassNiquestsClient` pre-populated from disk.

    Returns
    -------
    FordPassNiquestsClient
        The client; tokens may be ``None`` if no bundle exists.
    """
    tokens = load_tokens()
    return FordPassNiquestsClient(cat=tokens.get('cat'),
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


# ---- command decorator -----------------------------------------------------


def with_client(async_impl: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
    """
    Wrap ``async def(client, ctx, *args, **kwargs)`` into a sync Click callback.

    The wrapped function handles :py:class:`fordpass.client.FordPassNiquestsClient`
    construction, interactive sign-in, and dispatch through :py:func:`run_async`.

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


def _resolve_vin(_ctx: click.Context, _param: click.Parameter, value: str | None) -> str:
    """
    Resolve a ``VIN`` argument: CLI value first, then ``[vehicle] default_vin``.

    Parameters
    ----------
    _ctx : click.Context
        The current Click context (unused).
    _param : click.Parameter
        The parameter descriptor (unused).
    value : str | None
        The CLI-provided VIN, or ``None`` if omitted.

    Returns
    -------
    str
        The resolved VIN.

    Raises
    ------
    click.UsageError
        If no CLI value was passed and no ``default_vin`` is configured.
    """
    if value:
        return value
    cfg_vin = (load_config().get('vehicle') or {}).get('default_vin')
    if cfg_vin:
        return cfg_vin
    msg = ('VIN is required: pass it as a command argument or set '
           f'`[vehicle] default_vin` in {CONFIG_FILE}.')
    raise click.UsageError(msg)


vin_argument = click.argument('vin', required=False, callback=_resolve_vin)
"""Reusable ``VIN`` argument decorator that falls back to ``[vehicle] default_vin``.

:meta hide-value:
"""

json_option = click.option('--json',
                           'as_json',
                           is_flag=True,
                           default=False,
                           help='Emit machine-readable JSON instead of a pretty table.')
"""Reusable ``--json`` flag decorator paired with :py:func:`should_emit_json`.

:meta hide-value:
"""


def should_emit_json(as_json: bool) -> bool:  # noqa: FBT001
    """
    Decide whether a multi-value command should emit JSON.

    Wraps :py:func:`fordpass.config.resolve_output_format` so callers can write
    a single boolean check at the top of the callback.

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
