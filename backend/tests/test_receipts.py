import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.models.seller import SellerResponse
from app.models.transaction import TransactionResponse, TransactionStatus
from app.services import email_service, receipt_service, transaction_service


class TestReceipts(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.seller_id = uuid4()
        self.coupon_id = uuid4()
        self.reference = f"INCPAY-RECEIPT-{uuid4().hex[:8].upper()}"

        self.mock_tx = TransactionResponse(
            id=uuid4(),
            seller_id=self.seller_id,
            coupon_id=self.coupon_id,
            paystack_reference=self.reference,
            currency="GHS",
            listed_amount=Decimal("1000.00"),
            customer_discount_amount=Decimal("100.00"),
            amount_paid=Decimal("900.00"),
            platform_cut_amount=Decimal("100.00"),
            seller_payout_amount=Decimal("800.00"),
            status=TransactionStatus.SUCCESS,
            customer_email="customer@example.com",
            created_at="2026-09-24T12:00:00Z",
            updated_at="2026-09-24T12:00:00Z",
        )

        self.mock_seller = SellerResponse(
            id=self.seller_id,
            business_name="Accra Fashion House",
            contact_email="seller@example.com",
            contact_phone="+233201234567",
            agreed_discount=Decimal("20.00"),
            settlement_type="mobile_money",
            settlement_bank_code="MTN",
            settlement_account_number="0240000000",
            settlement_account_name="Kwame Mensah",
            paystack_subaccount_code="ACCT_sub123",
            is_active=True,
            created_at="2026-09-24T10:00:00Z",
            updated_at="2026-09-24T10:00:00Z",
        )

    def test_generate_receipt_pdf_bytes(self):
        """Verify that generate_receipt_pdf creates valid PDF bytes and protects sensitive margins."""
        tx_dict = self.mock_tx.model_dump()
        seller_dict = self.mock_seller.model_dump()

        pdf_bytes = receipt_service.generate_receipt_pdf(tx_dict, seller_dict)

        # 1. Valid PDF header
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

        # 2. Security: Verify hidden platform cut amounts are NOT leaked in PDF content
        pdf_str = pdf_bytes.decode("latin1", errors="ignore")
        self.assertNotIn("platform_cut", pdf_str)
        self.assertNotIn("seller_payout", pdf_str)

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.transaction_service.get_transaction_by_reference")
    def test_public_receipt_endpoint_success(self, mock_get_tx, mock_get_seller):
        """GET /api/public/receipt/{reference} returns 200 and application/pdf."""
        mock_get_tx.return_value = self.mock_tx
        mock_get_seller.return_value = self.mock_seller

        response = self.client.get(f"/api/public/receipt/{self.reference}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn(f'filename="receipt-{self.reference}.pdf"', response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

    @patch("app.services.transaction_service.get_transaction_by_reference")
    def test_public_receipt_endpoint_not_found(self, mock_get_tx):
        """Non-existent reference returns 404."""
        mock_get_tx.return_value = None
        response = self.client.get("/api/public/receipt/NON_EXISTENT_REF")
        self.assertEqual(response.status_code, 404)

    @patch("app.services.transaction_service.get_transaction_by_reference")
    def test_public_receipt_endpoint_pending_rejected(self, mock_get_tx):
        """Pending or non-success transactions return 404."""
        pending_tx = TransactionResponse(
            **{**self.mock_tx.model_dump(), "status": TransactionStatus.PENDING}
        )
        mock_get_tx.return_value = pending_tx

        response = self.client.get(f"/api/public/receipt/{self.reference}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not in a successful state", response.json()["detail"])

    @patch("resend.Emails.send")
    def test_send_receipt_email_success(self, mock_resend_send):
        """send_receipt_email properly calls Resend SDK with PDF attachment."""
        settings = get_settings()
        settings.RESEND_API_KEY = "re_test_mock_key"
        settings.RESEND_FROM_EMAIL = "receipts@incpay.app"

        mock_resend_send.return_value = {"id": "email_12345"}

        pdf_bytes = b"%PDF-mockcontent"
        result = email_service.send_receipt_email(
            customer_email="customer@example.com",
            seller_name="Accra Fashion House",
            pdf_bytes=pdf_bytes,
            reference=self.reference,
        )

        self.assertEqual(result["id"], "email_12345")
        mock_resend_send.assert_called_once()
        call_params = mock_resend_send.call_args[0][0]
        self.assertEqual(call_params["to"], ["customer@example.com"])
        self.assertIn("Accra Fashion House", call_params["subject"])
        self.assertEqual(len(call_params["attachments"]), 1)
        self.assertEqual(call_params["attachments"][0]["filename"], f"receipt-{self.reference}.pdf")
        self.assertEqual(call_params["attachments"][0]["content"], list(pdf_bytes))

    def test_send_receipt_email_unconfigured_skips_gracefully(self):
        """Missing RESEND_API_KEY skips delivery safely without raising an exception."""
        settings = get_settings()
        old_key = settings.RESEND_API_KEY
        settings.RESEND_API_KEY = ""
        try:
            result = email_service.send_receipt_email(
                customer_email="customer@example.com",
                seller_name="Accra Fashion House",
                pdf_bytes=b"%PDF-mock",
                reference=self.reference,
            )
            self.assertEqual(result.get("status"), "skipped")
        finally:
            settings.RESEND_API_KEY = old_key

    @patch("app.services.email_service.send_receipt_email")
    @patch("app.services.receipt_service.generate_receipt_pdf")
    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.create_transaction")
    @patch("app.services.transaction_service.get_transaction_by_reference", return_value=None)
    def test_webhook_triggers_receipt_email(
        self, mock_get_tx, mock_create_tx, mock_log_event, mock_gen_pdf, mock_send_email
    ):
        """charge.success webhook automatically triggers PDF generation and email sending."""
        mock_create_tx.return_value = self.mock_tx
        mock_gen_pdf.return_value = b"%PDF-mock"

        payload = {
            "event": "charge.success",
            "data": {
                "reference": self.reference,
                "amount": 90000,
                "status": "success",
                "customer": {"email": "customer@example.com"},
                "metadata": {
                    "seller_id": str(self.seller_id),
                    "coupon_code": "TEST-CODE",
                    "business_name": "Accra Fashion House",
                    "agreed_discount": 20.0,
                },
            },
        }

        res = transaction_service.create_transaction_from_webhook(payload)
        self.assertIsNotNone(res)
        mock_gen_pdf.assert_called_once()
        mock_send_email.assert_called_once()

    @patch("app.services.email_service.send_receipt_email", side_effect=RuntimeError("Resend API down"))
    @patch("app.services.receipt_service.generate_receipt_pdf", return_value=b"%PDF-mock")
    @patch("app.services.log_service.log_event")
    @patch("app.services.transaction_service.create_transaction")
    @patch("app.services.transaction_service.get_transaction_by_reference", return_value=None)
    def test_webhook_email_failure_does_not_break_transaction(
        self, mock_get_tx, mock_create_tx, mock_log_event, mock_gen_pdf, mock_send_email
    ):
        """If email dispatch throws an exception, transaction insertion still succeeds."""
        mock_create_tx.return_value = self.mock_tx

        payload = {
            "event": "charge.success",
            "data": {
                "reference": self.reference,
                "amount": 90000,
                "status": "success",
                "customer": {"email": "customer@example.com"},
                "metadata": {
                    "seller_id": str(self.seller_id),
                    "coupon_code": "TEST-CODE",
                    "business_name": "Accra Fashion House",
                },
            },
        }

        res = transaction_service.create_transaction_from_webhook(payload)
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "success")
