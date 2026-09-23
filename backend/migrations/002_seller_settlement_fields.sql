-- ============================================================================
-- IncPay Migration 002: Add Settlement Fields to Sellers
-- Description: Adds payout bank/mobile money settlement destination fields.
-- Currency: Ghanaian Cedis (GHS / ₵).
-- ============================================================================

ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS settlement_type TEXT,
ADD COLUMN IF NOT EXISTS settlement_bank_code TEXT,
ADD COLUMN IF NOT EXISTS settlement_account_number TEXT,
ADD COLUMN IF NOT EXISTS settlement_account_name TEXT;

-- Add comment explaining settlement types
COMMENT ON COLUMN sellers.settlement_type IS 'Settlement destination type: bank or mobile_money';
COMMENT ON COLUMN sellers.settlement_bank_code IS 'Paystack settlement bank code or telco code (MTN, VOD, ATL)';
COMMENT ON COLUMN sellers.settlement_account_number IS 'Bank account number or mobile money number';
COMMENT ON COLUMN sellers.settlement_account_name IS 'Account holder name for settlement verification';
