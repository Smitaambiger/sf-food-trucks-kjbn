import logging

import httpx

from app.core.config import Settings
from app.core.exceptions import UpstreamServiceError
from app.core.logging import log_duration

logger = logging.getLogger(__name__)

# Only rows with these statuses represent trucks that may actually be operating.
_ACTIVE_STATUSES = {"APPROVED", "REQUESTED", "ISSUED"}


class DataSFClient:
    """Thin wrapper around the DataSF Socrata "Mobile Food Facility Permit" API.

    Isolated in its own class so the rest of the app never touches raw HTTP or
    the upstream's field names directly - if DataSF changes its schema or we
    swap providers, only this file changes.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    async def fetch_active_trucks(self) -> list[dict]:
        """Fetch all currently-active mobile food facility permits.

        Retries transient network/5xx failures with backoff before giving up.
        Raises UpstreamServiceError if the upstream never responds successfully.
        """
        params = {
            "$limit": 5000,
            "$where": "status in(" + ",".join(f"'{s}'" for s in _ACTIVE_STATUSES) + ")",
        }
        headers = {}
        if self._settings.datasf_app_token:
            headers["X-App-Token"] = self._settings.datasf_app_token

        last_error: Exception | None = None
        for attempt in range(1, self._settings.datasf_max_retries + 1):
            try:
                with log_duration(logger, f"DataSF fetch (attempt {attempt})"):
                    async with httpx.AsyncClient(timeout=self._settings.datasf_timeout_seconds) as client:
                        response = await client.get(
                            self._settings.datasf_base_url, params=params, headers=headers
                        )
                        response.raise_for_status()
                        return response.json()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                logger.warning("DataSF request attempt %d/%d failed: %s",
                                attempt, self._settings.datasf_max_retries, exc)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if 400 <= exc.response.status_code < 500:
                    # Client errors (bad request, auth) won't be fixed by retrying.
                    break
                logger.warning("DataSF request attempt %d/%d returned %s",
                                attempt, self._settings.datasf_max_retries, exc.response.status_code)

        logger.error("DataSF fetch exhausted retries: %s", last_error)
        raise UpstreamServiceError(f"Failed to fetch data from DataSF: {last_error}")
