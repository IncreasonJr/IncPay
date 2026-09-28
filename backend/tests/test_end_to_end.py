import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth import verify_admin
from app.config import get_settings
from app.limiter import limiter
from app.main import app
from app.models.coupon import CouponResponse
from app.models.seller import SellerResponse
from app.models.transaction import TransactionCreate, TransactionResponse, TransactionStatus
from app.services.coupon_service import CouponDetails


class TestEndToEndLifecycle(unittest.TestCase):
    """
    Comprehensive End-to-End lifecycle test walking through the 10-step platform journey:
    1. Admin authenticates
    2. Admin creates a seller (20% agreed discount, bank account details)
    3. Platform generates coupon code + QR data for that seller
    4. Customer opens payment page via coupon -> verifies seller and 10% customer discount
    5. Customer enters listed amount ₵100 -> server recalculates ₵90
    6. Customer initiates payment -> gets Paystack checkout URL & reference
    7. Paystack sends authentic charge.success webhook
    8. Transaction split verified:
       - listed: ₵100.00
       - discount: ₵10.00
       - paid: ₵90.00
       - platform cut: ₵10.00
       - seller payout: ₵80.00
       - status: success
    9. PDF receipt generated and emailed to customer
    10. Admin inspects transaction log -> verifies seller name, split amounts, and audit trail
    """

    def setUp(self):
        self.client = TestClient(app)
        limiter.reset()
        self.settings = get_settings()

    def tearDown(self):
        limiter.reset()
        app.dependency_overrides.clear()

    def _sign_payload(self, body_bytes: bytes) -> str:
        secret = self.settings.PAYSTACK_SECRET_KEY.encode("utf-8")
        return hmac.new(secret, body_bytes, hashlib.sha512).hexdigest()

    @patch("app.services.email_service.send_receipt_email")
    @patch("app.services.receipt_service.generate_receipt_pdf")
    @patch("app.services.paystack_service.initialize_transaction")
    @patch("app.services.paystack_service.create_subaccount")
    def test_full_platform_lifecycle_e2e(
        self,
        mock_create_subaccount,
        mock_init_paystack,
        mock_generate_pdf,
        mock_send_email,
    ):
        # In-memory test databases
        sellers_db = {}
        coupons_db = {}
        transactions_db = {}
        logs_db = []

        now_utc = datetime.now(timezone.utc)

        # Mock Paystack subaccount creation
        mock_create_subaccount.return_value = {"id": 12345, "subaccount_code": "ACCT_E2E_98765"}

        # Mock PDF generator
        mock_generate_pdf.return_value = b"%PDF-1.4 E2E Receipt Mock"

        # Mock Email sender
        mock_send_email.return_value = {"id": "email_e2e_123"}

        # Patch service layers with stateful in-memory stores
        with patch("app.services.seller_service.create_seller") as mock_create_seller, \
             patch("app.services.seller_service.get_seller") as mock_get_seller, \
             patch("app.services.seller_service.get_seller_by_id") as mock_get_seller_by_id, \
             patch("app.services.seller_service.list_sellers") as mock_list_sellers, \
             patch("app.services.coupon_service.create_coupon_for_seller") as mock_create_coupon_for_seller, \
             patch("app.services.coupon_service.get_coupon_by_code") as mock_get_coupon, \
             patch("app.services.coupon_service.get_active_coupon_for_seller") as mock_get_seller_coupon, \
             patch("app.services.transaction_service.create_transaction") as mock_create_tx, \
             patch("app.services.transaction_service.get_transaction_by_reference") as mock_get_tx_ref, \
             patch("app.services.transaction_service.get_transaction_by_id") as mock_get_tx_id, \
             patch("app.services.transaction_service.list_transactions_filtered") as mock_list_tx_filtered, \
             patch("app.services.log_service.log_event") as mock_log_event:

            def side_create_seller(seller_in):
                s_id = uuid4()
                c_code = f"FRESHMART-{uuid4().hex[:6].upper()}"
                seller_obj = SellerResponse(
                    id=s_id,
                    business_name=seller_in.business_name,
                    contact_email=seller_in.contact_email,
                    contact_phone=seller_in.contact_phone,
                    agreed_discount=seller_in.agreed_discount,
                    settlement_type=seller_in.settlement_type,
                    settlement_bank_code=seller_in.settlement_bank_code,
                    settlement_account_number=seller_in.settlement_account_number,
                    settlement_account_name=seller_in.settlement_account_name,
                    paystack_subaccount_code="ACCT_E2E_98765",
                    is_active=True,
                    coupon_code=c_code,
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                sellers_db[str(s_id)] = seller_obj

                c_id = uuid4()
                coupons_db[c_code] = CouponDetails({
                    "id": str(c_id),
                    "seller_id": str(s_id),
                    "code": c_code,
                    "coupon_code": c_code,
                    "is_active": True,
                    "agreed_discount": float(seller_in.agreed_discount),
                    "business_name": seller_in.business_name,
                    "paystack_subaccount_code": "ACCT_E2E_98765",
                })
                return seller_obj

            def side_get_seller(s_id):
                return sellers_db.get(str(s_id))

            def side_list_sellers(*args, **kwargs):
                return list(sellers_db.values())

            def side_get_seller_coupon(s_id):
                for c in coupons_db.values():
                    if c["seller_id"] == str(s_id) and c["is_active"]:
                        return CouponResponse(
                            id=uuid4(),
                            seller_id=s_id,
                            code=c["code"],
                            is_active=True,
                            created_at=now_utc,
                            updated_at=now_utc,
                        )
                return None

            def side_create_coupon_for_seller(s_id, b_name):
                c_code = f"FRESHMART-{uuid4().hex[:6].upper()}"
                coupons_db[c_code] = CouponDetails({
                    "id": str(uuid4()),
                    "seller_id": str(s_id),
                    "code": c_code,
                    "coupon_code": c_code,
                    "is_active": True,
                    "agreed_discount": 20.0,
                    "business_name": b_name,
                    "paystack_subaccount_code": "ACCT_E2E_98765",
                })
                return CouponResponse(
                    id=uuid4(),
                    seller_id=s_id,
                    code=c_code,
                    is_active=True,
                    created_at=now_utc,
                    updated_at=now_utc,
                )

            def side_get_coupon(code):
                return coupons_db.get(code.upper().strip())

            def side_create_tx(tx_in):
                t_id = uuid4()
                tx_obj = TransactionResponse(
                    id=t_id,
                    seller_id=tx_in.seller_id,
                    coupon_id=tx_in.coupon_id,
                    paystack_reference=tx_in.paystack_reference,
                    currency=tx_in.currency,
                    listed_amount=tx_in.listed_amount,
                    customer_discount_amount=tx_in.customer_discount_amount,
                    amount_paid=tx_in.amount_paid,
                    platform_cut_amount=tx_in.platform_cut_amount,
                    seller_payout_amount=tx_in.seller_payout_amount,
                    status=tx_in.status,
                    customer_email=tx_in.customer_email,
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                transactions_db[tx_in.paystack_reference] = tx_obj
                return tx_obj

            def side_get_tx_ref(ref):
                return transactions_db.get(ref)

            def side_get_tx_id(t_id):
                for tx in transactions_db.values():
                    if str(tx.id) == str(t_id):
                        return tx
                return None

            def side_list_tx_filtered(*args, **kwargs):
                tx_list = list(transactions_db.values())
                return tx_list, len(tx_list)

            def side_log_event(event, transaction_id=None, payload=None):
                logs_db.append({"event": event, "transaction_id": transaction_id, "payload": payload})
                return MagicMock()

            mock_create_seller.side_effect = side_create_seller
            mock_get_seller.side_effect = side_get_seller
            mock_get_seller_by_id.side_effect = side_get_seller
            mock_list_sellers.side_effect = side_list_sellers
            mock_create_coupon_for_seller.side_effect = side_create_coupon_for_seller
            mock_get_coupon.side_effect = side_get_coupon
            mock_get_seller_coupon.side_effect = side_get_seller_coupon
            mock_create_tx.side_effect = side_create_tx
            mock_get_tx_ref.side_effect = side_get_tx_ref
            mock_get_tx_id.side_effect = side_get_tx_id
            mock_list_tx_filtered.side_effect = side_list_tx_filtered
            mock_log_event.side_effect = side_log_event

            # -----------------------------------------------------------------
            # STEP 1: Admin logs in (authenticated session established)
            # -----------------------------------------------------------------
            admin_user = {"id": str(uuid4()), "email": "admin@incpay.app"}
            app.dependency_overrides[verify_admin] = lambda: admin_user

            # -----------------------------------------------------------------
            # STEP 2: Admin creates a seller (20% agreed discount, bank account)
            # -----------------------------------------------------------------
            seller_payload = {
                "business_name": "E2E Fresh Mart",
                "contact_email": "owner@freshmart.com",
                "contact_phone": "+233241234567",
                "agreed_discount": 20.0,
                "settlement_type": "bank",
                "settlement_bank_code": "030100",
                "settlement_account_number": "1234567890",
                "settlement_account_name": "Kofi Mensah",
            }
            create_seller_res = self.client.post("/api/sellers", json=seller_payload)
            self.assertEqual(create_seller_res.status_code, 201)
            created_seller = create_seller_res.json()
            seller_id = created_seller["id"]
            self.assertEqual(created_seller["business_name"], "E2E Fresh Mart")
            self.assertEqual(created_seller["paystack_subaccount_code"], "ACCT_E2E_98765")

            # -----------------------------------------------------------------
            # STEP 3: Platform generates coupon code + QR data for that seller
            # -----------------------------------------------------------------
            coupon_res = self.client.get(f"/api/sellers/{seller_id}/coupon")
            self.assertEqual(coupon_res.status_code, 200)
            coupon_data = coupon_res.json()
            coupon_code = coupon_data.get("code") or coupon_data.get("coupon_code")
            self.assertTrue(len(coupon_code) >= 4)
            self.assertIn("payment_url", coupon_data)

            qr_res = self.client.get(f"/api/sellers/{seller_id}/qr?format=svg")
            self.assertEqual(qr_res.status_code, 200)
            self.assertEqual(qr_res.headers["content-type"], "image/svg+xml")

            # -----------------------------------------------------------------
            # STEP 4: Customer scans QR / opens payment page -> GET /api/public/coupon/{code}
            # -----------------------------------------------------------------
            # Public endpoint: clear admin dependency override to prove unauthenticated access
            app.dependency_overrides.clear()

            public_coupon_res = self.client.get(f"/api/public/coupon/{coupon_code}")
            self.assertEqual(public_coupon_res.status_code, 200)
            public_coupon_data = public_coupon_res.json()
            self.assertEqual(public_coupon_data["business_name"], "E2E Fresh Mart")
            self.assertEqual(public_coupon_data["customer_discount"], 10.0)
            self.assertEqual(public_coupon_data["agreed_discount"], 20.0)

            # -----------------------------------------------------------------
            # STEP 5 & 6: Customer enters listed amount ₵100 -> initiates payment
            # -----------------------------------------------------------------
            reference = f"INCPAY-E2E-{uuid4().hex.upper()}"
            mock_init_paystack.return_value = {
                "authorization_url": "https://checkout.paystack.com/e2e_checkout",
                "access_code": "acc_e2e_123",
                "reference": reference,
            }

            init_payload = {
                "coupon_code": coupon_code,
                "listed_amount": 100.0,
                "email": "customer@gmail.com",
            }
            init_res = self.client.post("/api/public/initialize-payment", json=init_payload)
            self.assertEqual(init_res.status_code, 200)
            init_data = init_res.json()

            self.assertEqual(init_data["listed_amount"], 100.0)
            self.assertEqual(init_data["discount_amount"], 10.0)
            self.assertEqual(init_data["amount_paid"], 90.0)
            self.assertEqual(init_data["authorization_url"], "https://checkout.paystack.com/e2e_checkout")
            self.assertEqual(init_data["reference"], reference)

            # -----------------------------------------------------------------
            # STEP 7: Paystack sends webhook -> POST /api/webhooks/paystack
            # -----------------------------------------------------------------
            webhook_payload = {
                "event": "charge.success",
                "data": {
                    "reference": reference,
                    "amount": 9000,  # ₵90.00 in pesewas
                    "status": "success",
                    "customer": {"email": "customer@gmail.com"},
                    "metadata": {
                        "coupon_code": coupon_code,
                        "seller_id": str(seller_id),
                        "business_name": "E2E Fresh Mart",
                        "listed_amount": 100.0,
                        "customer_discount_amount": 10.0,
                        "amount_paid": 90.0,
                        "agreed_discount": 20.0,
                    },
                },
            }
            body_bytes = json.dumps(webhook_payload).encode("utf-8")
            signature = self._sign_payload(body_bytes)

            webhook_res = self.client.post(
                "/api/webhooks/paystack",
                data=body_bytes,
                headers={"x-paystack-signature": signature, "content-type": "application/json"},
            )
            self.assertEqual(webhook_res.status_code, 200)
            self.assertEqual(webhook_res.json(), {"status": "ok"})

            # -----------------------------------------------------------------
            # STEP 8: Verify transaction split recorded accurately
            # -----------------------------------------------------------------
            saved_tx = transactions_db.get(reference)
            self.assertIsNotNone(saved_tx)
            self.assertEqual(saved_tx.listed_amount, Decimal("100.00"))
            self.assertEqual(saved_tx.customer_discount_amount, Decimal("10.00"))
            self.assertEqual(saved_tx.amount_paid, Decimal("90.00"))
            self.assertEqual(saved_tx.platform_cut_amount, Decimal("10.00"))
            self.assertEqual(saved_tx.seller_payout_amount, Decimal("80.00"))
            self.assertEqual(saved_tx.status, TransactionStatus.SUCCESS)

            # -----------------------------------------------------------------
            # STEP 9: Verify receipt generation & dispatch
            # -----------------------------------------------------------------
            mock_generate_pdf.assert_called_once()
            mock_send_email.assert_called_once()
            email_args = mock_send_email.call_args[0]
            self.assertEqual(email_args[0], "customer@gmail.com")
            self.assertEqual(email_args[1], "E2E Fresh Mart")
            self.assertEqual(email_args[3], reference)

            # -----------------------------------------------------------------
            # STEP 10: Admin views transaction log in dashboard
            # -----------------------------------------------------------------
            app.dependency_overrides[verify_admin] = lambda: admin_user

            tx_list_res = self.client.get("/api/transactions")
            self.assertEqual(tx_list_res.status_code, 200)
            tx_list_data = tx_list_res.json()
            self.assertEqual(tx_list_data["total"], 1)
            first_tx = tx_list_data["transactions"][0]

            self.assertEqual(first_tx["paystack_reference"], reference)
            self.assertEqual(first_tx["seller"]["business_name"], "E2E Fresh Mart")
            self.assertEqual(float(first_tx["listed_amount"]), 100.0)
            self.assertEqual(float(first_tx["discount_amount"]), 10.0)
            self.assertEqual(float(first_tx["amount_paid"]), 90.0)
            self.assertEqual(float(first_tx["platform_cut"]), 10.0)
            self.assertEqual(float(first_tx["seller_payout"]), 80.0)
            self.assertEqual(first_tx["status"], "success")
            self.assertEqual(first_tx["customer_email"], "customer@gmail.com")


if __name__ == "__main__":
    unittest.main()
