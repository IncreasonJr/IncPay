-- ============================================================================
-- IncPay Migration 003: Customer Accounts & Personal IncPay Coupons
-- Description: Adds customers table and links transactions to customers.
-- ============================================================================

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    phone TEXT,
    supabase_user_id UUID UNIQUE,
    coupon_token TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger for customers updated_at
CREATE OR REPLACE TRIGGER trg_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Indexes for customer lookups
CREATE INDEX IF NOT EXISTS idx_customers_supabase_user_id ON customers(supabase_user_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_coupon_token ON customers(coupon_token);

-- Add customer_id reference to transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);

COMMENT ON TABLE customers IS 'Registered customer accounts with personal digital IncPay coupons';
COMMENT ON COLUMN customers.coupon_token IS 'Cryptographically signed coupon token identifying the customer';
COMMENT ON COLUMN transactions.customer_id IS 'Optional reference to the registered customer who made this payment';
