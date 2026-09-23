import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.models.coupon import CouponResponse
from app.models.seller import SellerResponse
from app.services.coupon_service import generate_coupon_code
from app.services.qr_service import generate_qr_png, generate_qr_svg


class TestCouponsAndQr(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_user = MagicMock()
        self.mock_user.id = str(uuid4())
        self.mock_user.email = "admin@incpay.com"

        self.mock_user_response = MagicMock()
        self.mock_user_response.user = self.mock_user

    def test_coupon_code_generation_format(self):
        """
        Verify format {SLUG}-{RANDOM}:
        - Slug: up to 12 alphanumeric uppercase characters with spaces converted to hyphens.
        - Random: 6 uppercase alphanumeric characters.
        """
        code = generate_coupon_code("Kofi Fashions Ltd")
        parts = code.split("-")
        self.assertGreaterEqual(len(parts), 2)
        # Random part is last segment of 6 chars
        self.assertEqual(len(parts[-1]), 6)
        self.assertTrue(parts[-1].isalnum())
        self.assertTrue(parts[-1].isupper())
        # First part starts with KOFI
        self.assertTrue(code.startswith("KOFI"))

    def test_coupon_code_sanitization_special_characters(self):
        """
        Verify that special symbols (!, @, &, etc.) are stripped from slug.
        """
        code = generate_coupon_code("Ama & Sons (Trading) #1")
        # No special characters in code besides hyphen
        self.assertTrue(all(c.isalnum() or c == "-" for c in code))
        self.assertTrue(code.isupper())

    def test_qr_png_generation_bytes(self):
        """
        Verify in-memory PNG generation returns valid PNG bytes.
        """
        url = "https://incpay.vercel.app/pay/ACCRA-SHOP-99AB12"
        png_bytes = generate_qr_png(url)
        self.assertIsInstance(png_bytes, bytes)
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(png_bytes), 100)

    def test_qr_svg_generation_markup(self):
        """
        Verify in-memory SVG generation returns valid SVG XML string.
        """
        url = "https://incpay.vercel.app/pay/ACCRA-SHOP-99AB12"
        svg_str = generate_qr_svg(url)
        self.assertIsInstance(svg_str, str)
        self.assertIn("<svg", svg_str)
        self.assertIn("</svg>", svg_str)

    def test_endpoints_unauthenticated(self):
        """
        Verify that coupon and QR endpoints require admin Bearer token.
        """
        dummy_id = str(uuid4())
        self.assertEqual(self.client.get(f"/api/sellers/{dummy_id}/coupon").status_code, 401)
        self.assertEqual(self.client.get(f"/api/sellers/{dummy_id}/qr").status_code, 401)
        self.assertEqual(self.client.get(f"/api/sellers/{dummy_id}/qr?format=svg").status_code, 401)
        self.assertEqual(self.client.post(f"/api/sellers/{dummy_id}/regenerate-coupon").status_code, 401)

    @patch("app.auth.get_supabase_client")
    @patch("app.services.seller_service.get_seller")
    @patch("app.services.coupon_service.get_active_coupon_for_seller")
    def test_get_seller_coupon_authenticated(
        self,
        mock_get_coupon,
        mock_get_seller,
        mock_supabase_client,
    ):
        """
        Authenticated request returns coupon details and full payment URL.
        """
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = self.mock_user_response
        mock_supabase_client.return_value = mock_client

        seller_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_get_seller.return_value = SellerResponse(
            id=seller_id,
            business_name="Kofi Electronics",
            contact_email="kofi@example.com",
            agreed_discount="20.00",
            settlement_type="mobile_money",
            settlement_bank_code="MTN",
            settlement_account_number="0240000000",
            settlement_account_name="Kofi Mensah",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        coupon_id = uuid4()
        mock_get_coupon.return_value = CouponResponse(
            id=coupon_id,
            seller_id=seller_id,
            code="KOFI-ELECTR-123456",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        headers = {"Authorization": "Bearer valid_admin_token"}
        resp = self.client.get(f"/api/sellers/{seller_id}/coupon", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["code"], "KOFI-ELECTR-123456")
        self.assertIn("/pay/KOFI-ELECTR-123456", data["payment_url"])

    @patch("app.auth.get_supabase_client")
    @patch("app.services.seller_service.get_seller")
    @patch("app.services.coupon_service.get_active_coupon_for_seller")
    def test_get_seller_qr_png_and_svg_authenticated(
        self,
        mock_get_coupon,
        mock_get_seller,
        mock_supabase_client,
    ):
        """
        Authenticated requests return image/png and image/svg+xml streams.
        """
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = self.mock_user_response
        mock_supabase_client.return_value = mock_client

        seller_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_get_seller.return_value = SellerResponse(
            id=seller_id,
            business_name="Kofi Electronics",
            contact_email="kofi@example.com",
            agreed_discount="20.00",
            settlement_type="mobile_money",
            settlement_bank_code="MTN",
            settlement_account_number="0240000000",
            settlement_account_name="Kofi Mensah",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        mock_get_coupon.return_value = CouponResponse(
            id=uuid4(),
            seller_id=seller_id,
            code="KOFI-ELECTR-123456",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        headers = {"Authorization": "Bearer valid_admin_token"}

        # PNG format
        resp_png = self.client.get(f"/api/sellers/{seller_id}/qr?format=png", headers=headers)
        self.assertEqual(resp_png.status_code, 200)
        self.assertEqual(resp_png.headers["content-type"], "image/png")
        self.assertTrue(resp_png.content.startswith(b"\x89PNG\r\n\x1a\n"))

        # SVG format
        resp_svg = self.client.get(f"/api/sellers/{seller_id}/qr?format=svg", headers=headers)
        self.assertEqual(resp_svg.status_code, 200)
        self.assertTrue(resp_svg.headers["content-type"].startswith("image/svg+xml"))
        self.assertIn("<svg", resp_svg.text)

    @patch("app.auth.get_supabase_client")
    @patch("app.services.seller_service.get_seller")
    @patch("app.services.coupon_service.regenerate_coupon_for_seller")
    def test_regenerate_seller_coupon_authenticated(
        self,
        mock_regenerate_coupon,
        mock_get_seller,
        mock_supabase_client,
    ):
        """
        Authenticated request deactivates previous coupon and returns new coupon with payment URL.
        """
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = self.mock_user_response
        mock_supabase_client.return_value = mock_client

        seller_id = uuid4()
        now = datetime.now(timezone.utc)
        mock_get_seller.return_value = SellerResponse(
            id=seller_id,
            business_name="Kofi Electronics",
            contact_email="kofi@example.com",
            agreed_discount="20.00",
            settlement_type="mobile_money",
            settlement_bank_code="MTN",
            settlement_account_number="0240000000",
            settlement_account_name="Kofi Mensah",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        new_coupon_id = uuid4()
        mock_regenerate_coupon.return_value = CouponResponse(
            id=new_coupon_id,
            seller_id=seller_id,
            code="KOFI-ELECTR-NEW999",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        headers = {"Authorization": "Bearer valid_admin_token"}
        resp = self.client.post(f"/api/sellers/{seller_id}/regenerate-coupon", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["code"], "KOFI-ELECTR-NEW999")
        self.assertIn("/pay/KOFI-ELECTR-NEW999", data["payment_url"])


if __name__ == "__main__":
    unittest.main()
