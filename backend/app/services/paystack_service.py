import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"

# Static list of supported Ghanaian Mobile Money providers
GHANA_MOBILE_MONEY_PROVIDERS: List[Dict[str, str]] = [
    {"name": "MTN Mobile Money", "code": "MTN", "type": "mobile_money"},
    {"name": "Telecel / Vodafone Cash", "code": "VOD", "type": "mobile_money"},
    {"name": "AT / AirtelTigo Money", "code": "ATL", "type": "mobile_money"},
]

# Fallback directory of top Ghanaian banks in case of network timeouts
FALLBACK_GHANA_BANKS: List[Dict[str, Any]] = [
    {"name": "Absa Bank Ghana Ltd", "code": "030100", "type": "ghipss"},
    {"name": "Access Bank", "code": "280100", "type": "ghipss"},
    {"name": "Agricultural Development Bank", "code": "080100", "type": "ghipss"},
    {"name": "Bank of Africa Ghana", "code": "140100", "type": "ghipss"},
    {"name": "CalBank", "code": "130100", "type": "ghipss"},
    {"name": "Consolidated Bank Ghana", "code": "340100", "type": "ghipss"},
    {"name": "Ecobank Ghana", "code": "130100", "type": "ghipss"},
    {"name": "FBNBank Ghana", "code": "190100", "type": "ghipss"},
    {"name": "Fidelity Bank Ghana", "code": "240100", "type": "ghipss"},
    {"name": "First Atlantic Bank", "code": "170100", "type": "ghipss"},
    {"name": "First National Bank Ghana", "code": "330100", "type": "ghipss"},
    {"name": "GCB Bank Limited", "code": "040100", "type": "ghipss"},
    {"name": "Guaranty Trust Bank (Ghana) Ltd", "code": "230100", "type": "ghipss"},
    {"name": "National Investment Bank", "code": "050100", "type": "ghipss"},
    {"name": "Prudential Bank", "code": "180100", "type": "ghipss"},
    {"name": "Republic Bank (GH) Limited", "code": "110100", "type": "ghipss"},
    {"name": "Societe Generale Ghana", "code": "090100", "type": "ghipss"},
    {"name": "Stanbic Bank Ghana Ltd", "code": "190100", "type": "ghipss"},
    {"name": "Standard Chartered Bank", "code": "020100", "type": "ghipss"},
    {"name": "United Bank for Africa Ghana", "code": "060100", "type": "ghipss"},
    {"name": "Universal Merchant Bank", "code": "070100", "type": "ghipss"},
    {"name": "Zenith Bank Ghana", "code": "120100", "type": "ghipss"},
]


class PaystackError(Exception):
    """Exception raised when a Paystack API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_headers() -> Dict[str, str]:
    """Build Authorization headers using Paystack secret key."""
    settings = get_settings()
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        logger.error("PAYSTACK_SECRET_KEY is not configured in settings.")
        raise PaystackError("PAYSTACK_SECRET_KEY is missing from environment.")

    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }


def create_subaccount(
    business_name: str,
    settlement_bank: str,
    account_number: str,
    percentage_charge: float,
    primary_contact_email: Optional[str] = None,
    primary_contact_name: Optional[str] = None,
    primary_contact_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Paystack Subaccount for automated split settlement in GHS.
    percentage_charge is IncPay platform's cut: D / (200 - D) * 100.
    """
    url = f"{PAYSTACK_BASE_URL}/subaccount"
    headers = _get_headers()

    payload: Dict[str, Any] = {
        "business_name": business_name,
        "settlement_bank": settlement_bank,
        "account_number": account_number,
        "percentage_charge": round(percentage_charge, 2),
    }
    if primary_contact_email:
        payload["primary_contact_email"] = primary_contact_email
    if primary_contact_name:
        payload["primary_contact_name"] = primary_contact_name
    if primary_contact_phone:
        payload["primary_contact_phone"] = primary_contact_phone

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=headers, json=payload)

        data = response.json()
        if response.is_success and data.get("status") is True:
            return data["data"]

        error_msg = data.get("message", "Paystack subaccount creation failed.")
        logger.error(f"Paystack subaccount error ({response.status_code}): {error_msg}")
        raise PaystackError(error_msg, status_code=response.status_code)

    except httpx.RequestError as exc:
        logger.error(f"HTTP connection error contacting Paystack: {exc}")
        raise PaystackError(f"Network error contacting Paystack: {exc}")
    except PaystackError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in Paystack subaccount creation: {exc}")
        raise PaystackError(f"Unexpected Paystack error: {exc}")


def update_subaccount(
    subaccount_code: str,
    percentage_charge: Optional[float] = None,
    business_name: Optional[str] = None,
    settlement_bank: Optional[str] = None,
    account_number: Optional[str] = None,
    primary_contact_email: Optional[str] = None,
    primary_contact_name: Optional[str] = None,
    primary_contact_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing Paystack Subaccount (e.g. updating percentage_charge on discount change).
    """
    url = f"{PAYSTACK_BASE_URL}/subaccount/{subaccount_code}"
    headers = _get_headers()

    payload: Dict[str, Any] = {}
    if percentage_charge is not None:
        payload["percentage_charge"] = round(percentage_charge, 2)
    if business_name is not None:
        payload["business_name"] = business_name
    if settlement_bank is not None:
        payload["settlement_bank"] = settlement_bank
    if account_number is not None:
        payload["account_number"] = account_number
    if primary_contact_email is not None:
        payload["primary_contact_email"] = primary_contact_email
    if primary_contact_name is not None:
        payload["primary_contact_name"] = primary_contact_name
    if primary_contact_phone is not None:
        payload["primary_contact_phone"] = primary_contact_phone

    if not payload:
        return {}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.put(url, headers=headers, json=payload)

        data = response.json()
        if response.is_success and data.get("status") is True:
            return data["data"]

        error_msg = data.get("message", "Paystack subaccount update failed.")
        logger.error(f"Paystack subaccount update error: {error_msg}")
        raise PaystackError(error_msg, status_code=response.status_code)

    except httpx.RequestError as exc:
        logger.error(f"HTTP connection error updating Paystack subaccount: {exc}")
        raise PaystackError(f"Network error contacting Paystack: {exc}")
    except PaystackError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error updating Paystack subaccount: {exc}")
        raise PaystackError(f"Unexpected Paystack error: {exc}")


def list_banks(currency: str = "GHS") -> List[Dict[str, Any]]:
    """
    Fetch Ghanaian banks from Paystack directory.
    Falls back to curated directory on network/API failure.
    """
    url = f"{PAYSTACK_BASE_URL}/bank?currency={currency}"
    try:
        headers = _get_headers()
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)

        if response.is_success:
            data = response.json()
            if data.get("status") is True and data.get("data"):
                return data["data"]

        logger.warning("Paystack bank endpoint returned non-success, using fallback directory.")
        return FALLBACK_GHANA_BANKS
    except Exception as exc:
        logger.warning(f"Failed to fetch live banks from Paystack ({exc}). Using fallback directory.")
        return FALLBACK_GHANA_BANKS


def list_mobile_money_providers(currency: str = "GHS") -> List[Dict[str, str]]:
    """
    Return supported Ghanaian Mobile Money providers (MTN, Telecel/Vodafone, AT/AirtelTigo).
    """
    return GHANA_MOBILE_MONEY_PROVIDERS
