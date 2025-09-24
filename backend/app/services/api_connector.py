
import httpx
from app.core.config import settings

async def fetch_json(method: str, url: str, headers: dict | None = None, params: dict | None = None, json_body: dict | None = None):
    timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(method, url, headers=headers, params=params, json=json_body)
        resp.raise_for_status()
        # crude size cap
        if len(resp.content) > settings.HTTP_MAX_RESPONSE_MB * 1024 * 1024:
            raise ValueError("Response too large")
        return resp.json()
