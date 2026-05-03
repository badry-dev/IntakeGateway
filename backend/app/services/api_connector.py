import asyncio
import base64
import datetime as _dt
import email.utils
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.core.encryption import decrypt_value


def _parse_retry_after(header_value: str | None) -> float | None:
    """
    Parse an HTTP `Retry-After` header per RFC 7231 §7.1.3.

    Accepts either a non-negative delta-seconds integer or an HTTP-date.
    Returns the wait in seconds, or None if the header is absent / unparseable
    / in the past.
    """
    if not header_value:
        return None
    header_value = header_value.strip()
    try:
        seconds = float(header_value)
        return max(seconds, 0.0)
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(header_value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=_dt.UTC)
    delta = (when - _dt.datetime.now(_dt.UTC)).total_seconds()
    return max(delta, 0.0)


def apply_authentication(
    headers: dict,
    auth_type: str | None = None,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
    oauth_config: dict | None = None,
) -> dict:
    """
    Apply authentication to HTTP headers based on auth type.

    Args:
        headers: Base HTTP headers dictionary
        auth_type: Authentication type ('none', 'bearer', 'api_key', 'basic', 'oauth')
        api_key: Encrypted API key for Bearer or API Key auth
        username: Username for Basic auth
        password: Encrypted password for Basic auth
        oauth_config: OAuth configuration dictionary

    Returns:
        Updated headers dictionary with authentication

    Raises:
        ValueError: If auth configuration is invalid
    """
    if headers is None:
        headers = {}

    if not auth_type or auth_type == "none":
        return headers

    headers = dict(headers)  # Create copy to avoid mutating original

    if auth_type == "bearer":
        # Bearer token authentication
        if not api_key:
            raise ValueError("Bearer token required")

        # Decrypt the API key
        decrypted_key = decrypt_value(api_key)
        headers["Authorization"] = f"Bearer {decrypted_key}"
        logger.debug("Applied Bearer token authentication")

    elif auth_type == "api_key":
        # API Key in custom header
        if not api_key:
            raise ValueError("API key required")

        # Decrypt the API key
        decrypted_key = decrypt_value(api_key)
        header_name = (oauth_config or {}).get("api_key_header", "X-API-Key")
        headers[header_name] = decrypted_key
        logger.debug(f"Applied API Key authentication using header {header_name}")

    elif auth_type == "basic":
        # HTTP Basic Authentication
        if not username or not password:
            raise ValueError("Username and password required")

        # Decrypt the password
        decrypted_password = decrypt_value(password)

        # Encode credentials
        credentials = f"{username}:{decrypted_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
        logger.debug(f"Applied Basic authentication for user: {username}")

    elif auth_type == "oauth":
        # OAuth token authentication. Token may have been resolved by
        # oauth_token_service.get_access_token() and passed in plaintext via
        # `oauth_config['_already_decrypted']=True` — in that case skip decrypt.
        if not oauth_config or "access_token" not in oauth_config:
            logger.warning("OAuth auth configured but no access_token available; skipping auth")
            return headers

        if oauth_config.get("_already_decrypted"):
            access_token = oauth_config["access_token"]
        else:
            access_token = decrypt_value(oauth_config["access_token"])
        headers["Authorization"] = f"Bearer {access_token}"
        logger.debug("Applied OAuth authentication")

    else:
        logger.warning(f"Unknown auth_type {auth_type!r}; skipping auth")

    return headers


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
    oauth_config: dict | None = None,
    max_retries_429: int | None = None,
    max_wait_seconds: int | None = None,
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
        oauth_config=oauth_config,
    )

    # Debug: Show request details (mask sensitive headers)
    debug_headers = dict(headers)
    if "Authorization" in debug_headers:
        auth_value = debug_headers["Authorization"]
        if auth_value.startswith("Bearer "):
            debug_headers["Authorization"] = f"Bearer ***{auth_value[-4:]}"
        elif auth_value.startswith("Basic "):
            debug_headers["Authorization"] = "Basic ***"
    if "X-API-Key" in debug_headers:
        debug_headers["X-API-Key"] = f"***{debug_headers['X-API-Key'][-4:]}"

    logger.info(f"Making API request: {method} {url}")
    logger.info(f"Request headers: {debug_headers}")
    if params:
        logger.debug(f"Query params: {params}")
    if json_body:
        logger.debug(f"Request body: {json_body}")

    # Generate curl command for debugging
    curl_cmd = f"curl -X {method} '{url}'"
    for key, value in headers.items():
        if key == "Authorization":
            curl_cmd += f" -H '{key}: ***'"
        else:
            curl_cmd += f" -H '{key}: {value}'"
    if params:
        curl_cmd += f" -G {' '.join([f'-d {k}={v}' for k, v in params.items()])}"
    if json_body:
        curl_cmd += f" -d '{json_body}'"
    logger.info(f"Equivalent curl: {curl_cmd}")

    timeout = httpx.Timeout(settings.HTTP_TIMEOUT_SECONDS)

    # 429 has its own retry budget so a misbehaving upstream can't exhaust the
    # transient/5xx budget intended for genuine errors.
    rl_max_retries = (
        max_retries_429 if max_retries_429 is not None else settings.HTTP_RATE_LIMIT_DEFAULT_RETRIES
    )
    rl_max_wait = (
        max_wait_seconds if max_wait_seconds is not None else settings.HTTP_RETRY_AFTER_MAX_SECONDS
    )

    transient_attempts = 0  # network errors + 5xx
    rate_limit_attempts = 0  # 429 only

    while True:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(
                    f"API request attempt: transient={transient_attempts}/{max_retries} "
                    f"rate_limit={rate_limit_attempts}/{rl_max_retries}: {method} {url}"
                )
                resp = await client.request(
                    method, url, headers=headers, params=params, json=json_body
                )
                resp.raise_for_status()

                if len(resp.content) > settings.HTTP_MAX_RESPONSE_MB * 1024 * 1024:
                    raise ValueError(
                        f"Response size {len(resp.content)} bytes exceeds "
                        f"limit of {settings.HTTP_MAX_RESPONSE_MB}MB"
                    )

                logger.info(f"API request successful: {method} {url}")
                return resp.json()

        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
            if transient_attempts < max_retries:
                backoff_time = initial_backoff * (2**transient_attempts)
                transient_attempts += 1
                logger.warning(
                    f"API request failed ({type(e).__name__}): {str(e)}. "
                    f"Retrying in {backoff_time}s (transient {transient_attempts}/{max_retries})..."
                )
                await asyncio.sleep(backoff_time)
                continue
            logger.error(f"API request failed after {max_retries + 1} transient attempts: {str(e)}")
            raise

        except httpx.HTTPStatusError as e:
            status = e.response.status_code

            if status == 429:
                # Honor Retry-After if present, else exponential backoff. Cap at rl_max_wait.
                advised = _parse_retry_after(e.response.headers.get("Retry-After"))
                computed = initial_backoff * (2**rate_limit_attempts)
                wait_seconds = advised if advised is not None else computed

                if wait_seconds > rl_max_wait:
                    logger.error(
                        f"API returned 429 with Retry-After={advised}; required wait "
                        f"{wait_seconds}s exceeds cap {rl_max_wait}s. Giving up."
                    )
                    raise

                if rate_limit_attempts < rl_max_retries:
                    rate_limit_attempts += 1
                    logger.warning(
                        f"API returned 429 Too Many Requests "
                        f"(rate_limit {rate_limit_attempts}/{rl_max_retries}). "
                        f"Retrying in {wait_seconds:.2f}s "
                        f"(advised={'yes' if advised is not None else 'no'})..."
                    )
                    await asyncio.sleep(wait_seconds)
                    continue
                logger.error(f"API request failed after {rl_max_retries} rate-limit retries (429)")
                raise

            if 500 <= status < 600 and transient_attempts < max_retries:
                backoff_time = initial_backoff * (2**transient_attempts)
                transient_attempts += 1
                logger.warning(
                    f"API returned server error {status} "
                    f"(transient {transient_attempts}/{max_retries}). "
                    f"Retrying in {backoff_time}s..."
                )
                await asyncio.sleep(backoff_time)
                continue

            logger.error(f"API request failed with status {status}: {str(e)}")
            raise

        except Exception as e:
            # Don't retry on unexpected errors (e.g. response-size ValueError, JSON decode).
            logger.error(f"Unexpected error during API request: {str(e)}")
            raise


async def fetch_with_auth(
    task: Any,
    db: Any,
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    """
    Fetch JSON honoring the Task's auth configuration. Resolves OAuth tokens
    via `oauth_token_service` for `client_credentials` / `refresh_token` grants
    and forces a single refresh-and-retry on a 401 response.

    For non-OAuth tasks this delegates straight to `fetch_json` with the
    Task's configured auth fields (back-compat).

    Per-task rate-limit tuning (rate_limit_max_retries, rate_limit_max_wait_seconds)
    is forwarded to the underlying retry loop.
    """
    # Lazy import to avoid an import cycle (oauth_token_service imports the Task model).
    from app.services import oauth_token_service

    rl_max_retries = getattr(task, "rate_limit_max_retries", None)
    rl_max_wait = getattr(task, "rate_limit_max_wait_seconds", None)

    auth_type = getattr(task, "auth_type", None) or "none"

    # Non-OAuth path: pass Task auth fields through unchanged.
    if auth_type != "oauth":
        return await fetch_json(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_body=json_body,
            auth_type=auth_type,
            api_key=getattr(task, "api_key", None),
            username=getattr(task, "username", None),
            password=getattr(task, "password", None),
            oauth_config=getattr(task, "oauth_config", None),
            max_retries_429=rl_max_retries,
            max_wait_seconds=rl_max_wait,
        )

    # OAuth path: resolve a fresh access token, retry once with a forced refresh on 401.
    forced = False
    while True:
        token = await oauth_token_service.get_access_token(task, db, force_refresh=forced)
        try:
            return await fetch_json(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json_body=json_body,
                auth_type="oauth",
                oauth_config={"access_token": token, "_already_decrypted": True},
                max_retries_429=rl_max_retries,
                max_wait_seconds=rl_max_wait,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401 and not forced:
                logger.warning(
                    f"OAuth request returned 401; forcing token refresh for task_id={task.id}"
                )
                forced = True
                continue
            raise


async def fetch_sample_response(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    json_body: dict | None = None,
    record_path: str | None = None,
    auth_type: str | None = None,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
    oauth_config: dict | None = None,
    task: Any = None,
    db: Any = None,
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
        auth_type: Authentication type ('none', 'bearer', 'api_key', 'basic', 'oauth')
        api_key: Encrypted API key for Bearer or API Key auth
        username: Username for Basic auth
        password: Encrypted password for Basic auth
        oauth_config: OAuth configuration dictionary

    Returns:
        Extracted sample data (dict or list depending on record_path)
        If no record_path specified, returns entire response

    Raises:
        httpx.HTTPError: If API request fails
        ValueError: If response is not valid JSON
        KeyError: If record_path doesn't exist in response
    """
    # Debug logging for auth parameters
    logger.debug(
        f"fetch_sample_response called with auth_type={auth_type}, api_key={'***' if api_key else None}"
    )

    try:
        # When the caller provides a Task + Session (preview / auto-fetch from
        # the column-mapping route), delegate to fetch_with_auth so the new
        # OAuth client_credentials / refresh_token grants are exercised. Falling
        # through to fetch_json with task.oauth_config alone would miss the
        # per-column oauth_grant_type / oauth_client_secret / token_url path
        # and silently fail for any task configured via the new structured fields.
        # Resolve auth_type as caller-arg first, then task.auth_type, so a
        # populated task with auth_type=oauth still routes through fetch_with_auth
        # even if the caller forgot to forward the explicit auth_type kwarg.
        effective_auth_type = (
            auth_type or (getattr(task, "auth_type", None) if task is not None else None) or "none"
        )
        if task is not None and db is not None and effective_auth_type == "oauth":
            response_data = await fetch_with_auth(
                task=task,
                db=db,
                method=method,
                url=url,
                headers=headers,
                params=params,
                json_body=json_body,
            )
        else:
            response_data = await fetch_json(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json_body=json_body,
                max_retries=2,  # Reduce retries for sample fetch
                auth_type=auth_type,
                api_key=api_key,
                username=username,
                password=password,
                oauth_config=oauth_config,
            )

        # Extract data at record_path if provided
        if record_path:
            extracted = _extract_by_path(response_data, record_path)
            logger.info(
                f"Extracted sample data at path '{record_path}': {type(extracted).__name__}"
            )
            return extracted

        logger.info(f"Fetched sample API response: {type(response_data).__name__}")
        return response_data

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch sample response from {url}: {str(e)}")
        raise ValueError(f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching sample response: {str(e)}")
        raise ValueError(f"Failed to fetch sample response: {str(e)}")


def get_record_type_info(data: dict | list, record_path: str | None = None) -> dict:
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
    obj: any, prefix: str, result: dict, max_depth: int = 10, current_depth: int = 0
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
            "parent_path": _get_parent_path(prefix),
        }

    elif isinstance(obj, dict):
        if not obj:  # Empty dict
            field_key = prefix
            result[field_key] = {
                "field_type": "object",
                "sample_value": {},
                "nullable": False,
                "parent_path": _get_parent_path(prefix),
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
            "parent_path": _get_parent_path(prefix),
        }

    elif isinstance(obj, bool):
        # Check bool before int because bool is subclass of int
        field_key = prefix
        result[field_key] = {
            "field_type": "boolean",
            "sample_value": obj,
            "nullable": False,
            "parent_path": _get_parent_path(prefix),
        }

    elif isinstance(obj, int) or isinstance(obj, float):
        field_key = prefix
        result[field_key] = {
            "field_type": "number",
            "sample_value": obj,
            "nullable": False,
            "parent_path": _get_parent_path(prefix),
        }

    elif isinstance(obj, str):
        field_key = prefix
        result[field_key] = {
            "field_type": "string",
            "sample_value": obj,
            "nullable": False,
            "parent_path": _get_parent_path(prefix),
        }

    else:
        # Unknown type, treat as string
        field_key = prefix
        result[field_key] = {
            "field_type": "string",
            "sample_value": str(obj),
            "nullable": False,
            "parent_path": _get_parent_path(prefix),
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
            field_name = part[: part.index("[")]
            index_str = part[part.index("[") + 1 : part.index("]")]

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
