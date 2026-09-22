# IncPay Database Migrations

This directory contains SQL migrations for the IncPay database schema on Supabase (PostgreSQL).

All monetary fields are stored in **Ghanaian Cedis (GHS / ₵)** as `NUMERIC(12, 2)` (not in pesewas).

---

## Migration 001: Initial Schema

File: `001_initial_schema.sql`

### Tables Created:
1. **`sellers`**:
   - Stores merchant/seller profiles.
   - `agreed_discount`: The total discount percentage $D$ agreed with IncPay (e.g. `20.00%`).
   - Constraint: `0 < agreed_discount < 100`.
   - `paystack_subaccount_code` & `paystack_subaccount_id`: For automated Paystack split settlement.
2. **`coupons`**:
   - Stores each seller's unique coupon code for customer QR scanning and landing pages.
   - Foreign key to `sellers(id)` with `ON DELETE CASCADE`.
3. **`transactions`**:
   - Records every payment-bridge checkout.
   - Breakdown:
     - `listed_amount`: Original product/service price (₵).
     - `customer_discount_amount`: Half of $D$ ($D/2$) deducted for the customer (₵).
     - `amount_paid`: Actual amount charged to the customer ($P - D/2$) (₵).
     - `platform_cut_amount`: Half of $D$ ($D/2$) retained by IncPay (₵).
     - `seller_payout_amount`: Payout received by the seller ($P - D$) (₵).
   - Status: `'pending'`, `'success'`, or `'failed'`.
4. **`transaction_logs`**:
   - Audit trail capturing events (`payment_initiated`, `webhook_received`, `payment_success`, etc.) and JSON payloads.

---

## How to Apply Migrations

> [!IMPORTANT]
> Migrations are manual. Do NOT auto-run migrations from the backend application at this stage.

### Option 1: Via Supabase Studio (Recommended)
1. Open your project on [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to the **SQL Editor** from the left-hand navigation.
3. Click **New Query**.
4. Copy and paste the entire contents of `backend/migrations/001_initial_schema.sql`.
5. Click **Run** (or `Ctrl+Enter`).
6. Confirm in the **Table Editor** that `sellers`, `coupons`, `transactions`, and `transaction_logs` are created.

### Option 2: Via `psql` CLI
If you have PostgreSQL client tools installed and your Supabase database connection URI (available under Project Settings → Database → Connection string → URI):

```bash
psql "postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres" -f backend/migrations/001_initial_schema.sql
```
