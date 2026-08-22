import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        datasf_base_url="https://example.test/resource/rqzj-sfat.json",
        datasf_timeout_seconds=1.0,
        datasf_max_retries=2,
        cache_ttl_seconds=900,
        default_radius_km=1.0,
        max_radius_km=10.0,
        max_results=50,
    )


@pytest.fixture
def raw_truck_rows() -> list[dict]:
    return [
        {
            "permit": "24MFF-0001",
            "applicant": "Taco Palace",
            "fooditems": "Tacos: burritos: quesadillas",
            "address": "100 Market St",
            "locationdescription": "MARKET ST: 1ST ST to 2ND ST",
            "status": "APPROVED",
            "latitude": "37.7749",
            "longitude": "-122.4194",
        },
        {
            "permit": "24MFF-0002",
            "applicant": "Curry Cart",
            "fooditems": "Curry: rice bowls",
            "address": "500 Howard St",
            "locationdescription": "HOWARD ST: 1ST ST to 2ND ST",
            "status": "APPROVED",
            "latitude": "37.7897",
            "longitude": "-122.3972",
        },
        {
            # No location geocoded yet - should be dropped.
            "permit": "24MFF-0003",
            "applicant": "No Location Truck",
            "fooditems": "Sandwiches",
            "status": "APPROVED",
            "latitude": "0",
            "longitude": "0",
        },
        {
            # Malformed lat/lon - should be dropped.
            "permit": "24MFF-0004",
            "applicant": "Broken Truck",
            "fooditems": "Pizza",
            "status": "APPROVED",
            "latitude": "not-a-number",
            "longitude": "-122.4",
        },
    ]
