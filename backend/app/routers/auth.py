from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.auth import verify_admin

router = APIRouter(tags=["Auth"])


@router.get("/api/auth/me", summary="Get current authenticated admin user")
@router.get("/auth/me", summary="Get current authenticated admin user alias")
def get_current_user(user: Any = Depends(verify_admin)) -> Dict[str, str]:
    """
    Returns the ID and email address of the currently authenticated admin user.
    """
    return {
        "id": str(user.id),
        "email": user.email,
    }
