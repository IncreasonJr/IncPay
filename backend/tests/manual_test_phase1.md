# Phase 1 Manual Verification Guide: Supabase & Python Data Layer

This guide walks through verifying the database schema and Python data layer from a Python REPL after applying the migration in Supabase.

---

## 1. Prerequisites

1. **Apply Migration**:
   - Open your Supabase project dashboard → **SQL Editor**.
   - Paste and execute `backend/migrations/001_initial_schema.sql`.
   - Verify that tables `sellers`, `coupons`, `transactions`, and `transaction_logs` appear in Table Editor.

2. **Configure `.env`**:
   Ensure `backend/.env` contains your actual Supabase credentials:
   ```dotenv
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-service-or-anon-key
   FRONTEND_URL=http://localhost:5173
   ENVIRONMENT=development
   ```

3. **Activate Virtual Environment**:
   ```bash
   cd ~/Desktop/IncPay/backend
   source .venv/bin/activate
   ```

---

## 2. REPL Verification Steps

Launch Python REPL:
```bash
python3
```

Execute the following test snippet line-by-line:

### A. Test Seller Creation & Retrieval
```python
from decimal import Decimal
from app.models import SellerCreate, SellerUpdate
from app.services import (
    create_seller,
    get_seller,
    list_sellers,
    update_seller,
)

# 1. Create a seller with agreed discount D = 20.00%
seller_in = SellerCreate(
    business_name="Kofi Electronics",
    contact_email="kofi@example.com",
    contact_phone="+233240000000",
    agreed_discount=Decimal("20.00"),  # 20% total discount
)
seller = create_seller(seller_in)
print("Created seller:", seller.id, seller.business_name, f"{seller.agreed_discount}%")
assert seller is not None
assert seller.business_name == "Kofi Electronics"

# 2. Retrieve seller by ID
fetched = get_seller(seller.id)
print("Fetched seller:", fetched.id, fetched.contact_email)
assert fetched.id == seller.id

# 3. List sellers
sellers = list_sellers(limit=10)
print(f"Total sellers retrieved: {len(sellers)}")
```

---

### B. Test Coupon Creation & Lookup
```python
from app.models import CouponCreate
from app.services import create_coupon, get_coupon_by_code, list_coupons_for_seller

# 1. Create a coupon code for Kofi Electronics
coupon_in = CouponCreate(
    seller_id=seller.id,
    code="KOFI20",
)
coupon = create_coupon(coupon_in)
print("Created coupon:", coupon.code, "for seller:", coupon.seller_id)
assert coupon is not None
assert coupon.code == "KOFI20"

# 2. Retrieve coupon by code
found_coupon = get_coupon_by_code("kofi20")  # Case-insensitive
print("Found coupon by code:", found_coupon.code, "Active:", found_coupon.is_active)
assert found_coupon.id == coupon.id

# 3. List coupons for seller
seller_coupons = list_coupons_for_seller(seller.id)
print(f"Seller coupons count: {len(seller_coupons)}")
```

---

### C. Test Transaction Split Calculation & Creation (₵ Cedis)
```python
from app.models import TransactionCreate, TransactionStatus
from app.services import (
    create_transaction,
    get_transaction_by_reference,
    update_transaction_status,
)

# Example: Listed price ₵10,000.00 with D = 20.00%
# Customer discount (D/2 = 10%) = ₵1,000.00 -> Amount paid = ₵9,000.00
# Platform cut (D/2 = 10%) = ₵1,000.00
# Seller payout = ₵8,000.00
split = TransactionCreate.calculate_split(
    listed_amount=Decimal("10000.00"),
    agreed_discount=seller.agreed_discount,
)
print("Calculated Cedis split:", split)

tx_in = TransactionCreate(
    seller_id=seller.id,
    coupon_id=coupon.id,
    paystack_reference="T_TEST_1001",
    customer_email="customer@example.com",
    **split,
)
tx = create_transaction(tx_in)
print("Recorded transaction:", tx.paystack_reference, f"₵{tx.amount_paid}", tx.status)
assert tx is not None
assert tx.amount_paid == Decimal("9000.00")
assert tx.platform_cut_amount == Decimal("1000.00")
assert tx.seller_payout_amount == Decimal("8000.00")

# Update transaction status
updated_tx = update_transaction_status("T_TEST_1001", TransactionStatus.SUCCESS)
print("Updated transaction status:", updated_tx.status)
assert updated_tx.status == TransactionStatus.SUCCESS
```

---

### D. Test Transaction Event Logging
```python
from app.services import log_event

log_entry = log_event(
    event="payment_success",
    transaction_id=tx.id,
    payload={"gateway": "paystack", "channel": "card", "currency": "GHS"},
)
print("Recorded log entry:", log_entry.id, log_entry.event_type)
assert log_entry is not None
assert log_entry.event_type == "payment_success"
```

---

### E. Cleanup (Optional)
```python
from app.services import delete_seller

# Deleting the seller cascades and deletes associated coupons
deleted = delete_seller(seller.id)
print("Deleted test seller:", deleted)
```
