import asyncio
import logging
import time

from app.core.config import Settings
from app.core.exceptions import InvalidCoordinatesError, InvalidQueryParamsError
from app.schemas.truck import Truck, TruckWithDistance
from app.services.datasf_client import DataSFClient
from app.utils.geo import haversine_km, is_valid_latitude, is_valid_longitude

logger = logging.getLogger(__name__)


def _parse_truck(raw: dict) -> Truck | None:
    """Map one raw DataSF row into our domain model. Returns None for unusable rows."""
    try:
        lat = float(raw["latitude"])
        lon = float(raw["longitude"])
    except (KeyError, ValueError, TypeError):
        return None

    if lat == 0.0 and lon == 0.0:
        return None  # DataSF uses 0,0 for permits with no geocoded location yet.

    return Truck(
        permit=raw.get("permit", "unknown"),
        applicant=raw.get("applicant", "Unknown vendor"),
        food_items=raw.get("fooditems"),
        address=raw.get("address"),
        location_description=raw.get("locationdescription"),
        status=raw.get("status", "UNKNOWN"),
        latitude=lat,
        longitude=lon,
        schedule_url=raw.get("schedule"),
        days_hours=raw.get("dayshours"),
    )


class TruckService:
    """Business logic for querying nearby food trucks.

    Owns a small in-memory cache of the (slow-changing) truck dataset so a
    burst of user requests doesn't translate into a burst of calls to DataSF.
    """

    def __init__(self, settings: Settings, client: DataSFClient):
        self._settings = settings
        self._client = client
        self._cache: list[Truck] = []
        self._cache_loaded_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def default_radius_km(self) -> float:
        return self._settings.default_radius_km

    async def _get_trucks(self) -> list[Truck]:
        now = time.monotonic()
        if self._cache and (now - self._cache_loaded_at) < self._settings.cache_ttl_seconds:
            return self._cache

        async with self._lock:
            # Another coroutine may have refreshed the cache while we waited for the lock.
            now = time.monotonic()
            if self._cache and (now - self._cache_loaded_at) < self._settings.cache_ttl_seconds:
                return self._cache

            raw_rows = await self._client.fetch_active_trucks()
            trucks = [t for t in (_parse_truck(r) for r in raw_rows) if t is not None]
            logger.info("Loaded %d/%d usable truck records from DataSF", len(trucks), len(raw_rows))

            self._cache = trucks
            self._cache_loaded_at = time.monotonic()
            return self._cache

    async def find_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: float | None = None,
        food_type: str | None = None,
        limit: int | None = None,
    ) -> list[TruckWithDistance]:
        if not is_valid_latitude(lat) or not is_valid_longitude(lon):
            raise InvalidCoordinatesError(f"lat/lon out of range: ({lat}, {lon})")

        radius_km = radius_km if radius_km is not None else self._settings.default_radius_km
        if radius_km <= 0 or radius_km > self._settings.max_radius_km:
            raise InvalidQueryParamsError(
                f"radius_km must be between 0 and {self._settings.max_radius_km}"
            )

        limit = limit if limit is not None else self._settings.max_results
        if limit <= 0 or limit > self._settings.max_results:
            raise InvalidQueryParamsError(f"limit must be between 1 and {self._settings.max_results}")

        trucks = await self._get_trucks()

        if food_type:
            needle = food_type.strip().lower()
            trucks = [t for t in trucks if t.food_items and needle in t.food_items.lower()]

        results: list[TruckWithDistance] = []
        for truck in trucks:
            distance = haversine_km(lat, lon, truck.latitude, truck.longitude)
            if distance <= radius_km:
                results.append(TruckWithDistance(**truck.model_dump(), distance_km=round(distance, 3)))

        results.sort(key=lambda t: t.distance_km)
        return results[:limit]
