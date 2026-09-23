import logging
from typing import Any, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_admin
from app.models.seller import SellerCreate, SellerResponse, SellerUpdate
from app.services import seller_service
from app.services.paystack_service import PaystackError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sellers"])


@router.post(
    "/api/sellers",
    response_model=SellerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard new seller and generate Paystack subaccount",
)
def create_seller(
    seller_data: SellerCreate,
    _: Any = Depends(verify_admin),
) -> SellerResponse:
    """
    Onboards a seller:
    1. Computes platform cut: percentage_charge = D / (200 - D) * 100.
    2. Calls Paystack to create an automated split subaccount.
    3. Persists seller record in Supabase with subaccount_code.
    """
    try:
        created = seller_service.create_seller(seller_data)
        if not created:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist seller in database.",
            )
        return created
    except PaystackError as exc:
        logger.error(f"Paystack subaccount creation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paystack subaccount creation failed: {exc.message}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error onboarding seller: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error onboarding seller: {str(exc)}",
        )


@router.get(
    "/api/sellers",
    response_model=List[SellerResponse],
    summary="List all sellers",
)
def list_sellers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: bool = Query(None),
    _: Any = Depends(verify_admin),
) -> List[SellerResponse]:
    """
    List onboarded sellers with optional pagination.
    """
    return seller_service.list_sellers(limit=limit, offset=offset, is_active=is_active)


@router.get(
    "/api/sellers/{seller_id}",
    response_model=SellerResponse,
    summary="Get seller details by ID",
)
def get_seller(
    seller_id: UUID,
    _: Any = Depends(verify_admin),
) -> SellerResponse:
    """
    Retrieve details for a single seller.
    """
    seller = seller_service.get_seller(seller_id)
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller not found",
        )
    return seller


@router.put(
    "/api/sellers/{seller_id}",
    response_model=SellerResponse,
    summary="Update seller details",
)
def update_seller(
    seller_id: UUID,
    update_data: SellerUpdate,
    _: Any = Depends(verify_admin),
) -> SellerResponse:
    """
    Update seller details. If agreed_discount is modified,
    automatically updates the Paystack subaccount percentage charge.
    """
    try:
        updated = seller_service.update_seller(seller_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seller not found",
            )
        return updated
    except PaystackError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update Paystack subaccount: {exc.message}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating seller: {str(exc)}",
        )


@router.get(
    "/api/banks",
    response_model=List[Dict[str, Any]],
    summary="List Ghanaian banks from Paystack directory",
)
def get_banks(
    currency: str = Query("GHS"),
    _: Any = Depends(verify_admin),
) -> List[Dict[str, Any]]:
    """
    Returns list of Ghanaian banks from Paystack directory for settlement setup.
    """
    return seller_service.list_banks(currency=currency)


@router.get(
    "/api/mobile-money-providers",
    response_model=List[Dict[str, str]],
    summary="List supported Ghanaian Mobile Money providers",
)
def get_mobile_money_providers(
    currency: str = Query("GHS"),
    _: Any = Depends(verify_admin),
) -> List[Dict[str, str]]:
    """
    Returns supported mobile money telcos (MTN, Telecel/Vodafone, AT/AirtelTigo).
    """
    return seller_service.list_mobile_money_providers(currency=currency)
