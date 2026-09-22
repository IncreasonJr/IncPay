-- ============================================================================
-- IncPay Initial Database Schema Migration
-- Version: 001
-- Description: Core schema for IncPay payment-bridge platform.
-- Currency: All monetary amounts are in Ghanaian Cedis (GHS / ₵).
-- ============================================================================

-- 1. Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Trigger function to automatically update the 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- Table: sellers
-- Represents business owners on IncPay who offer an agreed discount D (%).
-- IncPay passes D/2 as customer discount and keeps D/2 as platform revenue.
-- Example: agreed_discount = 20.00 (₵10,000 listed price -> ₵1,000 off for customer, ₵1,000 to IncPay, ₵8,000 to seller)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sellers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT,
    agreed_discount NUMERIC(5, 2) NOT NULL,
    paystack_subaccount_code TEXT,
    paystack_subaccount_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_agreed_discount CHECK (agreed_discount > 0 AND agreed_discount < 100)
);

-- Trigger for sellers updated_at
CREATE OR REPLACE TRIGGER trg_sellers_updated_at
BEFORE UPDATE ON sellers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- Table: coupons
-- Represents unique QR/coupon codes issued to sellers.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    code TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger for coupons updated_at
CREATE OR REPLACE TRIGGER trg_coupons_updated_at
BEFORE UPDATE ON coupons
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Index for fast coupon lookup by code
CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code);

-- ----------------------------------------------------------------------------
-- Table: transactions
-- Records payment-bridge transactions routed through Paystack.
-- All monetary amounts stored as numeric in Ghanaian Cedis (GHS / ₵).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE RESTRICT,
    coupon_id UUID NOT NULL REFERENCES coupons(id) ON DELETE RESTRICT,
    paystack_reference TEXT NOT NULL UNIQUE,
    currency TEXT NOT NULL DEFAULT 'GHS',
    listed_amount NUMERIC(12, 2) NOT NULL,            -- Original price before discount (₵)
    customer_discount_amount NUMERIC(12, 2) NOT NULL, -- D/2 in GHS (₵)
    amount_paid NUMERIC(12, 2) NOT NULL,              -- What customer paid: listed - customer_discount (₵)
    platform_cut_amount NUMERIC(12, 2) NOT NULL,      -- D/2 in GHS (₵) kept by IncPay
    seller_payout_amount NUMERIC(12, 2) NOT NULL,     -- What seller receives: listed - (2 * customer_discount) (₵)
    status TEXT NOT NULL DEFAULT 'pending',
    customer_email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_transaction_status CHECK (status IN ('pending', 'success', 'failed'))
);

-- Trigger for transactions updated_at
CREATE OR REPLACE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Indexes for transaction lookups
CREATE INDEX IF NOT EXISTS idx_transactions_paystack_reference ON transactions(paystack_reference);
CREATE INDEX IF NOT EXISTS idx_transactions_seller_id ON transactions(seller_id);

-- ----------------------------------------------------------------------------
-- Table: transaction_logs
-- Audit log of lifecycle events (initiation, webhook callbacks, successes, failures).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying logs by transaction
CREATE INDEX IF NOT EXISTS idx_transaction_logs_transaction_id ON transaction_logs(transaction_id);
