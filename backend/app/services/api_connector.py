
import asyncio
import httpx
import base64
from loguru import logger
from app.core.config import settings
from app.core.encryption import decrypt_value


async def fetch_json(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    json_body: dict | None = None,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    auth_type: str | None = None,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
    oauth_config: dict | None = None
) -> dict:
    """
    Fetch JSON data from API with exponential backoff retry logic and authentication
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers: Optional HTTP headers
        params: Optional query parameters
        json_body: Optional JSON request body
        max_retries: Maximum number of retry attempts (default: 3)
        initial_backoff: Initial backoff delay in seconds (default: 1.0)
        auth_type: Authentication type ('none', 'bearer', 'api_key', 'basic', 'oauth')
        api_key: Encrypted API key for Bearer or API Key auth
        username: Username for Basic auth
        password: Encrypted password for Basic auth
        oauth_config: OAuth configuration dictionary
    
    Returns:
        Parsed JSON response as dictionary
    
    Raises:
        httpx.HTTPError: If all retries fail
        ValueError: If response size exceeds limit or auth is invalid
    """
    # Apply authentication to headers
    headers = apply_authentication(
        headers=headers or {},
        auth_type=auth_type,
        api_key=api_key,
        username=username,
        password=password,
        oauth_config=oauth_config
    )
    
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


async def fetch_sample_response(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    json_body: dict | None = None,
    record_path: str | None = None
) -> dict | list:
    """
    Fetch sample API response for preview and field mapping purposes.
    
    Uses lenient JSON parsing to handle malformed responses gracefully.
    Automatically extracts records at the specified JSONPath (e.g., "data.items[0]").
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target API endpoint
        headers: Optional HTTP headers (auth, custom headers)
        params: Optional query parameters
        json_body: Optional JSON request body
        record_path: Optional JSONPath to extract records (e.g., "data.items[0]" or "results")
    
    Returns:
        Extracted sample data (dict or list depending on record_path)
        If no record_path specified, returns entire response
    
    Raises:
        httpx.HTTPError: If API request fails
        ValueError: If response is not valid JSON
        KeyError: If record_path doesn't exist in response
    """
    try:
        response_data = await fetch_json(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_body=json_body,
            max_retries=2  # Reduce retries for sample fetch
        )
        
        # Extract data at record_path if provided
        if record_path:
            extracted = _extract_by_path(response_data, record_path)
            logger.info(f"Extracted sample data at path '{record_path}': {type(extracted).__name__}")
            return extracted
        
        logger.info(f"Fetched sample API response: {type(response_data).__name__}")
        return response_data
    
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch sample response from {url}: {str(e)}")
        raise ValueError(f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching sample response: {str(e)}")
        raise ValueError(f"Failed to fetch sample response: {str(e)}")


def get_record_type_info(
    data: dict | list,
    record_path: str | None = None
) -> dict:
    """
    Infer field types and flatten nested JSON structure for column mapping.
    
    Converts nested objects to dot notation (e.g., {"user": {"name": "Alice"}} → 
    {"user.name": "Alice"}). Automatically detects field types (string, number, 
    boolean, null, array, object) and includes sample values.
    
    Supports arbitrarily deep nesting levels. Arrays are kept as-is (not exploded).
    
    Args:
        data: Sample response data (dict or list)
        record_path: Optional JSONPath if data contains multiple records
    
    Returns:
        Flattened and typed field information:
        {
            "user.name": {
                "field_type": "string",
                "sample_value": "Alice",
                "nullable": False,
                "parent_path": "user"
            },
            ...
        }
    
    Raises:
        ValueError: If data format is invalid
    """
    try:
        # If data is a list, take first record for type inference
        if isinstance(data, list):
            if not data:
                raise ValueError("Cannot infer types from empty list")
            record = data[0]
        else:
            record = data
        
        if not isinstance(record, dict):
            raise ValueError(f"Expected dict or list, got {type(record).__name__}")
        
        # Flatten and infer types
        flattened = {}
        _flatten_dict(record, "", flattened)
        
        logger.info(f"Inferred types for {len(flattened)} fields from sample data")
        return flattened
    
    except Exception as e:
        logger.error(f"Error inferring record type info: {str(e)}")
        raise ValueError(f"Failed to infer field types: {str(e)}")


def _flatten_dict(
    obj: any,
    prefix: str,
    result: dict,
    max_depth: int = 10,
    current_depth: int = 0
) -> None:
    """
    Recursively flatten nested dictionary to dot notation.
    
    Args:
        obj: Object to flatten
        prefix: Current path prefix (e.g., "user.address")
        result: Output dictionary accumulating flattened fields
        max_depth: Maximum nesting depth to prevent infinite recursion
        current_depth: Current recursion depth
    """
    if current_depth >= max_depth:
        logger.warning(f"Max nesting depth ({max_depth}) reached at path '{prefix}'")
        return
    
    if obj is None:
        # Add null field
        field_key = prefix
        result[field_key] = {
            "field_type": "null",
            "sample_value": None,
            "nullable": True,
            "parent_path": _get_parent_path(prefix)
        }
    
    elif isinstance(obj, dict):
        if not obj:  # Empty dict
            field_key = prefix
            result[field_key] = {
                "field_type": "object",
                "sample_value": {},
                "nullable": False,
                "parent_path": _get_parent_path(prefix)
            }
        else:
            # Recursively process nested dict
            for key, value in obj.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                _flatten_dict(value, new_prefix, result, max_depth, current_depth + 1)
    
    elif isinstance(obj, list):
        # Keep arrays as-is, don't explode (Phase 1 limitation)
        field_key = prefix
        result[field_key] = {
            "field_type": "array",
            "sample_value": obj if obj else [],
            "nullable": False,
            "parent_path": _get_parent_path(prefix)
        }
    
    elif isinstance(obj, bool):
        # Check bool before int because bool is subclass of int
        field_key = prefix
        result[field_key] = {
            "field_type": "boolean",
            "sample_value": obj,
            "nullable": False,
            "parent_path": _get_parent_path(prefix)
        }
    
    elif isinstance(obj, int) or isinstance(obj, float):
        field_key = prefix
        result[field_key] = {
            "field_type": "number",
            "sample_value": obj,
            "nullable": False,
            "parent_path": _get_parent_path(prefix)
        }
    
    elif isinstance(obj, str):
        field_key = prefix
        result[field_key] = {
            "field_type": "string",
            "sample_value": obj,
            "nullable": False,
            "parent_path": _get_parent_path(prefix)
        }
    
    else:
        # Unknown type, treat as string
        field_key = prefix
        result[field_key] = {
            "field_type": "string",
            "sample_value": str(obj),
            "nullable": False,
            "parent_path": _get_parent_path(prefix)
        }


def _extract_by_path(data: dict | list, path: str) -> any:
    """
    Extract value from nested structure using dot notation and array indexing.
    
    Supports paths like "data.items[0]", "results", "user.address.city"
    
    Args:
        data: Data structure to extract from
        path: Path string with dot notation and optional array indices
    
    Returns:
        Extracted value
    
    Raises:
        KeyError: If path doesn't exist
    """
    current = data
    parts = path.split(".")
    
    for part in parts:
        # Check if part has array index notation [n]
        if "[" in part and "]" in part:
            # Extract field name and index
            field_name = part[:part.index("[")]
            index_str = part[part.index("[") + 1:part.index("]")]
            
            try:
                index = int(index_str)
            except ValueError:
                raise KeyError(f"Invalid array index in path: {part}")
            
            # Navigate to field first if it has a name
            if field_name:
                if not isinstance(current, dict) or field_name not in current:
                    raise KeyError(f"Path not found: {path}")
                current = current[field_name]
            
            # Apply array index
            if not isinstance(current, list):
                raise KeyError(f"Expected list at {part}, got {type(current).__name__}")
            if index >= len(current):
                raise KeyError(f"Array index {index} out of range for path: {path}")
            current = current[index]
        else:
            # Regular dot notation
            if not isinstance(current, dict):
                raise KeyError(f"Expected dict at {part}, got {type(current).__name__}")
            if part not in current:
                raise KeyError(f"Key '{part}' not found in path: {path}")
            current = current[part]
    
    return current


def _get_parent_path(field_path: str) -> str | None:
    """
    Extract parent path from dot notation field path.
    
    Examples:
        "user.address.city" → "user.address"
        "user.name" → "user"
        "name" → None
    """
    if "." not in field_path:
        return None
    return field_path.rsplit(".", 1)[0]
