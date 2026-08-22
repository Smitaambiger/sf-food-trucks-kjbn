import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_truck_service
from app.schemas.truck import NearbyTrucksResponse
from app.services.truck_service import TruckService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trucks", tags=["trucks"])


@router.get("/nearby", response_model=NearbyTrucksResponse)
async def get_nearby_trucks(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the search point"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the search point"),
    radius_km: float | None = Query(None, gt=0, description="Search radius in kilometers"),
    food_type: str | None = Query(None, description="Free-text filter on food items, e.g. 'tacos'"),
    limit: int | None = Query(None, gt=0, description="Max number of results to return"),
    service: TruckService = Depends(get_truck_service),
) -> NearbyTrucksResponse:
    """Return food trucks near a given point, closest first."""
    results = await service.find_nearby(lat, lon, radius_km, food_type, limit)
    logger.info("nearby query lat=%s lon=%s radius_km=%s -> %d results", lat, lon, radius_km, len(results))

    return NearbyTrucksResponse(
        query_lat=lat,
        query_lon=lon,
        radius_km=radius_km if radius_km is not None else service.default_radius_km,
        count=len(results),
        results=results,
    )
