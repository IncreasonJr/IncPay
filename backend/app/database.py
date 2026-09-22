from typing import Optional
import logging
from supabase import create_client, Client

from app.config import get_settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def init_supabase_client() -> Optional[Client]:
    """
    Initialize and return the Supabase client using configured environment variables.
    Returns None if credentials are not configured.
    """
    global _supabase_client
    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Supabase credentials are not fully configured. "
            "Set SUPABASE_URL and SUPABASE_KEY in your environment."
        )
        _supabase_client = None
        return None

    try:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Supabase client successfully initialized.")
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")
        _supabase_client = None

    return _supabase_client


def get_supabase_client() -> Optional[Client]:
    """
    Retrieve the current Supabase client, initializing it if not already done.
    """
    global _supabase_client
    if _supabase_client is None:
        return init_supabase_client()
    return _supabase_client


# Module-level client instance (can be None if credentials are not provided)
supabase: Optional[Client] = get_supabase_client()
