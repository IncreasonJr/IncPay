import hashlib
import hmac
import json
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.models.transaction import TransactionCreate, TransactionResponse, TransactionStatus
from app.services import transaction_service
from app.services.paystack_service import PaystackError


def compute_signature(payload_bytes: bytes, secret_key: str) -> str:
    """Helper to compute Paystack HMAC SHA512 signature."""
    return hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha512).hexdigest()


class TestPaystackWebhooks(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.settings = get_settings()
        self.secret_key = self.settings.PAYSTACK_SECRET_KEY or "sk_test_mock_secret_key"
        self.settings.PAYSTACK_SECRET_KEY = self.secret_key

        self.seller_id = str(uuid4())
        self.coupon_id = str(uuid4())

    def test_invalid_signature_rejected(self):
        """Webhooks with missing or invalid x-paystack-signature header return 401."""
        payload = {"event": "charge.success", "data": {"reference": "REF_1"}}
        raw_body = json.dumps(payload).encode("utf-8")

        # Case 1: Missing signature header
        res1 = self.client.post("/api/webhooks/paystack", content=raw_body)
        self.assertEqual(res1.status_code, 401)

        # Case 2: Invalid signature header
        res2 = self.client.post(
            "/api/webhooks/paystack",
            content=raw_body,
            headers={"x-paystack-signature": "invalid_signature_hash"},
        )
        self.assertEqual(res2.status_code, 401)

    @patch("app.services.transaction_service.create_transaction_from_webhook")
    def test_valid_signature_accepted(self, mock_create_tx):
        """Webhooks with valid HMAC SHA512 signature return 200 OK."""
        mock_create_tx.return_value = {"id": str(uuid4()), "status": "success"}

        payload = {
            "event": "charge.success",
            "data": {
                "reference": "REF_VALID_SIG",
                "amount": 90000,
                "status": "success",
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = compute_signature(raw_body, self.secret_key)

        response = self.client.post(
            "/api/webhooks/paystack",
            content=raw_body,
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_create_tx.assert_called_once()

    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.create_transaction")
    @patch("app.services.transaction_service.get_transaction_by_reference", return_value=None)
    def test_charge_success_creates_transaction_with_split(
        self, mock_get_tx, mock_create_tx, mock_log_event
    ):
        """
        charge.success event recalculates split values server-side:
        - 90000 pesewas = ₵900.00 amount_paid
        - agreed_discount D = 20.00%
        - listed_amount = ₵1,000.00
        - customer_discount = ₵100.00
        - platform_cut = ₵100.00
        - seller_payout = ₵800.00
        - status = 'success'
        """
        created_tx_id = uuid4()
        ref = f"INCPAY-SUCC-{uuid4().hex[:8].upper()}"

        def fake_create(tx_create: TransactionCreate):
            # Assert financial invariants
            self.assertEqual(tx_create.status, TransactionStatus.SUCCESS)
            self.assertEqual(tx_create.amount_paid, Decimal("900.00"))
            self.assertEqual(tx_create.listed_amount, Decimal("1000.00"))
            self.assertEqual(tx_create.customer_discount_amount, Decimal("100.00"))
            self.assertEqual(tx_create.platform_cut_amount, Decimal("100.00"))
            self.assertEqual(tx_create.seller_payout_amount, Decimal("800.00"))
            self.assertEqual(tx_create.paystack_reference, ref)

            return TransactionResponse(
                id=created_tx_id,
                seller_id=tx_create.seller_id,
                coupon_id=tx_create.coupon_id,
                paystack_reference=tx_create.paystack_reference,
                currency="GHS",
                listed_amount=tx_create.listed_amount,
                customer_discount_amount=tx_create.customer_discount_amount,
                amount_paid=tx_create.amount_paid,
                platform_cut_amount=tx_create.platform_cut_amount,
                seller_payout_amount=tx_create.seller_payout_amount,
                status=tx_create.status,
                customer_email=tx_create.customer_email,
                created_at="2026-09-24T12:00:00Z",
                updated_at="2026-09-24T12:00:00Z",
            )

        mock_create_tx.side_effect = fake_create

        payload = {
            "event": "charge.success",
            "data": {
                "reference": ref,
                "amount": 90000,
                "status": "success",
                "customer": {"email": "customer@example.com"},
                "metadata": {
                    "seller_id": self.seller_id,
                    "coupon_code": "TEST-COUPON",
                    "agreed_discount": 20.00,
                    "listed_amount": 1000.00,
                },
            },
        }

        result = transaction_service.create_transaction_from_webhook(payload)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(str(result["id"]), str(created_tx_id))
        mock_log_event.assert_called()

    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.create_transaction")
    @patch("app.services.transaction_service.get_transaction_by_reference", return_value=None)
    def test_charge_failed_creates_failed_transaction(
        self, mock_get_tx, mock_create_tx, mock_log_event
    ):
        """charge.failed event inserts a transaction row with status='failed'."""
        created_tx_id = uuid4()
        ref = f"INCPAY-FAIL-{uuid4().hex[:8].upper()}"

        def fake_create(tx_create: TransactionCreate):
            self.assertEqual(tx_create.status, TransactionStatus.FAILED)
            return TransactionResponse(
                id=created_tx_id,
                seller_id=tx_create.seller_id,
                coupon_id=tx_create.coupon_id,
                paystack_reference=tx_create.paystack_reference,
                currency="GHS",
                listed_amount=tx_create.listed_amount,
                customer_discount_amount=tx_create.customer_discount_amount,
                amount_paid=tx_create.amount_paid,
                platform_cut_amount=tx_create.platform_cut_amount,
                seller_payout_amount=tx_create.seller_payout_amount,
                status=tx_create.status,
                customer_email=tx_create.customer_email,
                created_at="2026-09-24T12:00:00Z",
                updated_at="2026-09-24T12:00:00Z",
            )

        mock_create_tx.side_effect = fake_create

        payload = {
            "event": "charge.failed",
            "data": {
                "reference": ref,
                "amount": 90000,
                "status": "failed",
                "customer": {"email": "customer@example.com"},
                "metadata": {
                    "seller_id": self.seller_id,
                    "coupon_code": "TEST-COUPON",
                    "agreed_discount": 20.00,
                },
            },
        }

        result = transaction_service.create_transaction_from_webhook(payload)
        self.assertEqual(result["status"], "failed")
        mock_log_event.assert_called()

    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.create_transaction")
    def test_idempotency_prevents_duplicate_transactions(
        self, mock_create_tx, mock_log_event
    ):
        """Second webhook call with same reference does NOT create a duplicate row."""
        existing_tx = TransactionResponse(
            id=uuid4(),
            seller_id=uuid4(),
            coupon_id=uuid4(),
            paystack_reference="REF_IDEMPOTENT_123",
            currency="GHS",
            listed_amount=Decimal("1000.00"),
            customer_discount_amount=Decimal("100.00"),
            amount_paid=Decimal("900.00"),
            platform_cut_amount=Decimal("100.00"),
            seller_payout_amount=Decimal("800.00"),
            status=TransactionStatus.SUCCESS,
            customer_email="kofi@example.com",
            created_at="2026-09-24T12:00:00Z",
            updated_at="2026-09-24T12:00:00Z",
        )

        with patch(
            "app.services.transaction_service.get_transaction_by_reference",
            return_value=existing_tx,
        ):
            payload = {
                "event": "charge.success",
                "data": {
                    "reference": "REF_IDEMPOTENT_123",
                    "amount": 90000,
                    "status": "success",
                },
            }
            res = transaction_service.create_transaction_from_webhook(payload)

            # Did NOT attempt to insert new transaction
            mock_create_tx.assert_not_called()
            # Returned existing transaction
            self.assertEqual(res["paystack_reference"], "REF_IDEMPOTENT_123")
            # Log event was still recorded for audit
            mock_log_event.assert_called()

    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.update_transaction_status")
    def test_reconciliation_updates_status_if_discrepancy(
        self, mock_update_status, mock_log_event
    ):
        """If transaction exists as pending but webhook says success, status is reconciled."""
        existing_pending = TransactionResponse(
            id=uuid4(),
            seller_id=uuid4(),
            coupon_id=uuid4(),
            paystack_reference="REF_RECONCILE_123",
            currency="GHS",
            listed_amount=Decimal("1000.00"),
            customer_discount_amount=Decimal("100.00"),
            amount_paid=Decimal("900.00"),
            platform_cut_amount=Decimal("100.00"),
            seller_payout_amount=Decimal("800.00"),
            status=TransactionStatus.PENDING,
            customer_email="kofi@example.com",
            created_at="2026-09-24T12:00:00Z",
            updated_at="2026-09-24T12:00:00Z",
        )

        reconciled_success = TransactionResponse(
            **{**existing_pending.model_dump(), "status": TransactionStatus.SUCCESS}
        )
        mock_update_status.return_value = reconciled_success

        with patch(
            "app.services.transaction_service.get_transaction_by_reference",
            return_value=existing_pending,
        ):
            payload = {
                "event": "charge.success",
                "data": {
                    "reference": "REF_RECONCILE_123",
                    "amount": 90000,
                    "status": "success",
                },
            }
            res = transaction_service.create_transaction_from_webhook(payload)
            mock_update_status.assert_called_once_with(
                "REF_RECONCILE_123", TransactionStatus.SUCCESS
            )
            self.assertEqual(res["status"], "success")

    @patch("app.services.paystack_service.verify_transaction")
    def test_public_verify_payment_endpoint_returns_data(self, mock_verify):
        """GET /api/public/verify-payment/{reference} returns sanitized Paystack verification."""
        mock_verify.return_value = {
            "status": "success",
            "amount": 90000,  # 900.00 GHS in pesewas
            "reference": "INCPAY-VERIFY-123",
        }

        res = self.client.get("/api/public/verify-payment/INCPAY-VERIFY-123")
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["amount_paid"], 900.0)
        self.assertEqual(data["reference"], "INCPAY-VERIFY-123")

        # Verify no internal secrets leaked
        self.assertNotIn("seller_id", data)
        self.assertNotIn("subaccount", data)
        self.assertNotIn("platform_cut_amount", data)

    @patch("app.services.paystack_service.verify_transaction")
    def test_public_verify_payment_not_found(self, mock_verify):
        """GET /api/public/verify-payment/{reference} returns 404 when Paystack returns error."""
        mock_verify.side_effect = PaystackError("Transaction reference not found", status_code=404)

        with patch("app.services.transaction_service.get_transaction_by_reference", return_value=None):
            res = self.client.get("/api/public/verify-payment/NON_EXISTENT_REF")
            self.assertEqual(res.status_code, 404)
