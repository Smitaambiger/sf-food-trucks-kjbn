import httpx
import pytest
import respx

from app.core.exceptions import UpstreamServiceError
from app.services.datasf_client import DataSFClient


async def test_fetch_active_trucks_success(settings):
    client = DataSFClient(settings)
    with respx.mock:
        respx.get(settings.datasf_base_url).mock(
            return_value=httpx.Response(200, json=[{"permit": "1"}])
        )
        result = await client.fetch_active_trucks()
    assert result == [{"permit": "1"}]


async def test_retries_on_timeout_then_succeeds(settings):
    client = DataSFClient(settings)
    with respx.mock:
        route = respx.get(settings.datasf_base_url)
        route.side_effect = [
            httpx.TimeoutException("boom"),
            httpx.Response(200, json=[]),
        ]
        result = await client.fetch_active_trucks()
    assert result == []
    assert route.call_count == 2


async def test_gives_up_after_max_retries(settings):
    client = DataSFClient(settings)
    with respx.mock:
        respx.get(settings.datasf_base_url).mock(side_effect=httpx.TimeoutException("boom"))
        with pytest.raises(UpstreamServiceError):
            await client.fetch_active_trucks()


async def test_client_error_does_not_retry(settings):
    client = DataSFClient(settings)
    with respx.mock:
        route = respx.get(settings.datasf_base_url).mock(
            return_value=httpx.Response(400, json={"error": "bad request"})
        )
        with pytest.raises(UpstreamServiceError):
            await client.fetch_active_trucks()
    assert route.call_count == 1
