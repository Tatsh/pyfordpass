"""Tests for fordpass.commands.service."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fordpass.main import fordpass

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from click.testing import CliRunner

_VIN = '1FAHP00000A000000'


def test_service_upcoming_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 20000.0
    mock_command_client.get_service_planner_upcoming.return_value = {
        'upcomingServiceActions': [{
            'id': 'A1',
            'date': '2026-08-01',
            'type': 'MAINTENANCE',
            'title': 'Oil change',
            'tags': ['REGULAR']
        }, {
            'id': 'A2',
            'date': '2026-09-01',
            'type': 'RECALL',
            'title': 'Recall foo',
            'tags': None
        }, 'not a mapping']
    }
    result = runner.invoke(fordpass, ('service', 'upcoming', _VIN))
    assert result.exit_code == 0
    assert 'Oil change' in result.output


def test_service_upcoming_explicit_odometer(runner: CliRunner,
                                            mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_upcoming.return_value = {'upcomingServiceActions': []}
    result = runner.invoke(fordpass, ('service', 'upcoming', _VIN, '--odometer', '12000'))
    assert result.exit_code == 0
    assert 'No upcoming' in result.output


def test_service_upcoming_no_odometer_error(runner: CliRunner,
                                            mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = None
    result = runner.invoke(fordpass, ('service', 'upcoming', _VIN))
    assert result.exit_code != 0
    assert 'Could not determine' in result.output


def test_service_upcoming_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 20000.0
    mock_command_client.get_service_planner_upcoming.return_value = {'upcomingServiceActions': []}
    result = runner.invoke(fordpass, ('service', 'upcoming', _VIN, '--json'))
    assert result.exit_code == 0


def test_service_upcoming_km(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 50000.0
    mock_command_client.get_service_planner_upcoming.return_value = {'upcomingServiceActions': []}
    result = runner.invoke(fordpass, ('service', 'upcoming', _VIN, '--uom', 'km'))
    assert result.exit_code == 0


def test_service_history_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_odometer.return_value = 20000.0
    mock_command_client.get_service_planner_history.return_value = {
        'completedServiceActions': [{
            'id': 'H1',
            'date': '2026-04-01',
            'title': 'First service',
            'price': {
                'total': 100,
                'currencyCode': 'USD'
            },
            'tags': ['REGULAR']
        }, {
            'id': 'H2',
            'date': '2026-03-01',
            'title': 'Tyre',
            'price': None,
            'tags': []
        }]
    }
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '50000'))
    assert result.exit_code == 0
    assert 'First service' in result.output
    assert 'USD' in result.output or '$' in result.output


def test_service_history_empty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {'completedServiceActions': []}
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000'))
    assert result.exit_code == 0
    assert 'No service history' in result.output


def test_service_history_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {'completedServiceActions': []}
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000', '--json'))
    assert result.exit_code == 0


def test_service_upcoming_detail_maintenance(runner: CliRunner,
                                             mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_action_detail.return_value = {
        'id': 'A1',
        'serviceType': 'MAINTENANCE',
        'title': 'Oil change',
        'odometerReading': 12345,
        'maintenanceItem': {
            'maintenanceDetails': {
                'maintenanceDate': '2026-08-01',
                'overview': ['Drain oil', 'Replace filter']
            }
        }
    }
    result = runner.invoke(fordpass,
                           ('service', 'upcoming-detail', 'A1', _VIN, '--odometer', '12345'))
    assert result.exit_code == 0
    assert 'Drain oil' in result.output


def test_service_upcoming_detail_recall(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_action_detail.return_value = {
        'id': 'A1',
        'serviceType': 'RECALL',
        'title': 'Brake recall',
        'odometerReading': 12345,
        'recallItem': {
            'campaignNumber': 'C1',
            'description': 'Faulty brake',
            'safetyRisk': 'Loss of control',
            'remedy': 'Replace caliper'
        }
    }
    result = runner.invoke(fordpass,
                           ('service', 'upcoming-detail', 'A1', _VIN, '--odometer', '12345'))
    assert result.exit_code == 0
    assert 'Faulty brake' in result.output


def test_service_upcoming_detail_unknown_variant(runner: CliRunner,
                                                 mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_action_detail.return_value = {
        'id': 'A1',
        'serviceType': 'UNKNOWN'
    }
    result = runner.invoke(fordpass,
                           ('service', 'upcoming-detail', 'A1', _VIN, '--odometer', '12345'))
    assert result.exit_code == 0


def test_service_upcoming_detail_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_action_detail.return_value = {'id': 'A1'}
    result = runner.invoke(
        fordpass, ('service', 'upcoming-detail', 'A1', _VIN, '--odometer', '12345', '--json'))
    assert result.exit_code == 0


def test_service_history_detail_pretty(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_completed_service_action_detail.return_value = {
        'id': 'H1',
        'dealerName': 'Test Dealer',
        'serviceDate': '2026-04-01',
        'odometerReading': 50000,
        'price': {
            'total': 100,
            'currencyCode': 'EUR'
        },
        'serviceType': 'Maintenance',
        'editable': True,
        'servicesPerformed': ['Oil change'],
        'inspectionsPerformed': ['Brake inspection']
    }
    result = runner.invoke(fordpass,
                           ('service', 'history-detail', 'H1', _VIN, '--odometer', '50000'))
    assert result.exit_code == 0
    assert 'Test Dealer' in result.output
    assert 'Oil change' in result.output


def test_service_history_detail_no_services(runner: CliRunner,
                                            mock_command_client: MagicMock) -> None:
    mock_command_client.get_completed_service_action_detail.return_value = {'id': 'H1'}
    result = runner.invoke(fordpass,
                           ('service', 'history-detail', 'H1', _VIN, '--odometer', '50000'))
    assert result.exit_code == 0
    assert 'No services were recorded' in result.output


def test_service_history_detail_json(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_completed_service_action_detail.return_value = {'id': 'H1'}
    result = runner.invoke(
        fordpass, ('service', 'history-detail', 'H1', _VIN, '--odometer', '50000', '--json'))
    assert result.exit_code == 0


def test_service_history_non_list_actions(runner: CliRunner,
                                          mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {
        'completedServiceActions': 'unexpected'
    }
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000'))
    assert result.exit_code == 0
    assert 'No service history' in result.output


def test_service_history_money_no_currency(runner: CliRunner,
                                           mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {
        'completedServiceActions': [{
            'id': 'H1',
            'date': '2026-04-01',
            'price': {
                'total': 50
            }
        }]
    }
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000'))
    assert result.exit_code == 0


def test_service_history_no_total(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {
        'completedServiceActions': [{
            'id': 'H1',
            'date': '2026-04-01',
            'price': 'not a mapping'
        }]
    }
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000'))
    assert result.exit_code == 0


def test_service_upcoming_detail_maintenance_no_overview(runner: CliRunner,
                                                         mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_action_detail.return_value = {
        'id': 'A1',
        'serviceType': 'MAINTENANCE',
        'title': 'Annual',
        'odometerReading': 12345,
        'maintenanceItem': {
            'maintenanceDetails': {
                'maintenanceDate': '2026-08-01'
            }
        }
    }
    result = runner.invoke(fordpass,
                           ('service', 'upcoming-detail', 'A1', _VIN, '--odometer', '12345'))
    assert result.exit_code == 0


def test_service_upcoming_detail_recall_no_strings(runner: CliRunner,
                                                   mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_action_detail.return_value = {
        'id': 'A1',
        'serviceType': 'RECALL',
        'title': 'Brake recall',
        'odometerReading': 12345,
        'recallItem': {
            'campaignNumber': 'C1',
            'description': None,
            'safetyRisk': '   ',
            'remedy': 42
        }
    }
    result = runner.invoke(fordpass,
                           ('service', 'upcoming-detail', 'A1', _VIN, '--odometer', '12345'))
    assert result.exit_code == 0


def test_service_history_invalid_total(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {
        'completedServiceActions': [{
            'id': 'H1',
            'date': '2026-04-01',
            'price': {
                'total': 'not a number',
                'currencyCode': 'USD'
            }
        }]
    }
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000'))
    assert result.exit_code == 0


def test_service_history_tags_not_list(runner: CliRunner, mock_command_client: MagicMock) -> None:
    mock_command_client.get_service_planner_history.return_value = {
        'completedServiceActions': [{
            'id': 'H1',
            'date': '2026-04-01',
            'tags': 'INVALID'
        }]
    }
    result = runner.invoke(fordpass, ('service', 'history', _VIN, '--odometer', '10000'))
    assert result.exit_code == 0
