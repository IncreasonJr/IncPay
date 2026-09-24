import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth import verify_admin
from app.main import app
from app.models.log import LogResponse
from app.models.seller import SellerResponse
from app.models.transaction import TransactionResponse, TransactionStatus


class TestTransactionsAdmin(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_admin_user = {
            "id": str(uuid4()),
            "email": "admin@incpay.app",
            "role": "authenticated",
        }
        self.seller_id = uuid4()
        self.coupon_id = uuid4()
        self.tx_id = uuid4()

        self.mock_seller = SellerResponse(
            id=self.seller_id,
            business_name="Accra Tech Hub",
            contact_email="owner@accratech.com",
            contact_phone="+233241112233",
            agreed_discount=Decimal("20.00"),
            settlement_type="mobile_money",
            settlement_bank_code="MTN",
            settlement_account_number="0241112233",
            settlement_account_name="Accra Tech Hub",
            paystack_subaccount_code="SUB_accra123",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.mock_transaction = TransactionResponse(
            id=self.tx_id,
            seller_id=self.seller_id,
            coupon_id=self.coupon_id,
            paystack_reference="INCPAY-TX-1001",
            currency="GHS",
            listed_amount=Decimal("100.00"),
            customer_discount_amount=Decimal("10.00"),
            amount_paid=Decimal("90.00"),
            platform_cut_amount=Decimal("10.00"),
            seller_payout_amount=Decimal("80.00"),
            status=TransactionStatus.SUCCESS,
            customer_email="customer@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.mock_log = LogResponse(
            id=uuid4(),
            transaction_id=self.tx_id,
            event_type="charge.success",
            payload={"status": "success", "amount": 9000},
            created_at=datetime.utcnow(),
        )

    def test_unauthenticated_requests_rejected(self):
        """Endpoints in /api/transactions require admin authentication."""
        app.dependency_overrides.clear()

        res1 = self.client.get("/api/transactions")
        self.assertEqual(res1.status_code, 401)

        res2 = self.client.get(f"/api/transactions/{self.tx_id}")
        self.assertEqual(res2.status_code, 401)

        res3 = self.client.post(f"/api/transactions/{self.tx_id}/resend-receipt")
        self.assertEqual(res3.status_code, 401)

        res4 = self.client.get(f"/api/transactions/{self.tx_id}/receipt")
        self.assertEqual(res4.status_code, 401)

    @patch("app.services.seller_service.list_sellers")
    @patch("app.services.transaction_service.list_transactions_filtered")
    def test_list_transactions_success(self, mock_list_tx, mock_list_sellers):
        """Admin can list transactions with seller metadata and pagination."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            mock_list_tx.return_value = ([self.mock_transaction], 1)
            mock_list_sellers.return_value = [self.mock_seller]

            response = self.client.get("/api/transactions?page=1&page_size=20")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(data["total"], 1)
            self.assertEqual(data["page"], 1)
            self.assertEqual(data["page_size"], 20)
            self.assertEqual(data["total_pages"], 1)
            self.assertEqual(len(data["transactions"]), 1)

            tx = data["transactions"][0]
            self.assertEqual(tx["id"], str(self.tx_id))
            self.assertEqual(tx["paystack_reference"], "INCPAY-TX-1001")
            self.assertEqual(tx["seller"]["business_name"], "Accra Tech Hub")
            self.assertEqual(float(tx["listed_amount"]), 100.0)
            self.assertEqual(float(tx["discount_amount"]), 10.0)
            self.assertEqual(float(tx["amount_paid"]), 90.0)
            self.assertEqual(float(tx["platform_cut"]), 10.0)
            self.assertEqual(float(tx["seller_payout"]), 80.0)
            self.assertEqual(tx["status"], "success")
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.log_service.get_logs_for_transaction")
    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_get_transaction_detail_success(self, mock_get_tx, mock_get_seller, mock_get_logs):
        """Admin can retrieve full transaction details with seller info and logs."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            mock_get_tx.return_value = self.mock_transaction
            mock_get_seller.return_value = self.mock_seller
            mock_get_logs.return_value = [self.mock_log]

            response = self.client.get(f"/api/transactions/{self.tx_id}")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(data["id"], str(self.tx_id))
            self.assertEqual(data["seller"]["business_name"], "Accra Tech Hub")
            self.assertEqual(data["seller"]["email"], "owner@accratech.com")
            self.assertEqual(len(data["logs"]), 1)
            self.assertEqual(data["logs"][0]["event_type"], "charge.success")
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_get_transaction_detail_not_found(self, mock_get_tx):
        """Unknown transaction ID returns 404."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            mock_get_tx.return_value = None

            unknown_id = uuid4()
            response = self.client.get(f"/api/transactions/{unknown_id}")
            self.assertEqual(response.status_code, 404)
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.log_service.log_event")
    @patch("app.services.email_service.send_receipt_email")
    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_resend_receipt_success(self, mock_get_tx, mock_get_seller, mock_send_email, mock_log_event):
        """Admin can resend receipt PDF to customer email."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            mock_get_tx.return_value = self.mock_transaction
            mock_get_seller.return_value = self.mock_seller
            mock_send_email.return_value = {"id": "mock_email_123"}

            response = self.client.post(f"/api/transactions/{self.tx_id}/resend-receipt")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(data["status"], "sent")
            self.assertEqual(data["recipient"], "customer@example.com")

            mock_send_email.assert_called_once()
            mock_log_event.assert_called_once()
            log_call_kwargs = mock_log_event.call_args[1]
            self.assertEqual(log_call_kwargs["event"], "receipt_resent")
            self.assertEqual(log_call_kwargs["transaction_id"], self.tx_id)
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_resend_receipt_unsuccessful_rejected(self, mock_get_tx):
        """Pending or failed transactions cannot resend receipts."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            pending_tx = self.mock_transaction.model_copy(update={"status": TransactionStatus.PENDING})
            mock_get_tx.return_value = pending_tx

            response = self.client.post(f"/api/transactions/{self.tx_id}/resend-receipt")
            self.assertEqual(response.status_code, 400)
            self.assertIn("unsuccessful", response.json()["detail"].lower())
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_resend_receipt_missing_email_rejected(self, mock_get_tx):
        """Transactions with no email or noreply@incpay.app cannot resend receipts."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            no_email_tx = self.mock_transaction.model_copy(update={"customer_email": "noreply@incpay.app"})
            mock_get_tx.return_value = no_email_tx

            response = self.client.post(f"/api/transactions/{self.tx_id}/resend-receipt")
            self.assertEqual(response.status_code, 400)
            self.assertIn("no valid customer email", response.json()["detail"].lower())
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.seller_service.get_seller_by_id")
    @patch("app.services.transaction_service.get_transaction_by_id")
    def test_download_transaction_receipt_pdf(self, mock_get_tx, mock_get_seller):
        """Admin can download receipt PDF directly."""
        app.dependency_overrides[verify_admin] = lambda: self.mock_admin_user
        try:
            mock_get_tx.return_value = self.mock_transaction
            mock_get_seller.return_value = self.mock_seller

            response = self.client.get(f"/api/transactions/{self.tx_id}/receipt")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Content-Type"], "application/pdf")
            self.assertIn("receipt-INCPAY-TX-1001.pdf", response.headers["Content-Disposition"])
            self.assertTrue(response.content.startswith(b"%PDF"))
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
