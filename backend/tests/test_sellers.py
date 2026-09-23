import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.services.seller_service import calculate_percentage_charge


class TestSellerOperations(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_user = MagicMock()
        self.mock_user.id = str(uuid4())
        self.mock_user.email = "admin@incpay.com"

        self.mock_user_response = MagicMock()
        self.mock_user_response.user = self.mock_user

    def test_percentage_charge_calculation(self):
        """
        Formula: D / (200 - D) * 100
        """
        # D = 20 -> 20 / 180 * 100 = 11.11%
        self.assertEqual(calculate_percentage_charge(20.0), 11.11)
        self.assertEqual(calculate_percentage_charge(Decimal("20.00")), 11.11)

        # D = 10 -> 10 / 190 * 100 = 5.26%
        self.assertEqual(calculate_percentage_charge(10.0), 5.26)

        # D = 50 -> 50 / 150 * 100 = 33.33%
        self.assertEqual(calculate_percentage_charge(50.0), 33.33)

        # Boundary checks
        with self.assertRaises(ValueError):
            calculate_percentage_charge(0.0)

        with self.assertRaises(ValueError):
            calculate_percentage_charge(200.0)

    def test_sellers_endpoints_unauthenticated(self):
        """All seller endpoints require admin authentication."""
        self.assertEqual(self.client.get("/api/sellers").status_code, 401)
        self.assertEqual(self.client.post("/api/sellers", json={}).status_code, 401)
        self.assertEqual(self.client.get("/api/banks").status_code, 401)
        self.assertEqual(self.client.get("/api/mobile-money-providers").status_code, 401)

    def test_get_mobile_money_providers_authenticated(self):
        """Returns the supported Ghanaian telcos."""
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = self.mock_user_response

        with patch("app.auth.get_supabase_client", return_value=mock_supabase):
            response = self.client.get(
                "/api/mobile-money-providers",
                headers={"Authorization": "Bearer test_token"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            codes = [p["code"] for p in data]
            self.assertIn("MTN", codes)
            self.assertIn("VOD", codes)
            self.assertIn("ATL", codes)

    def test_get_banks_authenticated(self):
        """Returns list of banks."""
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = self.mock_user_response

        with patch("app.auth.get_supabase_client", return_value=mock_supabase):
            response = self.client.get(
                "/api/banks",
                headers={"Authorization": "Bearer test_token"},
            )
            self.assertEqual(response.status_code, 200)
            banks = response.json()
            self.assertIsInstance(banks, list)
            self.assertGreater(len(banks), 0)

    def test_create_seller_success_mocked(self):
        """Verify full seller onboarding flow with mocked Paystack and Supabase."""
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = self.mock_user_response

        seller_id = str(uuid4())
        mock_db_row = {
            "id": seller_id,
            "business_name": "Kofi Store",
            "contact_email": "kofi@store.gh",
            "contact_phone": "+233241112222",
            "agreed_discount": "20.00",
            "settlement_type": "mobile_money",
            "settlement_bank_code": "MTN",
            "settlement_account_number": "0241112222",
            "settlement_account_name": "Kofi Mensah",
            "paystack_subaccount_code": "ACCT_test12345",
            "paystack_subaccount_id": "98765",
            "is_active": True,
            "created_at": "2026-09-23T09:00:00Z",
            "updated_at": "2026-09-23T09:00:00Z",
        }
        mock_insert_res = MagicMock()
        mock_insert_res.data = [mock_db_row]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_res

        mock_paystack_res = {
            "subaccount_code": "ACCT_test12345",
            "id": 98765,
        }

        with patch("app.auth.get_supabase_client", return_value=mock_supabase), \
             patch("app.services.seller_service.get_supabase_client", return_value=mock_supabase), \
             patch("app.services.paystack_service.create_subaccount", return_value=mock_paystack_res):

            payload = {
                "business_name": "Kofi Store",
                "contact_email": "kofi@store.gh",
                "contact_phone": "+233241112222",
                "agreed_discount": 20.0,
                "settlement_type": "mobile_money",
                "settlement_bank_code": "MTN",
                "settlement_account_number": "0241112222",
                "settlement_account_name": "Kofi Mensah",
            }
            response = self.client.post(
                "/api/sellers",
                headers={"Authorization": "Bearer test_token"},
                json=payload,
            )
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertEqual(data["business_name"], "Kofi Store")
            self.assertEqual(data["paystack_subaccount_code"], "ACCT_test12345")
            self.assertEqual(data["settlement_type"], "mobile_money")


if __name__ == "__main__":
    unittest.main()
