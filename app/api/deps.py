from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.datasf_client import DataSFClient
from app.services.truck_service import TruckService


@lru_cache
def get_truck_service() -> TruckService:
    settings: Settings = get_settings()
    client = DataSFClient(settings)
    return TruckService(settings, client)
