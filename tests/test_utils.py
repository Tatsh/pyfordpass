from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fordpass.utils import (
    MetricsBlock,
    extract_fuel,
    extract_odometer,
    extract_oil_life,
    extract_position,
    find_next_departure,
    find_preferred_dealer_code,
    is_list_like,
    is_washer_fluid_low,
    scalar_metric_value,
    walk_mapping,
)
import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fordpass.typing import AlertsResponse, GarageVehicle


def test_is_list_like_true_for_list() -> None:
    assert is_list_like([1, 2, 3]) is True


def test_is_list_like_true_for_tuple() -> None:
    assert is_list_like((1, 2)) is True


def test_is_list_like_false_for_str() -> None:
    assert is_list_like('not a list') is False


def test_is_list_like_false_for_bytes() -> None:
    assert is_list_like(b'bytes') is False


def test_is_list_like_false_for_dict() -> None:
    assert is_list_like({'a': 1}) is False


def test_is_list_like_false_for_none() -> None:
    assert is_list_like(None) is False


def test_walk_mapping_happy_path() -> None:
    obj: dict[str, Any] = {'a': {'b': {'c': 42}}}
    assert walk_mapping(obj, 'a', 'b', 'c') == 42


def test_walk_mapping_missing_key_returns_none() -> None:
    obj: dict[str, Any] = {'a': {'b': {}}}
    assert walk_mapping(obj, 'a', 'b', 'c') is None


def test_walk_mapping_non_mapping_returns_none() -> None:
    assert walk_mapping({'a': 'not a mapping'}, 'a', 'b') is None


def test_walk_mapping_no_keys_returns_root() -> None:
    obj: dict[str, Any] = {'a': 1}
    assert walk_mapping(obj) is obj


def test_scalar_metric_value_returns_value_field() -> None:
    assert scalar_metric_value({'value': 5, 'updateTime': '2026-01-01'}) == 5


def test_scalar_metric_value_returns_none_for_missing_value() -> None:
    assert scalar_metric_value({'updateTime': '2026-01-01'}) is None


def test_scalar_metric_value_returns_none_for_list_shaped() -> None:
    assert scalar_metric_value([{'value': 1}, {'value': 2}]) is None


def test_scalar_metric_value_returns_none_for_none() -> None:
    assert scalar_metric_value(None) is None


def test_extract_fuel_pair() -> None:
    metrics: MetricsBlock = {'fuelLevel': {'value': 75.0}, 'fuelRange': {'value': 400.0}}
    pct, rng = extract_fuel(metrics)
    assert pct == pytest.approx(75.0)
    assert rng == pytest.approx(400.0)


def test_extract_fuel_missing_both_returns_none_pair() -> None:
    assert extract_fuel({}) == (None, None)


def test_extract_odometer_present() -> None:
    metrics: MetricsBlock = {'odometer': {'value': 12345.6}}
    assert extract_odometer(metrics) == pytest.approx(12345.6)


def test_extract_odometer_absent_returns_none() -> None:
    assert extract_odometer({}) is None


def test_extract_oil_life_present() -> None:
    metrics: MetricsBlock = {'oilLifeRemaining': {'value': 80.0}}
    assert extract_oil_life(metrics) == pytest.approx(80.0)


def test_extract_oil_life_absent_returns_none() -> None:
    assert extract_oil_life({}) is None


def test_extract_position_minimal() -> None:
    metrics: MetricsBlock = {'position': {'value': {'location': {'lat': 40.7, 'lon': -74.0}}}}
    result = extract_position(metrics)
    assert result is not None
    assert result['lat'] == pytest.approx(40.7)
    assert result['lon'] == pytest.approx(-74.0)


def test_extract_position_full() -> None:
    metrics: MetricsBlock = {
        'position': {
            'value': {
                'location': {
                    'lat': 40.7,
                    'lon': -74.0,
                    'alt': 10.0
                }
            },
            'updateTime': '2026-01-01T00:00:00Z'
        },
        'heading': {
            'value': 90.0
        },
        'compassDirection': {
            'value': 'EAST'
        }
    }
    result = extract_position(metrics)
    assert result is not None
    assert result['alt'] == pytest.approx(10.0)
    assert result['heading'] == pytest.approx(90.0)
    assert result['compass'] == 'EAST'
    assert result['update_time'] == '2026-01-01T00:00:00Z'


def test_extract_position_missing_lat_lon_returns_none() -> None:
    assert extract_position({}) is None


def test_extract_position_non_mapping_value_returns_none() -> None:
    metrics = cast('MetricsBlock', {'position': {'value': 'not a mapping'}})
    assert extract_position(metrics) is None


def test_extract_position_non_mapping_location_returns_none() -> None:
    metrics = cast('MetricsBlock', {'position': {'value': {'location': 'not a mapping'}}})
    assert extract_position(metrics) is None


def test_extract_position_heading_nested_value() -> None:
    metrics: MetricsBlock = {
        'position': {
            'value': {
                'location': {
                    'lat': 1.0,
                    'lon': 2.0
                }
            }
        },
        'heading': {
            'value': {
                'heading': 180.0
            }
        }
    }
    result = extract_position(metrics)
    assert result is not None
    assert result['heading'] == pytest.approx(180.0)


def test_is_washer_fluid_low_true() -> None:
    response: AlertsResponse = {'alerts': [{'alertIdentifier': 'E19-374-43'}]}
    assert is_washer_fluid_low(response) is True


def test_is_washer_fluid_low_false() -> None:
    response: AlertsResponse = {'alerts': [{'alertIdentifier': 'E19-100-01'}]}
    assert is_washer_fluid_low(response) is False


def test_is_washer_fluid_low_empty_alerts() -> None:
    response: AlertsResponse = {'alerts': []}
    assert is_washer_fluid_low(response) is False


def test_is_washer_fluid_low_missing_alerts_key() -> None:
    response: AlertsResponse = {}
    assert is_washer_fluid_low(response) is False


def test_find_preferred_dealer_code_bare_list() -> None:
    garage: Sequence[GarageVehicle] = [{'vin': 'VIN1', 'preferredDealer': 'D001'}]
    assert find_preferred_dealer_code(garage, 'VIN1') == 'D001'


def test_find_preferred_dealer_code_envelope() -> None:
    garage: Mapping[str, Sequence[GarageVehicle]] = {
        'vehicles': [{
            'vin': 'VIN1',
            'preferredDealer': 'D001'
        }]
    }
    assert find_preferred_dealer_code(garage, 'VIN1') == 'D001'


def test_find_preferred_dealer_code_vin_not_found() -> None:
    garage: Sequence[GarageVehicle] = [{'vin': 'VIN1', 'preferredDealer': 'D001'}]
    assert find_preferred_dealer_code(garage, 'OTHER_VIN') is None


def test_find_preferred_dealer_code_no_preferred_dealer() -> None:
    garage: Sequence[GarageVehicle] = [{'vin': 'VIN1'}]
    assert find_preferred_dealer_code(garage, 'VIN1') is None


def test_find_preferred_dealer_code_non_string_dealer() -> None:
    garage = cast('Sequence[GarageVehicle]', [{'vin': 'VIN1', 'preferredDealer': 123}])
    assert find_preferred_dealer_code(garage, 'VIN1') is None


def test_find_preferred_dealer_code_invalid_garage_shape() -> None:
    garage: Mapping[str, Sequence[GarageVehicle]] = {}
    assert find_preferred_dealer_code(garage, 'VIN1') is None


def test_find_next_departure_matched() -> None:
    metrics: MetricsBlock = {
        'xevNextDepartureTimeScheduleId': {
            'value': 'sched-1'
        },
        'xevDepartureSchedules': {
            'value': {
                'departureLocations': [{
                    'departureSchedules': [{
                        'scheduleId': 'sched-1'
                    }, {
                        'scheduleId': 'sched-2'
                    }]
                }]
            }
        }
    }
    result = find_next_departure(metrics)
    assert result is not None
    assert result['scheduleId'] == 'sched-1'


def test_find_next_departure_no_next_id() -> None:
    assert find_next_departure({}) is None


def test_find_next_departure_no_match() -> None:
    metrics: MetricsBlock = {
        'xevNextDepartureTimeScheduleId': {
            'value': 'sched-X'
        },
        'xevDepartureSchedules': {
            'value': {
                'departureLocations': [{
                    'departureSchedules': [{
                        'scheduleId': 'sched-1'
                    }]
                }]
            }
        }
    }
    assert find_next_departure(metrics) is None


def test_extract_position_heading_mapping_with_missing_inner() -> None:
    metrics: MetricsBlock = {
        'position': {
            'value': {
                'location': {
                    'lat': 1.0,
                    'lon': 2.0
                }
            }
        },
        'heading': {
            'value': {
                'heading': None
            }
        }
    }
    result = extract_position(metrics)
    assert result is not None
    assert 'heading' not in result


def test_find_preferred_dealer_code_non_list_non_mapping() -> None:
    garage = cast('Sequence[GarageVehicle]', None)
    assert find_preferred_dealer_code(garage, 'VIN1') is None


def test_find_next_departure_tree_not_mapping() -> None:
    metrics = cast(
        'MetricsBlock', {
            'xevNextDepartureTimeScheduleId': {
                'value': 'sched-1'
            },
            'xevDepartureSchedules': {
                'value': 'not a mapping'
            }
        })
    assert find_next_departure(metrics) is None
