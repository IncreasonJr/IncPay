import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.services.coupon_service import CouponDetails


class TestPublicPayments(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_get_public_coupon_success(self, mock_get_coupon):
        """
        Public endpoint returns safe merchant metadata and discounts without authentication.
        Ensures no sensitive data (emails, phones, subaccount codes, UUIDs) are leaked.
        """
        mock_get_coupon.return_value = CouponDetails({
            "id": str(uuid4()),
            "seller_id": str(uuid4()),
            "code": "KOFI-TEST-123456",
            "business_name": "Kofi Fashions Ltd",
            "agreed_discount": Decimal("20.00"),
            "paystack_subaccount_code": "ACCT_test123",
            "contact_email": "kofi@secret.com",
            "contact_phone": "+233201234567",
            "is_active": True,
        })

        # No Authorization header
        response = self.client.get("/api/public/coupon/KOFI-TEST-123456")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["business_name"], "Kofi Fashions Ltd")
        self.assertEqual(data["agreed_discount"], 20.0)
        self.assertEqual(data["customer_discount"], 10.0)
        self.assertTrue(data["is_active"])

        # Sensitive field protection check
        self.assertNotIn("contact_email", data)
        self.assertNotIn("contact_phone", data)
        self.assertNotIn("paystack_subaccount_code", data)
        self.assertNotIn("seller_id", data)
        self.assertNotIn("id", data)

    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_get_public_coupon_not_found_or_inactive(self, mock_get_coupon):
        """Returns 404 for invalid or inactive coupons."""
        # Non-existent
        mock_get_coupon.return_value = None
        resp_404 = self.client.get("/api/public/coupon/NONEXISTENT")
        self.assertEqual(resp_404.status_code, 404)

        # Inactive
        mock_get_coupon.return_value = CouponDetails({
            "code": "INACTIVE-COUPON",
            "is_active": False,
            "business_name": "Closed Shop",
            "agreed_discount": Decimal("10.00"),
        })
        resp_inactive = self.client.get("/api/public/coupon/INACTIVE-COUPON")
        self.assertEqual(resp_inactive.status_code, 404)

    @patch("app.services.paystack_service.initialize_transaction")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_initialize_payment_server_calculation(
        self,
        mock_get_coupon,
        mock_paystack_init,
    ):
        """
        Verify server recalculates customer discount strictly server-side:
        Listed amount ₵100, D=20% -> Customer discount D/2 = 10% (₵10.00) -> Customer pays ₵90.00.
        Paystack is called with 90.00 GHS (9000 pesewas).
        """
        mock_get_coupon.return_value = CouponDetails({
            "code": "ACCRA-DEALS-ABC123",
            "seller_id": str(uuid4()),
            "business_name": "Accra Deals",
            "agreed_discount": Decimal("20.00"),
            "paystack_subaccount_code": "ACCT_test_sub_99",
            "is_active": True,
        })

        mock_paystack_init.return_value = {
            "authorization_url": "https://checkout.paystack.com/access123",
            "access_code": "access123",
            "reference": "INCPAY-REF-TEST",
        }

        payload = {
            "coupon_code": "ACCRA-DEALS-ABC123",
            "listed_amount": 100.00,
            "email": "customer@example.com",
        }

        # No Authorization header required
        response = self.client.post("/api/public/initialize-payment", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["authorization_url"], "https://checkout.paystack.com/access123")
        self.assertEqual(data["access_code"], "access123")
        self.assertEqual(data["amount_paid"], 90.00)
        self.assertEqual(data["listed_amount"], 100.00)
        self.assertEqual(data["discount_amount"], 10.00)

        # Verify arguments passed to paystack initialize_transaction
        mock_paystack_init.assert_called_once()
        call_kwargs = mock_paystack_init.call_args.kwargs
        self.assertEqual(call_kwargs["email"], "customer@example.com")
        self.assertEqual(call_kwargs["amount_ghs"], Decimal("90.00"))
        self.assertEqual(call_kwargs["subaccount_code"], "ACCT_test_sub_99")
        self.assertTrue(call_kwargs["reference"].startswith("INCPAY-"))
        self.assertEqual(call_kwargs["metadata"]["coupon_code"], "ACCRA-DEALS-ABC123")

    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_initialize_payment_minimum_amount_validation(self, mock_get_coupon):
        """Listed amount below MIN_PAYMENT_AMOUNT (1.00) returns 400."""
        payload = {
            "coupon_code": "ACCRA-DEALS-ABC123",
            "listed_amount": 0.50,
        }
        response = self.client.post("/api/public/initialize-payment", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Minimum payment amount", response.json()["detail"])

    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_initialize_payment_missing_subaccount(self, mock_get_coupon):
        """Seller without configured paystack_subaccount_code returns 400."""
        mock_get_coupon.return_value = CouponDetails({
            "code": "ACCRA-DEALS-ABC123",
            "business_name": "Accra Deals",
            "agreed_discount": Decimal("20.00"),
            "paystack_subaccount_code": None,
            "is_active": True,
        })

        payload = {
            "coupon_code": "ACCRA-DEALS-ABC123",
            "listed_amount": 50.00,
        }
        response = self.client.post("/api/public/initialize-payment", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("subaccount is not configured", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
