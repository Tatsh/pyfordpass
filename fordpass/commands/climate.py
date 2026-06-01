"""Remote Climate Control commands: show, set (Ford vehicle API)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.config import load_config
from fordpass.utils import decode_rcc_temperature, encode_rcc_temperature
from rich.table import Table
import click

from .utils import (
    console,
    debug_option,
    dump_json,
    json_option,
    should_emit_json,
    vin_argument,
    with_client,
)

if TYPE_CHECKING:
    from fordpass.client import AsyncFordPassClient
    from fordpass.typing.rcc import RCCPreferenceKey, RCCProfile

_TOGGLE_CHOICE = click.Choice(['off', 'on'], case_sensitive=False)
"""Case-insensitive ``off`` / ``on`` choice for the binary climate toggles.

:meta hide-value:
"""

_SEAT_CHOICE = click.Choice(['off', 'low', 'medium', 'high'], case_sensitive=False)
"""Case-insensitive level choice for the four climate seats.

:meta hide-value:
"""

_SET_POINT_TEMP: RCCPreferenceKey = 'SetPointTemp_Rq'
"""The ``preferenceType`` key carrying the target cabin temperature.

:meta hide-value:
"""

_LABELS: dict[str, str] = {
    'RccHeatedWindshield_Rq': 'Heated windshield',
    'RccRearDefrost_Rq': 'Rear defrost',
    'RccHeatedSteeringWheel_Rq': 'Heated steering wheel',
    'RccLeftFrontClimateSeat_Rq': 'Left-front climate seat',
    'RccLeftRearClimateSeat_Rq': 'Left-rear climate seat',
    'RccRightFrontClimateSeat_Rq': 'Right-front climate seat',
    'RccRightRearClimateSeat_Rq': 'Right-rear climate seat',
    'SetPointTemp_Rq': 'Target temperature'
}
"""Friendly labels for each :py:data:`~fordpass.typing.rcc.RCCPreferenceKey` in the pretty table.

:meta hide-value:
"""

_TOGGLE_SETTINGS: tuple[tuple[str, RCCPreferenceKey],
                        ...] = (('heated_windshield',
                                 'RccHeatedWindshield_Rq'), ('rear_defrost', 'RccRearDefrost_Rq'),
                                ('heated_steering_wheel', 'RccHeatedSteeringWheel_Rq'))
"""Maps each binary-toggle option name to its preference key.

:meta hide-value:
"""

_SEAT_SETTINGS: tuple[tuple[str, RCCPreferenceKey],
                      ...] = (('seat_lf', 'RccLeftFrontClimateSeat_Rq'),
                              ('seat_lr', 'RccLeftRearClimateSeat_Rq'),
                              ('seat_rf', 'RccRightFrontClimateSeat_Rq'),
                              ('seat_rr', 'RccRightRearClimateSeat_Rq'))
"""Maps each climate-seat option name to its preference key.

:meta hide-value:
"""


def _format_value(key: str, value: str, pref_temperature: str) -> str:
    """
    Render one preference value for the pretty table.

    The temperature key is decoded from its ``XX_Y`` wire form and shown in the user's preferred
    unit; every other key is shown verbatim.

    Parameters
    ----------
    key : str
        The ``preferenceType`` being rendered.
    value : str
        The raw ``preferenceValue``.
    pref_temperature : str
        ``'F'`` or ``'C'`` from the user's resolved temperature preference.

    Returns
    -------
    str
        The display string.
    """
    if key != _SET_POINT_TEMP:
        return value
    try:
        celsius = decode_rcc_temperature(value)
    except ValueError:
        return value
    if pref_temperature == 'F':
        return f'{celsius * 9.0 / 5.0 + 32.0:.1f}°F'
    return f'{celsius:.1f}°C'


def _render_show(profile: RCCProfile, *, pref_temperature: str, as_json: bool) -> None:
    """
    Print an RCC profile as JSON or a decoded Rich table.

    Parameters
    ----------
    profile : RCCProfile
        The parsed RCC profile.
    pref_temperature : str
        ``'F'`` or ``'C'`` from the user's resolved temperature preference.
    as_json : bool
        Emit machine-readable JSON instead of a table.
    """
    if should_emit_json(as_json):
        dump_json(profile)
        return
    preferences = profile.get('rccUserProfiles') or []
    if not preferences:
        click.secho('No remote climate profile is saved for this vehicle.', fg='yellow')
        return
    table = Table(title='Remote climate control', title_style='bold cyan')
    table.add_column('Setting', style='cyan')
    table.add_column('Value')
    for pref in preferences:
        key = pref.get('preferenceType', '')
        table.add_row(_LABELS.get(key, key),
                      _format_value(key, pref.get('preferenceValue', ''), pref_temperature))
    console.print(table)


@click.group()
def climate() -> None:
    """Remote Climate Control profile (Ford vehicle API)."""


@climate.command('show')
@debug_option
@vin_argument
@json_option
@with_client
async def climate_show(client: AsyncFordPassClient, _ctx: click.Context, vin: str, *,
                       as_json: bool) -> None:
    """Show the saved remote climate profile."""
    pref_temperature = load_config(locale=client.locale)['units']['temperature']
    _render_show(await client.get_remote_climate(vin),
                 pref_temperature=pref_temperature,
                 as_json=as_json)


@climate.command('set')
@debug_option
@vin_argument
@click.option('--temp',
              type=float,
              default=None,
              help='Target cabin temperature in your configured unit.')
@click.option('--heated-windshield',
              type=_TOGGLE_CHOICE,
              default=None,
              help='Heated windshield on or off.')
@click.option('--rear-defrost', type=_TOGGLE_CHOICE, default=None, help='Rear defrost on or off.')
@click.option('--heated-steering-wheel',
              type=_TOGGLE_CHOICE,
              default=None,
              help='Heated steering wheel on or off.')
@click.option('--seat-lf', type=_SEAT_CHOICE, default=None, help='Left-front climate seat level.')
@click.option('--seat-lr', type=_SEAT_CHOICE, default=None, help='Left-rear climate seat level.')
@click.option('--seat-rf', type=_SEAT_CHOICE, default=None, help='Right-front climate seat level.')
@click.option('--seat-rr', type=_SEAT_CHOICE, default=None, help='Right-rear climate seat level.')
@json_option
@with_client
async def climate_set(client: AsyncFordPassClient, ctx: click.Context, vin: str, *,
                      temp: float | None, heated_windshield: str | None, rear_defrost: str | None,
                      heated_steering_wheel: str | None, seat_lf: str | None, seat_lr: str | None,
                      seat_rf: str | None, seat_rr: str | None, as_json: bool) -> None:
    """Update one or more remote climate settings (sparse merge)."""
    options = {
        'heated_windshield': heated_windshield,
        'rear_defrost': rear_defrost,
        'heated_steering_wheel': heated_steering_wheel,
        'seat_lf': seat_lf,
        'seat_lr': seat_lr,
        'seat_rf': seat_rf,
        'seat_rr': seat_rr
    }
    updates: dict[RCCPreferenceKey, str] = {
        key: value.capitalize()
        for name, key in (*_TOGGLE_SETTINGS, *_SEAT_SETTINGS)
        if (value := options[name]) is not None
    }
    if temp is not None:
        pref_temperature = load_config(locale=client.locale)['units']['temperature']
        celsius = (temp - 32.0) * 5.0 / 9.0 if pref_temperature == 'F' else temp
        updates[_SET_POINT_TEMP] = encode_rcc_temperature(celsius)
    if not updates:
        ctx.fail('Specify at least one setting to change.')
    submitted = await client.set_remote_climate(vin, updates=updates)
    if should_emit_json(as_json):
        dump_json({'submitted': submitted, 'updates': dict(updates)})
        return
    if submitted:
        click.secho('Remote climate update submitted. Re-run `climate show` to confirm.',
                    fg='green')
    else:
        click.secho('Remote climate update was not accepted.', fg='red')
