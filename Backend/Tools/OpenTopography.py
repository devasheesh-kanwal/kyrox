# backend/tools/base_client.py
import httpx
import logging

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

async def fetch_json(url: str, params: dict, error_label: str) -> dict:
    """Shared async GET + error handling for external API tools."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
    except httpx.RequestError as exc:
        logger.error("%s request failed: %s", error_label, exc)
        raise Exception(f"Failed to reach {error_label}") from exc

    if response.is_success:
        return response.json()

    logger.error("%s error %s: %s", error_label, response.status_code, response.text)
    raise Exception(f"{error_label} request failed with status {response.status_code}")