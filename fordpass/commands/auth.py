"""Auth: sign in / out, inspect tokens."""
from __future__ import annotations

import click

from .utils import (
    TOKEN_FILE,
    ensure_signed_in,
    interactive_signin,
    load_tokens,
    make_client,
    persist_tokens,
    run_async,
)


@click.group()
def auth() -> None:
    """Sign in / out, inspect tokens."""


@auth.command('login')
def auth_login() -> None:
    """Interactive PKCE sign-in via the Ford B2C login page."""
    async def _impl() -> None:
        async with make_client() as client:
            await interactive_signin(client)

    run_async(_impl())


@auth.command('refresh')
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
def auth_status() -> None:
    """Show saved tokens (truncated)."""
    tokens = load_tokens()
    if not tokens:
        click.echo('Not signed in.')
        return
    cat = tokens.get('cat') or '<missing>'
    tmc = tokens.get('tmc') or '<missing>'
    click.echo(f'Tokens at: {TOKEN_FILE}')
    click.echo(f'  CAT: {cat[:48]}...({len(cat)} chars)')
    click.echo(f'  TMC: {tmc[:48]}...({len(tmc)} chars)')


@auth.command('logout')
def auth_logout() -> None:
    """Delete saved tokens."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        click.secho('Logged out.', fg='yellow')
    else:
        click.echo('Already logged out.')
