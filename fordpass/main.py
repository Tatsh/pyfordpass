"""Root Click group + subcommand wiring."""
from __future__ import annotations

import asyncio

import click

from .commands.alerts import alerts
from .commands.auth import auth
from .commands.dealer import dealer
from .commands.departure import departure
from .commands.drivers import drivers
from .commands.messages import messages
from .commands.ota import ota
from .commands.profile import profile
from .commands.remote import remote
from .commands.roadside import roadside
from .commands.schedule import schedule
from .commands.service import service
from .commands.telemetry import telemetry
from .commands.utils import install_loop
from .commands.vehicle import vehicle

__all__ = ('ford', 'main')


@click.group(context_settings={'help_option_names': ('-h', '--help')})
@click.version_option()
def ford() -> None:
    """FordPass CLI."""


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
    loop = asyncio.get_running_loop()
    install_loop(loop)
    await loop.run_in_executor(None, ford.main)


def main() -> None:
    """Sync entry point - enters async on its first line."""
    asyncio.run(_amain())
