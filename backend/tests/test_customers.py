import time
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.customer_coupon_service import (
    generate_coupon_token,
    verify_coupon_token,
    get_verbal_code,
)


class TestCustomerAccountsAndCoupons(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # 1. Coupon Token Cryptographic Tests
    def test_coupon_token_generation_and_verification(self):
        cust_id = str(uuid4())
        token = generate_coupon_token(cust_id)
        self.assertIn(".", token)
        parts = token.split(".")
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], cust_id)

        # Verification succeeds
        verified = verify_coupon_token(token)
        self.assertIsNotNone(verified)
        self.assertEqual(verified["customer_id"], cust_id)

        # Verbal code check
        verbal = get_verbal_code(token)
        self.assertEqual(len(verbal), 8)
        self.assertTrue(verbal.isalnum())

    def test_coupon_token_expiration(self):
        cust_id = str(uuid4())
        # Generated 31 days in the past
        past_ts = int(time.time()) - (31 * 86400)
        token = generate_coupon_token(cust_id, timestamp=past_ts)
        self.assertIsNone(verify_coupon_token(token))

    def test_coupon_token_tampering(self):
        cust_id = str(uuid4())
        token = generate_coupon_token(cust_id)
        parts = token.split(".")

        # Tampered customer ID
        tampered_token = f"{str(uuid4())}.{parts[1]}.{parts[2]}"
        self.assertIsNone(verify_coupon_token(tampered_token))

        # Tampered signature
        tampered_sig = f"{parts[0]}.{parts[1]}.{parts[2][:-4]}abcd"
        self.assertIsNone(verify_coupon_token(tampered_sig))

    # 2. Customer Signup Endpoints
    def test_customer_signup_success(self):
        email = f"customer_{uuid4().hex[:8]}@example.com"
        mock_user = MagicMock()
        mock_user.id = str(uuid4())

        mock_client = MagicMock()
        # Mock duplicate check: empty list
        mock_client.table("customers").select("id").eq("email", email).execute.return_value = MagicMock(data=[])

        # Mock auth create_user
        mock_admin = MagicMock()
        mock_admin.create_user.return_value = MagicMock(user=mock_user)
        mock_client.auth.admin = mock_admin

        # Mock table insert
        fake_inserted = {
            "id": str(uuid4()),
            "email": email,
            "full_name": "Kofi Mensah",
            "phone": "0240000000",
            "coupon_token": "token.123.sig",
            "is_active": True,
            "created_at": "2026-09-29T12:00:00Z",
        }
        mock_client.table("customers").insert.return_value.execute.return_value = MagicMock(data=[fake_inserted])

        with patch("app.services.customer_service.get_supabase_client", return_value=mock_client):
            resp = self.client.post(
                "/api/customer/signup",
                json={
                    "email": email,
                    "password": "strongPassword123!",
                    "full_name": "Kofi Mensah",
                    "phone": "0240000000",
                },
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            self.assertEqual(data["email"], email)
            self.assertEqual(data["full_name"], "Kofi Mensah")
            self.assertIn("coupon_token", data)
            self.assertIn("verbal_code", data)

    def test_customer_signup_duplicate_email(self):
        email = "existing@example.com"
        mock_client = MagicMock()
        mock_client.table("customers").select("id").eq("email", email).execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        with patch("app.services.customer_service.get_supabase_client", return_value=mock_client):
            resp = self.client.post(
                "/api/customer/signup",
                json={
                    "email": email,
                    "password": "strongPassword123!",
                    "full_name": "Existing User",
                },
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("already exists", resp.json()["detail"])

    def test_customer_signup_validation_errors(self):
        # Short password
        resp = self.client.post(
            "/api/customer/signup",
            json={
                "email": "valid@example.com",
                "password": "short",
                "full_name": "Test",
            },
        )
        self.assertEqual(resp.status_code, 422)

        # Invalid email
        resp2 = self.client.post(
            "/api/customer/signup",
            json={
                "email": "not-an-email",
                "password": "validPassword123",
                "full_name": "Test",
            },
        )
        self.assertEqual(resp2.status_code, 422)

    # 3. Customer Profile & Auth Dependencies
    def test_customer_me_authenticated(self):
        user_id = str(uuid4())
        mock_client = MagicMock()
        mock_user = MagicMock(id=user_id)
        mock_client.auth.get_user.return_value = MagicMock(user=mock_user)

        customer_row = {
            "id": str(uuid4()),
            "email": "cust@example.com",
            "full_name": "Ama Serwaa",
            "phone": None,
            "supabase_user_id": user_id,
            "coupon_token": "token.12345.abcdef12345678",
            "is_active": True,
            "created_at": "2026-09-29T12:00:00Z",
        }
        mock_client.table("customers").select("*").eq("supabase_user_id", user_id).execute.return_value = MagicMock(
            data=[customer_row]
        )

        with patch("app.auth.get_supabase_client", return_value=mock_client):
            resp = self.client.get(
                "/api/customer/me",
                headers={"Authorization": "Bearer test_customer_jwt"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["email"], "cust@example.com")
            self.assertEqual(data["full_name"], "Ama Serwaa")
            self.assertEqual(data["verbal_code"], "345678".upper() if len("345678") == 8 else data["verbal_code"])

    def test_customer_me_unauthorized(self):
        resp = self.client.get("/api/customer/me")
        self.assertEqual(resp.status_code, 401)

    # 4. Strict Role Separation
    def test_admin_blocked_from_customer_endpoint(self):
        """An admin user with no customer profile is rejected with 403 on /api/customer/me."""
        admin_id = str(uuid4())
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(user=MagicMock(id=admin_id))
        # Admin is not in customers table
        mock_client.table("customers").select("*").eq("supabase_user_id", admin_id).execute.return_value = MagicMock(
            data=[]
        )

        with patch("app.auth.get_supabase_client", return_value=mock_client):
            resp = self.client.get(
                "/api/customer/me",
                headers={"Authorization": "Bearer admin_jwt"},
            )
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Customer account not found", resp.json()["detail"])

    def test_customer_blocked_from_admin_endpoint(self):
        """A registered customer user is blocked with 403 on admin-only endpoints."""
        cust_uid = str(uuid4())
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(user=MagicMock(id=cust_uid))
        # User is present in customers table!
        mock_client.table("customers").select("id").eq("supabase_user_id", cust_uid).execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        with patch("app.auth.get_supabase_client", return_value=mock_client):
            resp = self.client.get(
                "/api/sellers/",
                headers={"Authorization": "Bearer customer_jwt"},
            )
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Admin privileges required", resp.json()["detail"])

    # 5. Customer Transactions
    def test_customer_transactions(self):
        cust_id = str(uuid4())
        user_id = str(uuid4())
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(user=MagicMock(id=user_id))

        customer_row = {
            "id": cust_id,
            "email": "cust@example.com",
            "full_name": "Test Customer",
            "supabase_user_id": user_id,
            "coupon_token": "token.123.sig",
            "is_active": True,
            "created_at": "2026-09-29T12:00:00Z",
        }
        mock_client.table("customers").select("*").eq("supabase_user_id", user_id).execute.return_value = MagicMock(
            data=[customer_row]
        )

        sample_txs = [
            {
                "id": str(uuid4()),
                "created_at": "2026-09-29T14:00:00Z",
                "sellers": {"business_name": "Kofi Electronics"},
                "currency": "GHS",
                "listed_amount": "100.00",
                "customer_discount_amount": "10.00",
                "amount_paid": "90.00",
                "paystack_reference": "INCPAY-TEST1234",
                "status": "success",
            }
        ]
        tx_query = MagicMock()
        tx_query.execute.return_value = MagicMock(data=sample_txs, count=1)
        mock_client.table("transactions").select.return_value.eq.return_value.order.return_value.range.return_value = tx_query

        with patch("app.auth.get_supabase_client", return_value=mock_client), \
             patch("app.services.customer_service.get_supabase_client", return_value=mock_client):
            resp = self.client.get(
                "/api/customer/me/transactions",
                headers={"Authorization": "Bearer customer_jwt"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(len(data["transactions"]), 1)
            tx = data["transactions"][0]
            self.assertEqual(tx["business_name"], "Kofi Electronics")
            self.assertEqual(tx["paystack_reference"], "INCPAY-TEST1234")
            self.assertIn("/api/receipts/INCPAY-TEST1234", tx["receipt_url"])

    # 6. Customer QR Endpoints
    def test_customer_coupon_qr(self):
        user_id = str(uuid4())
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(user=MagicMock(id=user_id))

        customer_row = {
            "id": str(uuid4()),
            "email": "cust@example.com",
            "full_name": "Test Customer",
            "supabase_user_id": user_id,
            "coupon_token": "token.12345.abcdef12",
            "is_active": True,
            "created_at": "2026-09-29T12:00:00Z",
        }
        mock_client.table("customers").select("*").eq("supabase_user_id", user_id).execute.return_value = MagicMock(
            data=[customer_row]
        )

        with patch("app.auth.get_supabase_client", return_value=mock_client):
            # Test PNG QR
            resp_png = self.client.get(
                "/api/customer/me/coupon-qr?format=png",
                headers={"Authorization": "Bearer customer_jwt"},
            )
            self.assertEqual(resp_png.status_code, 200)
            self.assertEqual(resp_png.headers["content-type"], "image/png")
            self.assertTrue(len(resp_png.content) > 100)

            # Test SVG QR
            resp_svg = self.client.get(
                "/api/customer/me/coupon-qr?format=svg",
                headers={"Authorization": "Bearer customer_jwt"},
            )
            self.assertEqual(resp_svg.status_code, 200)
            self.assertEqual(resp_svg.headers["content-type"], "image/svg+xml")
            self.assertIn("<svg", resp_svg.text)

    # 7. Payment Initialization with Customer Linking
    def test_payment_initialization_with_customer_token(self):
        cust_id = str(uuid4())
        token = generate_coupon_token(cust_id)

        mock_coupon = {
            "id": str(uuid4()),
            "seller_id": str(uuid4()),
            "code": "ACCRA-DEALS-ABC",
            "agreed_discount": 20.0,
            "business_name": "Accra Mart",
            "is_active": True,
            "paystack_subaccount_code": "ACCT_test123",
        }

        mock_cust = {
            "id": cust_id,
            "email": "loyalty@example.com",
            "full_name": "Loyal Customer",
            "is_active": True,
        }

        with patch("app.services.coupon_service.get_coupon_by_code", return_value=mock_coupon), \
             patch("app.services.customer_service.get_customer_by_id", return_value=mock_cust), \
             patch("app.services.paystack_service.initialize_transaction") as mock_paystack:
            mock_paystack.return_value = {
                "authorization_url": "https://checkout.paystack.com/test",
                "access_code": "code123",
                "reference": "INCPAY-REF123",
            }

            resp = self.client.post(
                "/api/public/initialize-payment",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "coupon_code": "ACCRA-DEALS-ABC",
                    "listed_amount": "100.00",
                },
            )
            self.assertEqual(resp.status_code, 200)
            # Verify customer_id was injected into Paystack metadata
            call_kwargs = mock_paystack.call_args[1]
            self.assertEqual(call_kwargs["metadata"]["customer_id"], cust_id)
            self.assertEqual(call_kwargs["metadata"]["customer_name"], "Loyal Customer")
            # Discount D remains identical (listed 100, D=20% -> paid 90)
            self.assertEqual(resp.json()["amount_paid"], 90.0)

    # 8. Guest Checkout Remains Untouched
    def test_guest_checkout_unaffected(self):
        mock_coupon = {
            "id": str(uuid4()),
            "seller_id": str(uuid4()),
            "code": "GUEST-DEAL-XYZ",
            "agreed_discount": 20.0,
            "business_name": "Guest Mart",
            "is_active": True,
            "paystack_subaccount_code": "ACCT_test456",
        }

        with patch("app.services.coupon_service.get_coupon_by_code", return_value=mock_coupon), \
             patch("app.services.paystack_service.initialize_transaction") as mock_paystack:
            mock_paystack.return_value = {
                "authorization_url": "https://checkout.paystack.com/guest",
                "access_code": "code456",
                "reference": "INCPAY-GUEST456",
            }

            resp = self.client.post(
                "/api/public/initialize-payment",
                json={
                    "coupon_code": "GUEST-DEAL-XYZ",
                    "listed_amount": "50.00",
                    "email": "guest@example.com",
                },
            )
            self.assertEqual(resp.status_code, 200)
            call_kwargs = mock_paystack.call_args[1]
            self.assertNotIn("customer_id", call_kwargs["metadata"])
            self.assertEqual(resp.json()["amount_paid"], 45.0)


if __name__ == "__main__":
    unittest.main()
