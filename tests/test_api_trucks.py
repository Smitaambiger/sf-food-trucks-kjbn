from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_truck_service
from app.main import app
from app.schemas.truck import TruckWithDistance


@pytest.fixture
def client_with_mocked_service():
    mock_service = AsyncMock()
    mock_service.default_radius_km = 1.0
    mock_service.find_nearby.return_value = [
        TruckWithDistance(
            permit="24MFF-0001",
            applicant="Taco Palace",
            food_items="Tacos",
            address="100 Market St",
            location_description=None,
            status="APPROVED",
            latitude=37.7749,
            longitude=-122.4194,
            distance_km=0.0,
        )
    ]

    app.dependency_overrides[get_truck_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_nearby_success(client_with_mocked_service):
    response = client_with_mocked_service.get(
        "/api/v1/trucks/nearby", params={"lat": 37.7749, "lon": -122.4194}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["applicant"] == "Taco Palace"


def test_nearby_rejects_out_of_range_latitude(client_with_mocked_service):
    response = client_with_mocked_service.get(
        "/api/v1/trucks/nearby", params={"lat": 999, "lon": -122.4194}
    )
    assert response.status_code == 422  # FastAPI query validation


def test_health_check():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
