import unittest
from decimal import Decimal
from uuid import uuid4
from pydantic import ValidationError

from app.models import (
    SellerCreate,
    SellerUpdate,
    CouponCreate,
    TransactionCreate,
    TransactionStatus,
    LogCreate,
)
from app.services import (
    create_seller,
    get_seller,
    list_sellers,
    update_seller,
    delete_seller,
    create_coupon,
    get_coupon_by_code,
    list_coupons_for_seller,
    deactivate_coupon,
    create_transaction,
    get_transaction_by_reference,
    list_transactions,
    update_transaction_status,
    log_event,
)


class TestPhase1DataLayer(unittest.TestCase):
    def test_seller_model_validation(self):
        """Verify SellerCreate validates discount boundaries."""
        # Valid seller
        seller = SellerCreate(
            business_name="Ama Supermarket",
            contact_email="ama@example.com",
            contact_phone="+233201234567",
            agreed_discount=Decimal("20.00"),
            settlement_type="bank",
            settlement_bank_code="030100",
            settlement_account_number="1234567890",
            settlement_account_name="Ama Owusu",
        )
        self.assertEqual(seller.business_name, "Ama Supermarket")
        self.assertEqual(seller.agreed_discount, Decimal("20.00"))
        self.assertTrue(seller.is_active)

        # Invalid discount: <= 0
        with self.assertRaises(ValidationError):
            SellerCreate(
                business_name="Invalid",
                contact_email="bad@example.com",
                contact_phone="+233201234567",
                agreed_discount=Decimal("0.00"),
                settlement_type="bank",
                settlement_bank_code="030100",
                settlement_account_number="1234567890",
                settlement_account_name="Invalid",
            )

        # Invalid discount: >= 100
        with self.assertRaises(ValidationError):
            SellerCreate(
                business_name="Invalid",
                contact_email="bad@example.com",
                contact_phone="+233201234567",
                agreed_discount=Decimal("100.00"),
                settlement_type="bank",
                settlement_bank_code="030100",
                settlement_account_number="1234567890",
                settlement_account_name="Invalid",
            )

        # Missing contact_phone: required on SellerCreate
        with self.assertRaises(ValidationError):
            SellerCreate(
                business_name="Missing Phone",
                contact_email="seller@example.com",
                agreed_discount=Decimal("20.00"),
                settlement_type="bank",
                settlement_bank_code="030100",
                settlement_account_number="1234567890",
                settlement_account_name="Seller",
            )

    def test_coupon_model_sanitization(self):
        """Verify coupon code is sanitized to uppercase and trimmed."""
        seller_id = uuid4()
        coupon = CouponCreate(
            seller_id=seller_id,
            code="  accra-deal  ",
        )
        self.assertEqual(coupon.code, "ACCRA-DEAL")
        self.assertTrue(coupon.is_active)

    def test_transaction_split_calculation(self):
        """
        Verify payment-bridge calculation:
        Example from spec: D = 20%, listed price ₵10,000
        - Customer discount: ₵1,000 (D/2 = 10%)
        - Amount paid: ₵9,000
        - Platform cut: ₵1,000 (D/2 = 10%)
        - Seller payout: ₵8,000
        """
        split = TransactionCreate.calculate_split(
            listed_amount=Decimal("10000.00"),
            agreed_discount=Decimal("20.00"),
        )
        self.assertEqual(split["listed_amount"], Decimal("10000.00"))
        self.assertEqual(split["customer_discount_amount"], Decimal("1000.00"))
        self.assertEqual(split["amount_paid"], Decimal("9000.00"))
        self.assertEqual(split["platform_cut_amount"], Decimal("1000.00"))
        self.assertEqual(split["seller_payout_amount"], Decimal("8000.00"))

        # Invariance check: amount_paid = platform_cut + seller_payout
        self.assertEqual(
            split["amount_paid"],
            split["platform_cut_amount"] + split["seller_payout_amount"],
        )

        tx = TransactionCreate(
            seller_id=uuid4(),
            coupon_id=uuid4(),
            paystack_reference="REF_ABC_123",
            customer_email="buyer@example.com",
            **split,
        )
        self.assertEqual(tx.status, TransactionStatus.PENDING)
        self.assertEqual(tx.currency, "GHS")

    def test_transaction_imbalance_validation(self):
        """Verify that manually imbalanced amounts trigger a ValidationError."""
        with self.assertRaises(ValidationError):
            TransactionCreate(
                seller_id=uuid4(),
                coupon_id=uuid4(),
                paystack_reference="REF_BAD",
                listed_amount=Decimal("100.00"),
                customer_discount_amount=Decimal("10.00"),
                amount_paid=Decimal("90.00"),
                platform_cut_amount=Decimal("10.00"),
                seller_payout_amount=Decimal("50.00"),  # 10 + 50 = 60 != 90
            )

    def test_log_model_creation(self):
        """Verify LogCreate payload handling."""
        log = LogCreate(
            event_type="payment_initiated",
            payload={"amount": "9000.00", "currency": "GHS"},
        )
        self.assertEqual(log.event_type, "payment_initiated")
        self.assertIsNone(log.transaction_id)
        self.assertEqual(log.payload["currency"], "GHS")

    def test_services_unconfigured_client_graceful_handling(self):
        """Verify that services handle unconfigured/unreachable client gracefully without exceptions."""
        dummy_id = uuid4()

        # Seller service
        self.assertIsNone(get_seller(dummy_id))
        self.assertEqual(list_sellers(), [])
        self.assertIsNone(update_seller(dummy_id, SellerUpdate(business_name="Test")))
        self.assertFalse(delete_seller(dummy_id))

        # Coupon service
        self.assertIsNone(get_coupon_by_code("CODE"))
        self.assertEqual(list_coupons_for_seller(dummy_id), [])
        self.assertIsNone(deactivate_coupon(dummy_id))

        # Transaction service
        self.assertIsNone(get_transaction_by_reference("REF"))
        self.assertEqual(list_transactions(), [])
        self.assertIsNone(update_transaction_status("REF", TransactionStatus.SUCCESS))

        # Log service
        self.assertIsNone(log_event("test_event", payload={"test": True}))


if __name__ == "__main__":
    unittest.main()
