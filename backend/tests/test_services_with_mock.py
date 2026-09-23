import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

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
    get_seller_by_id,
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


class TestServicesWithMockSupabase(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_table = MagicMock()
        self.mock_client.table.return_value = self.mock_table

    def test_create_seller_success(self):
        now = datetime.now(timezone.utc).isoformat()
        seller_id = str(uuid4())
        mock_row = {
            "id": seller_id,
            "business_name": "Kofi Electronics",
            "contact_email": "kofi@example.com",
            "contact_phone": "+233240000000",
            "agreed_discount": "20.00",
            "settlement_type": "bank",
            "settlement_bank_code": "030100",
            "settlement_account_number": "1234567890",
            "settlement_account_name": "Kofi Owusu",
            "paystack_subaccount_code": "ACCT_123",
            "paystack_subaccount_id": "12345",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        mock_execute = MagicMock()
        mock_execute.data = [mock_row]
        self.mock_table.insert.return_value.execute.return_value = mock_execute

        mock_paystack_res = {"subaccount_code": "ACCT_123", "id": 12345}

        with patch("app.services.seller_service.get_supabase_client", return_value=self.mock_client), \
             patch("app.services.paystack_service.create_subaccount", return_value=mock_paystack_res):
            seller_in = SellerCreate(
                business_name="Kofi Electronics",
                contact_email="kofi@example.com",
                contact_phone="+233240000000",
                agreed_discount=Decimal("20.00"),
                settlement_type="bank",
                settlement_bank_code="030100",
                settlement_account_number="1234567890",
                settlement_account_name="Kofi Owusu",
            )
            result = create_seller(seller_in)
            self.assertIsNotNone(result)
            self.assertEqual(str(result.id), seller_id)
            self.assertEqual(result.business_name, "Kofi Electronics")
            self.assertEqual(result.agreed_discount, Decimal("20.00"))

    def test_get_seller_and_by_id(self):
        now = datetime.now(timezone.utc).isoformat()
        seller_id = str(uuid4())
        mock_row = {
            "id": seller_id,
            "business_name": "Kofi Electronics",
            "contact_email": "kofi@example.com",
            "contact_phone": None,
            "agreed_discount": "20.00",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        mock_execute = MagicMock()
        mock_execute.data = [mock_row]
        self.mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute

        with patch("app.services.seller_service.get_supabase_client", return_value=self.mock_client):
            seller = get_seller(seller_id)
            self.assertIsNotNone(seller)
            self.assertEqual(str(seller.id), seller_id)

            seller_alias = get_seller_by_id(seller_id)
            self.assertEqual(seller, seller_alias)

    def test_coupon_services(self):
        now = datetime.now(timezone.utc).isoformat()
        coupon_id = str(uuid4())
        seller_id = uuid4()
        mock_row = {
            "id": coupon_id,
            "seller_id": str(seller_id),
            "code": "KOFI20",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        # Create
        mock_insert = MagicMock()
        mock_insert.data = [mock_row]
        self.mock_table.insert.return_value.execute.return_value = mock_insert

        with patch("app.services.coupon_service.get_supabase_client", return_value=self.mock_client):
            c_in = CouponCreate(seller_id=seller_id, code="kofi20")
            c = create_coupon(c_in)
            self.assertIsNotNone(c)
            self.assertEqual(c.code, "KOFI20")

        # Get by code
        mock_select = MagicMock()
        mock_select.data = [mock_row]
        self.mock_table.select.return_value.eq.return_value.execute.return_value = mock_select
        with patch("app.services.coupon_service.get_supabase_client", return_value=self.mock_client):
            c_get = get_coupon_by_code("kofi20")
            self.assertIsNotNone(c_get)
            self.assertEqual(c_get.code, "KOFI20")

    def test_transaction_services(self):
        now = datetime.now(timezone.utc).isoformat()
        tx_id = str(uuid4())
        seller_id = uuid4()
        coupon_id = uuid4()

        split = TransactionCreate.calculate_split(
            listed_amount=Decimal("10000.00"),
            agreed_discount=Decimal("20.00"),
        )
        mock_row = {
            "id": tx_id,
            "seller_id": str(seller_id),
            "coupon_id": str(coupon_id),
            "paystack_reference": "T_1001",
            "currency": "GHS",
            "listed_amount": "10000.00",
            "customer_discount_amount": "1000.00",
            "amount_paid": "9000.00",
            "platform_cut_amount": "1000.00",
            "seller_payout_amount": "8000.00",
            "status": "pending",
            "customer_email": "test@buyer.com",
            "created_at": now,
            "updated_at": now,
        }

        mock_insert = MagicMock()
        mock_insert.data = [mock_row]
        self.mock_table.insert.return_value.execute.return_value = mock_insert

        with patch("app.services.transaction_service.get_supabase_client", return_value=self.mock_client):
            tx_in = TransactionCreate(
                seller_id=seller_id,
                coupon_id=coupon_id,
                paystack_reference="T_1001",
                customer_email="test@buyer.com",
                **split,
            )
            tx = create_transaction(tx_in)
            self.assertIsNotNone(tx)
            self.assertEqual(tx.paystack_reference, "T_1001")
            self.assertEqual(tx.amount_paid, Decimal("9000.00"))

    def test_log_service(self):
        now = datetime.now(timezone.utc).isoformat()
        log_id = str(uuid4())
        mock_row = {
            "id": log_id,
            "transaction_id": None,
            "event_type": "payment_initiated",
            "payload": {"gateway": "paystack"},
            "created_at": now,
        }
        mock_insert = MagicMock()
        mock_insert.data = [mock_row]
        self.mock_table.insert.return_value.execute.return_value = mock_insert

        with patch("app.services.log_service.get_supabase_client", return_value=self.mock_client):
            res = log_event("payment_initiated", payload={"gateway": "paystack"})
            self.assertIsNotNone(res)
            self.assertEqual(res.event_type, "payment_initiated")


if __name__ == "__main__":
    unittest.main()
