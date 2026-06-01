"""Root Click group + subcommand wiring."""
from __future__ import annotations

import asyncio

import click

from .commands.alerts import alerts
from .commands.api_config import api_config
from .commands.auth import auth
from .commands.charge import charge
from .commands.climate import climate
from .commands.config import config
from .commands.dealer import dealer
from .commands.departure import departure
from .commands.drivers import drivers
from .commands.guard import guard
from .commands.lights import lights
from .commands.messages import messages
from .commands.ota import ota
from .commands.ppo import ppo
from .commands.precondition import precondition
from .commands.profile import profile
from .commands.remote import remote
from .commands.roadside import roadside
from .commands.schedule import schedule
from .commands.service import service
from .commands.telemetry import telemetry
from .commands.trailer import trailer
from .commands.utils import install_loop
from .commands.vehicle import vehicle

__all__ = ('fordpass', 'main')


@click.group(context_settings={'help_option_names': ('-h', '--help')})
@click.version_option()
def fordpass() -> None:
    """FordPass CLI."""


fordpass.add_command(alerts)
fordpass.add_command(api_config)
fordpass.add_command(auth)
fordpass.add_command(charge)
fordpass.add_command(climate)
fordpass.add_command(config)
fordpass.add_command(dealer)
fordpass.add_command(departure)
fordpass.add_command(drivers)
fordpass.add_command(guard)
fordpass.add_command(lights)
fordpass.add_command(messages)
fordpass.add_command(ota)
fordpass.add_command(ppo)
fordpass.add_command(precondition)
fordpass.add_command(profile)
fordpass.add_command(remote)
fordpass.add_command(roadside)
fordpass.add_command(schedule)
fordpass.add_command(service)
fordpass.add_command(telemetry)
fordpass.add_command(trailer)
fordpass.add_command(vehicle)


async def _amain() -> None:
    loop = asyncio.get_running_loop()
    install_loop(loop)
    await loop.run_in_executor(None, fordpass.main)


def main() -> None:
    """Sync entry point - enters async on its first line."""
    asyncio.run(_amain())
