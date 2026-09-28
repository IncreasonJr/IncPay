import hashlib
import hmac
import json
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.limiter import limiter
from app.main import app
from app.models.coupon import CouponResponse
from app.models.seller import SellerResponse
from app.models.transaction import TransactionResponse, TransactionStatus
from app.services.paystack_service import PaystackError


class TestEdgeCasesAndSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        limiter.reset()
        self.settings = get_settings()

    def tearDown(self):
        limiter.reset()

    # =========================================================================
    # 1.1 COUPONS EDGE CASES
    # =========================================================================

    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_inactive_coupon_returns_404(self, mock_get_coupon):
        """Inactive coupon returns 404 with 'This coupon is no longer valid'."""
        mock_get_coupon.return_value = {
            "coupon_code": "INACTIVE-01",
            "is_active": False,
            "seller_id": str(uuid4()),
            "agreed_discount": 20.0,
            "business_name": "Closed Shop",
        }
        response = self.client.get("/api/public/coupon/INACTIVE-01")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "This coupon is no longer valid")

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_inactive_seller_returns_404(self, mock_get_coupon, mock_get_seller):
        """Active coupon with inactive seller returns 404 'This coupon is no longer valid'."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "SHOP-DEACT-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "business_name": "Suspended Shop",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = False
        mock_get_seller.return_value = mock_seller

        response = self.client.get("/api/public/coupon/SHOP-DEACT-01")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "This coupon is no longer valid")

    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_malformed_coupon_code_rejected_immediately(self, mock_get_coupon):
        """Malformed coupon codes (spaces, script tags, special characters, too long) 404 without DB call."""
        malformed_codes = [
            "<script>alert(1)</script>",
            "CODE WITH SPACES",
            "TOOLONG" + "A" * 35,
            "SH",  # too short (< 4)
            "BAD;DROP TABLE;",
            "CODE@#$%",
        ]
        for code in malformed_codes:
            response = self.client.get(f"/api/public/coupon/{code}")
            self.assertEqual(response.status_code, 404, f"Failed for code: {code}")
            mock_get_coupon.assert_not_called()

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_coupon_case_insensitivity(self, mock_get_coupon, mock_get_seller):
        """Coupon code is normalized to uppercase for case-insensitive lookup."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "ACCRA-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "business_name": "Accra Mart",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_get_seller.return_value = mock_seller

        response = self.client.get("/api/public/coupon/accra-01")
        self.assertEqual(response.status_code, 200)
        mock_get_coupon.assert_called_with("ACCRA-01")
        data = response.json()
        self.assertEqual(data["business_name"], "Accra Mart")
        self.assertEqual(data["customer_discount"], 10.0)

    # =========================================================================
    # 1.2 PAYMENT INITIALIZATION EDGE CASES
    # =========================================================================

    def test_listed_amount_zero_or_negative(self):
        """listed_amount <= 0 returns 400 Bad Request."""
        for amount in [0.0, -5.0, -0.01]:
            response = self.client.post(
                "/api/public/initialize-payment",
                json={"coupon_code": "VALID-01", "listed_amount": amount},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("greater than zero", response.json()["detail"])

    def test_listed_amount_below_minimum(self):
        """listed_amount below MIN_PAYMENT_AMOUNT (₵1.00) returns 400."""
        response = self.client.post(
            "/api/public/initialize-payment",
            json={"coupon_code": "VALID-01", "listed_amount": 0.50},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(f"Minimum payment amount is ₵{self.settings.MIN_PAYMENT_AMOUNT:.2f}", response.json()["detail"])

    def test_listed_amount_above_maximum(self):
        """listed_amount above MAX_PAYMENT_AMOUNT (₵50,000.00) returns 400."""
        response = self.client.post(
            "/api/public/initialize-payment",
            json={"coupon_code": "VALID-01", "listed_amount": 60000.00},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum payment amount is", response.json()["detail"])

    @patch("app.services.paystack_service.initialize_transaction")
    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_listed_amount_rounded_half_up(self, mock_get_coupon, mock_get_seller, mock_paystack_init):
        """listed_amount with 3+ decimals is rounded to 2 decimal places using ROUND_HALF_UP."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "ROUND-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "paystack_subaccount_code": "ACCT_ROUND123",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_seller.paystack_subaccount_code = "ACCT_ROUND123"
        mock_get_seller.return_value = mock_seller

        mock_paystack_init.return_value = {
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "acc_123",
            "reference": "INCPAY-ROUNDED-REF",
        }

        # 85.555 -> rounds to 85.56. With 20% discount (10% cust cut = 8.56), amount_paid = 77.00
        response = self.client.post(
            "/api/public/initialize-payment",
            json={"coupon_code": "ROUND-01", "listed_amount": 85.555},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["listed_amount"], 85.56)

        # Check call to paystack service with Decimal
        called_args = mock_paystack_init.call_args[1]
        self.assertEqual(called_args["amount_ghs"], Decimal("77.00"))

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_missing_subaccount_returns_400(self, mock_get_coupon, mock_get_seller):
        """Missing seller subaccount returns 400 'Seller is not configured for payments.'."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "NOSUB-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "paystack_subaccount_code": None,
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_seller.paystack_subaccount_code = None
        mock_get_seller.return_value = mock_seller

        response = self.client.post(
            "/api/public/initialize-payment",
            json={"coupon_code": "NOSUB-01", "listed_amount": 100.0},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Seller is not configured for payments.")

    @patch("app.services.log_service.log_event")
    @patch("app.services.paystack_service.initialize_transaction")
    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_paystack_init_failure_logs_and_returns_400(
        self, mock_get_coupon, mock_get_seller, mock_paystack_init, mock_log_event
    ):
        """Paystack API failure returns sanitized 400 error and logs to transaction_logs."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "FAIL-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "paystack_subaccount_code": "ACCT_ERR123",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_seller.paystack_subaccount_code = "ACCT_ERR123"
        mock_get_seller.return_value = mock_seller

        mock_paystack_init.side_effect = PaystackError("Integration keys disabled", status_code=400)

        response = self.client.post(
            "/api/public/initialize-payment",
            json={"coupon_code": "FAIL-01", "listed_amount": 100.0},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Payment initialization failed", response.json()["detail"])
        mock_log_event.assert_called_once()
        self.assertEqual(mock_log_event.call_args[1]["event"], "payment_initialization_failed")

    # =========================================================================
    # 1.3 WEBHOOKS EDGE CASES
    # =========================================================================

    def _sign_payload(self, body_bytes: bytes) -> str:
        secret = self.settings.PAYSTACK_SECRET_KEY.encode("utf-8")
        return hmac.new(secret, body_bytes, hashlib.sha512).hexdigest()

    @patch("app.services.email_service.send_receipt_email")
    @patch("app.services.transaction_service.create_transaction")
    @patch("app.services.transaction_service.get_transaction_by_reference")
    def test_webhook_idempotency_no_duplicate_no_receipt_resend(
        self, mock_get_tx, mock_create_tx, mock_send_email
    ):
        """Duplicate webhook for already completed transaction returns 200 without duplicate row or email."""
        existing_tx = TransactionResponse(
            id=uuid4(),
            seller_id=uuid4(),
            coupon_id=uuid4(),
            paystack_reference="INCPAY-IDEM-01",
            currency="GHS",
            listed_amount=Decimal("100.00"),
            customer_discount_amount=Decimal("10.00"),
            amount_paid=Decimal("90.00"),
            platform_cut_amount=Decimal("10.00"),
            seller_payout_amount=Decimal("80.00"),
            status=TransactionStatus.SUCCESS,
            customer_email="kofi@example.com",
            created_at="2026-09-28T12:00:00Z",
            updated_at="2026-09-28T12:00:00Z",
        )
        mock_get_tx.return_value = existing_tx

        payload = {
            "event": "charge.success",
            "data": {
                "reference": "INCPAY-IDEM-01",
                "amount": 9000,
                "status": "success",
                "customer": {"email": "kofi@example.com"},
            },
        }
        body = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(body)

        response = self.client.post(
            "/api/webhooks/paystack",
            data=body,
            headers={"x-paystack-signature": sig, "content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        mock_create_tx.assert_not_called()
        mock_send_email.assert_not_called()

    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.get_transaction_by_reference")
    def test_webhook_amount_discrepancy_alert_logged(self, mock_get_tx, mock_log_event):
        """Webhook with mismatched amount logs payment_amount_discrepancy and avoids silent reconciliation."""
        existing_tx = TransactionResponse(
            id=uuid4(),
            seller_id=uuid4(),
            coupon_id=uuid4(),
            paystack_reference="INCPAY-DISC-01",
            currency="GHS",
            listed_amount=Decimal("100.00"),
            customer_discount_amount=Decimal("10.00"),
            amount_paid=Decimal("90.00"),
            platform_cut_amount=Decimal("10.00"),
            seller_payout_amount=Decimal("80.00"),
            status=TransactionStatus.PENDING,
            customer_email="user@example.com",
            created_at="2026-09-28T12:00:00Z",
            updated_at="2026-09-28T12:00:00Z",
        )
        mock_get_tx.return_value = existing_tx

        # Payload says customer paid 80 GHS (8000 pesewas) instead of expected 90 GHS
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "INCPAY-DISC-01",
                "amount": 8000,
                "status": "success",
            },
        }
        body = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(body)

        response = self.client.post(
            "/api/webhooks/paystack",
            data=body,
            headers={"x-paystack-signature": sig, "content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)

        # Discrepancy logged
        discrepancy_call = next(
            (c for c in mock_log_event.call_args_list if c[1].get("event") == "payment_amount_discrepancy"),
            None,
        )
        self.assertIsNotNone(discrepancy_call)
        self.assertEqual(discrepancy_call[1]["payload"]["expected_amount"], "90.00")
        self.assertEqual(discrepancy_call[1]["payload"]["received_amount"], "80.00")

    @patch("app.services.log_service.log_event")
    def test_webhook_invalid_signature_logged_and_401(self, mock_log_event):
        """Invalid webhook signature returns 401 and logs webhook_invalid_signature."""
        body = b'{"event": "charge.success"}'
        response = self.client.post(
            "/api/webhooks/paystack",
            data=body,
            headers={"x-paystack-signature": "bad_sig_hex_123", "content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid signature")
        mock_log_event.assert_called_once()
        self.assertEqual(mock_log_event.call_args[1]["event"], "webhook_invalid_signature")

    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.get_transaction_by_reference")
    def test_webhook_refund_event_logged_gracefully(self, mock_get_tx, mock_log_event):
        """Refund events (e.g. refund.processed) are logged without altering transaction or crashing."""
        tx_id = uuid4()
        existing_tx = TransactionResponse(
            id=tx_id,
            seller_id=uuid4(),
            coupon_id=uuid4(),
            paystack_reference="INCPAY-REFUND-01",
            currency="GHS",
            listed_amount=Decimal("100.00"),
            customer_discount_amount=Decimal("10.00"),
            amount_paid=Decimal("90.00"),
            platform_cut_amount=Decimal("10.00"),
            seller_payout_amount=Decimal("80.00"),
            status=TransactionStatus.SUCCESS,
            created_at="2026-09-28T12:00:00Z",
            updated_at="2026-09-28T12:00:00Z",
        )
        mock_get_tx.return_value = existing_tx

        payload = {
            "event": "refund.processed",
            "data": {
                "reference": "INCPAY-REFUND-01",
                "amount": 9000,
                "refunded_amount": 9000,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(body)

        response = self.client.post(
            "/api/webhooks/paystack",
            data=body,
            headers={"x-paystack-signature": sig, "content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)

        refund_call = next(
            (c for c in mock_log_event.call_args_list if c[1].get("event") == "refund.processed"),
            None,
        )
        self.assertIsNotNone(refund_call)
        self.assertEqual(refund_call[1]["transaction_id"], tx_id)

    # =========================================================================
    # 1.4 RECEIPTS EDGE CASES
    # =========================================================================

    @patch("app.services.email_service.send_receipt_email")
    @patch("app.services.transaction_service.create_transaction")
    def test_receipt_missing_or_noreply_email_skipped(self, mock_create_tx, mock_send_email):
        """Missing or placeholder noreply@incpay.app email skips receipt sending cleanly."""
        for email in [None, "", "noreply@incpay.app", "NOREPLY@incpay.app"]:
            payload = {
                "event": "charge.success",
                "data": {
                    "reference": f"INCPAY-NOREPLY-{uuid4().hex[:6]}",
                    "amount": 9000,
                    "status": "success",
                    "customer": {"email": email} if email else {},
                    "metadata": {"listed_amount": 100.0, "agreed_discount": 20.0},
                },
            }
            body = json.dumps(payload).encode("utf-8")
            sig = self._sign_payload(body)

            response = self.client.post(
                "/api/webhooks/paystack",
                data=body,
                headers={"x-paystack-signature": sig, "content-type": "application/json"},
            )
            self.assertEqual(response.status_code, 200)
            mock_send_email.assert_not_called()

    @patch("app.services.log_service.log_event")
    @patch("app.services.email_service.send_receipt_email")
    @patch("app.services.transaction_service.create_transaction")
    def test_resend_api_failure_logged_and_does_not_break_webhook(
        self, mock_create_tx, mock_send_email, mock_log_event
    ):
        """Resend API failure logs receipt_failed and still returns 200 to Paystack."""
        mock_send_email.side_effect = Exception("Resend API rate limit or outage")

        payload = {
            "event": "charge.success",
            "data": {
                "reference": "INCPAY-RESEND-ERR",
                "amount": 9000,
                "status": "success",
                "customer": {"email": "customer@gmail.com"},
                "metadata": {"listed_amount": 100.0, "agreed_discount": 20.0},
            },
        }
        body = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(body)

        response = self.client.post(
            "/api/webhooks/paystack",
            data=body,
            headers={"x-paystack-signature": sig, "content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)

        receipt_fail_call = next(
            (c for c in mock_log_event.call_args_list if c[1].get("event") == "receipt_failed"),
            None,
        )
        self.assertIsNotNone(receipt_fail_call)

    # =========================================================================
    # 1.5 ADMIN EDGE CASES
    # =========================================================================

    def test_expired_token_returns_401_session_expired(self):
        """Request with expired/invalid admin token returns 401 'Session expired, please log in again.'."""
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("Token expired or invalid JWT")

        with patch("app.auth.get_supabase_client", return_value=mock_supabase):
            response = self.client.get(
                "/api/transactions",
                headers={"Authorization": "Bearer expired_token"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Session expired, please log in again.")

    @patch("app.services.transaction_service.get_transaction_by_id", return_value=None)
    def test_non_existent_transaction_returns_404(self, mock_get_tx):
        """Request for non-existent transaction ID returns 404."""
        from app.auth import verify_admin
        app.dependency_overrides[verify_admin] = lambda: {"id": str(uuid4())}
        try:
            unknown_id = uuid4()
            response = self.client.get(f"/api/transactions/{unknown_id}")
            self.assertEqual(response.status_code, 404)
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_resend_receipt_non_success_returns_400(self, mock_get_tx):
        """Attempting to resend receipt for a failed transaction returns 400."""
        from app.auth import verify_admin
        app.dependency_overrides[verify_admin] = lambda: {"id": str(uuid4())}
        try:
            tx_id = uuid4()
            failed_tx = TransactionResponse(
                id=tx_id,
                seller_id=uuid4(),
                coupon_id=uuid4(),
                paystack_reference="INCPAY-FAILED-01",
                currency="GHS",
                listed_amount=Decimal("100.00"),
                customer_discount_amount=Decimal("10.00"),
                amount_paid=Decimal("90.00"),
                platform_cut_amount=Decimal("10.00"),
                seller_payout_amount=Decimal("80.00"),
                status=TransactionStatus.FAILED,
                customer_email="kofi@example.com",
                created_at="2026-09-28T12:00:00Z",
                updated_at="2026-09-28T12:00:00Z",
            )
            mock_get_tx.return_value = failed_tx

            response = self.client.post(f"/api/transactions/{tx_id}/resend-receipt")
            self.assertEqual(response.status_code, 400)
            self.assertIn("Receipt can only be sent for successful transactions", response.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    # =========================================================================
    # 2. SECURITY HARDENING TESTS
    # =========================================================================

    def test_security_headers_present(self):
        """Verify strict security headers in HTTP responses."""
        response = self.client.get("/health")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_public_coupon_no_data_leakage(self, mock_get_coupon, mock_get_seller):
        """Assert public coupon endpoint never leaks sensitive merchant or platform data."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "SECURE-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "business_name": "Accra Super Store",
            "paystack_subaccount_code": "ACCT_SECRET999",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_seller.contact_email = "owner@secretmail.com"
        mock_seller.contact_phone = "+233555555555"
        mock_seller.settlement_account_number = "9876543210"
        mock_get_seller.return_value = mock_seller

        response = self.client.get("/api/public/coupon/SECURE-01")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check allowed fields
        self.assertEqual(data["business_name"], "Accra Super Store")
        self.assertEqual(data["customer_discount"], 10.0)

        # Check prohibited data leakage
        prohibited_keys = [
            "email", "phone", "contact_email", "contact_phone",
            "settlement_account_number", "paystack_subaccount_code",
            "seller_id", "id", "platform_cut", "platform_cut_amount",
        ]
        for key in prohibited_keys:
            self.assertNotIn(key, data, f"Leaked sensitive field '{key}' in public coupon endpoint")

    @patch("app.services.paystack_service.verify_transaction")
    def test_public_verify_no_data_leakage(self, mock_paystack_verify):
        """Assert public verify-payment never leaks sensitive fields."""
        mock_paystack_verify.return_value = {
            "status": "success",
            "reference": "INCPAY-SECURE-VERIFY",
            "amount": 9000,
            "subaccount": {"subaccount_code": "ACCT_SECRET"},
            "split": {"formula": "50/50"},
            "customer": {"email": "customer@example.com"},
        }

        response = self.client.get("/api/public/verify-payment/INCPAY-SECURE-VERIFY")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        prohibited_keys = ["subaccount", "split", "platform_cut", "seller_id"]
        for key in prohibited_keys:
            self.assertNotIn(key, data, f"Leaked sensitive field '{key}' in public verify endpoint")

    def test_malformed_reference_rejected(self):
        """Malformed reference parameters fail regex validation immediately with 400."""
        malformed_refs = [
            "SHORT",
            "BAD;DROP TABLE;",
            "<script>",
            "REF WITH SPACES",
            "INVALID!@#$",
        ]
        for ref in malformed_refs:
            response = self.client.get(f"/api/public/verify-payment/{ref}")
            self.assertEqual(response.status_code, 400)
            self.assertIn("Invalid payment reference format", response.json()["detail"])

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_invalid_email_format_rejected(self, mock_get_coupon, mock_get_seller):
        """Invalid customer email format in initialize-payment returns 400."""
        mock_get_coupon.return_value = {
            "coupon_code": "VALID-01",
            "is_active": True,
            "seller_id": str(uuid4()),
            "agreed_discount": 20.0,
            "paystack_subaccount_code": "ACCT_TEST",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_seller.paystack_subaccount_code = "ACCT_TEST"
        mock_get_seller.return_value = mock_seller

        invalid_emails = [
            "not-an-email",
            "@missinguser.com",
            "missingdomain@",
            "spaces in@email.com",
        ]
        for email in invalid_emails:
            response = self.client.post(
                "/api/public/initialize-payment",
                json={"coupon_code": "VALID-01", "listed_amount": 100.0, "email": email},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("Invalid email address format", response.json()["detail"])

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.coupon_service.get_coupon_by_code")
    def test_rate_limit_exceeded(self, mock_get_coupon, mock_get_seller):
        """Calling public coupon endpoint beyond limit (30/min) returns 429 Too Many Requests."""
        seller_id = uuid4()
        mock_get_coupon.return_value = {
            "coupon_code": "RATE-01",
            "is_active": True,
            "seller_id": str(seller_id),
            "agreed_discount": 20.0,
            "business_name": "Accra Rate Store",
        }
        mock_seller = MagicMock()
        mock_seller.is_active = True
        mock_get_seller.return_value = mock_seller

        # 30 requests should succeed
        for _ in range(30):
            res = self.client.get("/api/public/coupon/RATE-01")
            self.assertEqual(res.status_code, 200)

        # 31st request should be rate-limited (HTTP 429)
        over_limit_res = self.client.get("/api/public/coupon/RATE-01")
        self.assertEqual(over_limit_res.status_code, 429)
        self.assertIn("Rate limit exceeded", over_limit_res.text)


if __name__ == "__main__":
    unittest.main()
