
import asyncio
import httpx
from loguru import logger
from app.core.config import settings


async def fetch_json(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    json_body: dict | None = None,
    max_retries: int = 3,
    initial_backoff: float = 1.0
) -> dict:
    """
    Fetch JSON data from API with exponential backoff retry logic
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers: Optional HTTP headers
        params: Optional query parameters
        json_body: Optional JSON request body
        max_retries: Maximum number of retry attempts (default: 3)
        initial_backoff: Initial backoff delay in seconds (default: 1.0)
    
    Returns:
        Parsed JSON response as dictionary
    
    Raises:
        httpx.HTTPError: If all retries fail
        ValueError: If response size exceeds limit
    """
    timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS)
    
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"API request attempt {attempt + 1}/{max_retries + 1}: {method} {url}")
                
                resp = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body
                )
                resp.raise_for_status()
                
                # Check response size limit
                if len(resp.content) > settings.HTTP_MAX_RESPONSE_MB * 1024 * 1024:
                    raise ValueError(
                        f"Response size {len(resp.content)} bytes exceeds "
                        f"limit of {settings.HTTP_MAX_RESPONSE_MB}MB"
                    )
                
                logger.info(f"API request successful: {method} {url} (attempt {attempt + 1})")
                return resp.json()
        
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
            # Retry on network/timeout errors
            if attempt < max_retries:
                backoff_time = initial_backoff * (2 ** attempt)
                logger.warning(
                    f"API request failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                    f"Retrying in {backoff_time}s..."
                )
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"API request failed after {max_retries + 1} attempts: {str(e)}")
                raise
        
        except httpx.HTTPStatusError as e:
            # Don't retry on client errors (4xx), but do retry on server errors (5xx)
            if e.response.status_code >= 500 and attempt < max_retries:
                backoff_time = initial_backoff * (2 ** attempt)
                logger.warning(
                    f"API returned server error {e.response.status_code} "
                    f"(attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {backoff_time}s..."
                )
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"API request failed with status {e.response.status_code}: {str(e)}")
                raise
        
        except Exception as e:
            # Don't retry on unexpected errors
            logger.error(f"Unexpected error during API request: {str(e)}")
            raise
    
    # Should never reach here, but just in case
    raise RuntimeError("Retry logic failed unexpectedly")
