import logging
import httpx
from supabase import create_client, Client, ClientOptions
from .config import settings

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Initialize and return a reusable Supabase client instance.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_ANON_KEY environment variables are not set.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be configured."
        )

    if not settings.SUPABASE_URL.lower().startswith("https://"):
        raise ValueError(
            "SUPABASE_URL must begin with https:// to ensure secure communication."
        )

    _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase_client


def create_scoped_supabase_client(token: str) -> Client:
    """Create a new request-scoped Supabase client instance authenticated with the caller's bearer JWT.

    Does not mutate the shared Supabase client instance.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_ANON_KEY environment variables are not set,
                    or if SUPABASE_URL does not begin with https://.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be configured."
        )

    if not settings.SUPABASE_URL.lower().startswith("https://"):
        raise ValueError(
            "SUPABASE_URL must begin with https:// to ensure secure communication."
        )

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

    if not url.lower().startswith("https://"):
        return {
            "status": "error",
            "message": "SUPABASE_URL must begin with https:// to ensure secure communication.",
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

