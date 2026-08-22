from pydantic import BaseModel, Field


class Truck(BaseModel):
    """A single food truck / mobile food facility."""

    permit: str
    applicant: str
    food_items: str | None = None
    address: str | None = None
    location_description: str | None = None
    status: str
    latitude: float
    longitude: float
    schedule_url: str | None = None
    days_hours: str | None = None


class TruckWithDistance(Truck):
    distance_km: float = Field(..., description="Distance from the query point, in kilometers")


class NearbyTrucksResponse(BaseModel):
    query_lat: float
    query_lon: float
    radius_km: float
    count: int
    results: list[TruckWithDistance]


class ErrorResponse(BaseModel):
    detail: str
