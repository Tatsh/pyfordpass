"""Auth: sign in / out, inspect tokens."""
from __future__ import annotations

import click

from .utils import (
    TOKEN_FILE,
    debug_option,
    dump_json,
    ensure_signed_in,
    interactive_signin,
    json_option,
    load_tokens,
    make_client,
    persist_tokens,
    run_async,
    should_emit_json,
)


@click.group()
def auth() -> None:
    """Sign in / out, inspect tokens."""


@auth.command('login')
@debug_option
def auth_login() -> None:
    """Interactive PKCE sign-in via the Ford B2C login page."""
    async def _impl() -> None:
        async with make_client() as client:
            await interactive_signin(client)

    run_async(_impl())


@auth.command('refresh')
@debug_option
def auth_refresh() -> None:
    """Refresh the short-lived TMC bearer."""
    async def _impl() -> None:
        async with make_client() as client:
            ctx = click.get_current_context()
            await ensure_signed_in(client, ctx)
            await client.exchange_cat_for_tmc()
            persist_tokens(client)
            click.secho('TMC bearer refreshed.', fg='green')

    run_async(_impl())


@auth.command('status')
@debug_option
@json_option
def auth_status(*, as_json: bool) -> None:
    """Show saved tokens (truncated)."""
    tokens = load_tokens()
    cat = tokens.get('cat') or ''
    tmc = tokens.get('tmc') or ''
    if should_emit_json(as_json):
        dump_json({
            'signed_in': bool(tokens),
            'tokens_path': str(TOKEN_FILE),
            'cat_length': len(cat),
            'tmc_length': len(tmc)
        })
        return
    if not tokens:
        click.echo('Not signed in.')
        return
    click.echo(f'Tokens at: {TOKEN_FILE}')
    click.echo(f'  CAT: {cat[:48] or "<missing>"}...({len(cat)} chars)')
    click.echo(f'  TMC: {tmc[:48] or "<missing>"}...({len(tmc)} chars)')


@auth.command('logout')
@debug_option
def auth_logout() -> None:
    """Delete saved tokens."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        click.secho('Logged out.', fg='yellow')
    else:
        click.echo('Already logged out.')
