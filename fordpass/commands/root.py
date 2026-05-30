"""Root Click group + subcommand wiring."""
from __future__ import annotations

import asyncio

import click

from .alerts import alerts
from .auth import auth
from .dealer import dealer
from .departure import departure
from .drivers import drivers
from .messages import messages
from .ota import ota
from .profile import profile
from .remote import remote
from .roadside import roadside
from .schedule import schedule
from .service import service
from .telemetry import telemetry
from .utils import install_loop
from .vehicle import vehicle

__all__ = ('ford', 'main')


@click.group(context_settings={'help_option_names': ('-h', '--help')})
@click.version_option(prog_name='ford')
def ford() -> None:
    """FordPass CLI.

    Usage: ``ford <activity> <action> [args]``.
    """


# Sub-groups (alphabetical for stable help output).
ford.add_command(alerts)
ford.add_command(auth)
ford.add_command(dealer)
ford.add_command(departure)
ford.add_command(drivers)
ford.add_command(messages)
ford.add_command(ota)
ford.add_command(profile)
ford.add_command(remote)
ford.add_command(roadside)
ford.add_command(schedule)
ford.add_command(service)
ford.add_command(telemetry)
ford.add_command(vehicle)


async def _amain() -> None:
    """
    Capture the running loop and dispatch Click in an executor.

    Click's sync callbacks dispatch back here via :py:func:`fordpass.commands.utils.run_async`.
    """
    loop = asyncio.get_running_loop()
    install_loop(loop)
    await loop.run_in_executor(None, ford.main)


def main() -> None:
    """Sync entry point — enters async on its first line."""
    asyncio.run(_amain())
