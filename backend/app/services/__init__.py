"""
IncPay Services Package.

Provides database access helpers and business workflows interacting with Supabase.
"""

from app.services.seller_service import (
    create_seller,
    get_seller,
    get_seller_by_id,
    list_sellers,
    update_seller,
    delete_seller,
)
from app.services.coupon_service import (
    create_coupon,
    get_coupon_by_code,
    list_coupons_for_seller,
    deactivate_coupon,
)
from app.services.transaction_service import (
    create_transaction,
    get_transaction_by_reference,
    list_transactions,
    update_transaction_status,
)
from app.services.log_service import (
    log_event,
)

__all__ = [
    # Seller service
    "create_seller",
    "get_seller",
    "get_seller_by_id",
    "list_sellers",
    "update_seller",
    "delete_seller",
    # Coupon service
    "create_coupon",
    "get_coupon_by_code",
    "list_coupons_for_seller",
    "deactivate_coupon",
    # Transaction service
    "create_transaction",
    "get_transaction_by_reference",
    "list_transactions",
    "update_transaction_status",
    # Log service
    "log_event",
]
