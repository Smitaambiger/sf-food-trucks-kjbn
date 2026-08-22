import pytest

from app.utils.geo import haversine_km, is_valid_latitude, is_valid_longitude


def test_haversine_same_point_is_zero():
    assert haversine_km(37.7749, -122.4194, 37.7749, -122.4194) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance_sf_landmarks():
    # Ferry Building to Golden Gate Park (~8.6 km, allow some tolerance)
    ferry_building = (37.7955, -122.3937)
    golden_gate_park = (37.7694, -122.4862)
    distance = haversine_km(*ferry_building, *golden_gate_park)
    assert 8.0 < distance < 9.0


def test_is_valid_latitude():
    assert is_valid_latitude(0)
    assert is_valid_latitude(90)
    assert is_valid_latitude(-90)
    assert not is_valid_latitude(90.1)
    assert not is_valid_latitude(-90.1)


def test_is_valid_longitude():
    assert is_valid_longitude(0)
    assert is_valid_longitude(180)
    assert is_valid_longitude(-180)
    assert not is_valid_longitude(180.1)
    assert not is_valid_longitude(-180.1)
