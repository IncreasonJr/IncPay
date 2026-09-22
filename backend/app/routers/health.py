from fastapi import APIRouter, Response, status
from typing import Dict, Any

from app.database import get_supabase_client
from app.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic health check")
@router.get("/api/health", summary="Basic health check alias")
def health_check() -> Dict[str, str]:
    """
    Basic health check returning static ok status.
    """
    return {"status": "ok"}


@router.get("/api/health/db", summary="Database health check")
@router.get("/health/db", summary="Database health check alias")
def db_health_check(response: Response) -> Dict[str, Any]:
    """
    Attempt a simple Supabase connection check and return success/failure.
    """
    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "unconfigured",
            "message": "SUPABASE_URL or SUPABASE_KEY is missing.",
        }

    client = get_supabase_client()
    if client is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "failed",
            "message": "Supabase client failed to initialize.",
        }

    try:
        # Attempt a lightweight query to verify connectivity.
        # Even if the specific table doesn't exist, reaching Supabase postgrest confirms connectivity.
        client.table("_health_probe").select("*").limit(1).execute()
        return {
            "status": "ok",
            "database": "connected",
            "message": "Successfully communicated with Supabase.",
        }
    except Exception as exc:
        err_msg = str(exc)
        # Note: If PostgreSQL returns 'relation does not exist' (code 42P01 / PGRST200 / PGRST204),
        # the database server was reached successfully.
        if "relation" in err_msg.lower() or "not found" in err_msg.lower() or "pgrst" in err_msg.lower():
            return {
                "status": "ok",
                "database": "connected",
                "message": "Successfully reached Supabase (no tables created yet).",
            }

        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "disconnected",
            "message": f"Failed to connect to Supabase: {err_msg}",
        }
