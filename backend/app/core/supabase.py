import logging
from urllib.parse import urlparse
import httpx
from supabase import create_client, Client, ClientOptions
from .config import settings

logger = logging.getLogger(__name__)

APPROVED_DEV_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_supabase_client: Client | None = None


def validate_supabase_url(url: str, environment: str | None = None) -> None:
    """Validate that SUPABASE_URL uses HTTPS, or HTTP strictly on local loopback in development.

    Raises:
        ValueError: If the URL is malformed, uses HTTP on a non-loopback host, or uses HTTP
                    outside the 'development' environment.
    """
    raw_url = (url or "").strip()
    if not raw_url or any(ch.isspace() for ch in raw_url):
        raise ValueError(
            "SUPABASE_URL must begin with https:// to ensure secure communication."
        )

    try:
        parsed = urlparse(raw_url)
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(
            "SUPABASE_URL must begin with https:// to ensure secure communication."
        ) from exc

    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()

    if not parsed.netloc or not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError(
            "SUPABASE_URL must begin with https:// to ensure secure communication."
        )

    if scheme == "https":
        return

    active_env = (environment if environment is not None else settings.ENVIRONMENT or "").strip().lower()
    if scheme == "http" and active_env == "development" and hostname in APPROVED_DEV_LOOPBACK_HOSTS:
        return

    raise ValueError(
        "SUPABASE_URL must begin with https:// to ensure secure communication."
    )


def get_supabase_client() -> Client:
    """Initialize and return a reusable Supabase client instance.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_ANON_KEY environment variables are not set.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY):
        raise ValueError(
            "SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY must be configured."
        )

    validate_supabase_url(settings.SUPABASE_URL)

    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    _supabase_client = create_client(settings.SUPABASE_URL, key)
    return _supabase_client


_service_role_supabase_client: Client | None = None


def get_service_role_supabase_client() -> Client:
    """Initialize and return a reusable Supabase client authenticated strictly with SUPABASE_SERVICE_ROLE_KEY.

    Fails closed if SUPABASE_SERVICE_ROLE_KEY is missing. Never falls back to the anon key.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not configured,
                    or if SUPABASE_URL does not begin with https:// (except approved dev loopback).
    """
    global _service_role_supabase_client

    if _service_role_supabase_client is not None:
        return _service_role_supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured for privileged operations."
        )

    validate_supabase_url(settings.SUPABASE_URL)

    _service_role_supabase_client = create_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
    )
    return _service_role_supabase_client


def create_scoped_supabase_client(token: str) -> Client:
    """Create a new request-scoped Supabase client instance authenticated with the caller's bearer JWT.

    Does not mutate the shared Supabase client instance.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_ANON_KEY environment variables are not set,
                    or if SUPABASE_URL does not begin with https:// (except approved dev loopback).
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be configured."
        )

    validate_supabase_url(settings.SUPABASE_URL)

    options = ClientOptions(headers={"Authorization": f"Bearer {token}"})
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY, options=options)
    client.postgrest.auth(token)
    return client



def verify_supabase_connection() -> dict:
    """Verify connectivity to the configured Supabase instance without accessing database tables.

    Returns:
        dict: Operational status and message detailing connection verification result.
    """
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_ANON_KEY

    if not url or not key:
        return {
            "status": "unconfigured",
            "message": "SUPABASE_URL or SUPABASE_ANON_KEY is not set.",
        }

    try:
        validate_supabase_url(url)
    except ValueError as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


    # Perform a minimal network reachability ping to the Supabase REST root endpoint
    rest_url = f"{url.rstrip('/')}/rest/v1/"
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(rest_url, headers=headers)
            status_code = response.status_code
            if status_code == 200:
                return {
                    "status": "connected",
                    "url": url,
                    "status_code": status_code,
                }
            elif status_code in (401, 403):
                return {
                    "status": "error",
                    "message": "Invalid or unauthorized credentials provided for Supabase.",
                    "status_code": status_code,
                }
            elif status_code == 404:
                return {
                    "status": "error",
                    "message": "Invalid Supabase REST endpoint URL.",
                    "status_code": status_code,
                }
            elif status_code >= 500:
                return {
                    "status": "error",
                    "message": f"Supabase server error returned HTTP {status_code}.",
                    "status_code": status_code,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unexpected HTTP status {status_code} received from Supabase.",
                    "status_code": status_code,
                }
    except Exception as exc:
        logger.error(f"Supabase connection verification failed: {exc}")
        return {
            "status": "error",
            "message": f"Could not reach Supabase endpoint: {exc}",
        }

