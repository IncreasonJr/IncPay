"""
IncPay Services Package.

Provides database access helpers and business workflows interacting with Supabase and Paystack.
"""

from app.services.seller_service import (
    create_seller,
    get_seller,
    get_seller_by_id,
    list_sellers,
    update_seller,
    delete_seller,
    calculate_percentage_charge,
    list_banks,
    list_mobile_money_providers,
)
from app.services.coupon_service import (
    create_coupon,
    create_coupon_for_seller,
    generate_coupon_code,
    get_active_coupon_for_seller,
    get_coupon_by_code,
    list_coupons_for_seller,
    regenerate_coupon_for_seller,
    deactivate_coupon,
)
from app.services.qr_service import (
    generate_qr_png,
    generate_qr_svg,
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
from app.services import paystack_service
from app.services import qr_service
from app.services import coupon_service

__all__ = [
    # Seller service
    "create_seller",
    "get_seller",
    "get_seller_by_id",
    "list_sellers",
    "update_seller",
    "delete_seller",
    "calculate_percentage_charge",
    "list_banks",
    "list_mobile_money_providers",
    # Coupon service
    "create_coupon",
    "create_coupon_for_seller",
    "generate_coupon_code",
    "get_active_coupon_for_seller",
    "get_coupon_by_code",
    "list_coupons_for_seller",
    "regenerate_coupon_for_seller",
    "deactivate_coupon",
    "coupon_service",
    # QR service
    "qr_service",
    "generate_qr_png",
    "generate_qr_svg",
    # Transaction service
    "create_transaction",
    "get_transaction_by_reference",
    "list_transactions",
    "update_transaction_status",
    # Log service
    "log_event",
    # Paystack service
    "paystack_service",
]
