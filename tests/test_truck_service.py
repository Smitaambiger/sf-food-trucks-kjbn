from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import InvalidCoordinatesError, InvalidQueryParamsError
from app.services.truck_service import TruckService


def make_service(settings, raw_rows) -> TruckService:
    client = AsyncMock()
    client.fetch_active_trucks.return_value = raw_rows
    return TruckService(settings, client)


async def test_drops_rows_with_missing_or_invalid_coordinates(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    results = await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=10)
    # Only the 2 rows with valid, non-zero coordinates should survive.
    assert len(results) == 2


async def test_results_sorted_by_distance_ascending(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    results = await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=10)
    distances = [r.distance_km for r in results]
    assert distances == sorted(distances)
    assert results[0].applicant == "Taco Palace"  # exact match to query point


async def test_radius_filters_out_far_trucks(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    results = await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=0.05)
    assert len(results) == 1
    assert results[0].applicant == "Taco Palace"


async def test_food_type_filter_is_case_insensitive(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    results = await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=10, food_type="CURRY")
    assert len(results) == 1
    assert results[0].applicant == "Curry Cart"


async def test_invalid_latitude_raises(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    with pytest.raises(InvalidCoordinatesError):
        await service.find_nearby(lat=200, lon=-122.4194)


async def test_radius_over_max_raises(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    with pytest.raises(InvalidQueryParamsError):
        await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=999)


async def test_dataset_is_cached_between_calls(settings, raw_truck_rows):
    service = make_service(settings, raw_truck_rows)
    await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=10)
    await service.find_nearby(lat=37.7749, lon=-122.4194, radius_km=10)
    assert service._client.fetch_active_trucks.await_count == 1
