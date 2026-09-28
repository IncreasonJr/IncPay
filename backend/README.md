# IncPay Backend

FastAPI backend service for IncPay, handling API routing, authentication, Supabase database operations, and Paystack payment processing.

---

## Requirements
- Python 3.11+ (`python3` and `pip3`)

---

## Setup & Installation

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Update .env with your credentials
   ```

---

## Running the Backend

Start the Uvicorn development server with auto-reload:

```bash
uvicorn app.main:app --reload
```

By default, the server runs on `http://localhost:8000`.

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Database Health Check**: [http://localhost:8000/api/health/db](http://localhost:8000/api/health/db)

---

## Environment Variables

| Variable | Description |
| :--- | :--- |
| `SUPABASE_URL` | Supabase project API URL |
| `SUPABASE_KEY` | Supabase API key (anon or service key) |
| `PAYSTACK_SECRET_KEY` | Paystack secret key |
| `PAYSTACK_PUBLIC_KEY` | Paystack public key |
| `FRONTEND_URL` | Allowed origin for CORS (e.g. `http://localhost:5173`) |
| `ENVIRONMENT` | Environment name (e.g. `development`, `production`) |

---

## Local Webhook Testing with Ngrok

To receive live Paystack webhook callbacks on your local development machine:

### 1. Install Ngrok

- **macOS (Homebrew):** `brew install ngrok/ngrok/ngrok`
- **Linux (Snap):** `sudo snap install ngrok`
- **Linux (Apt):**
  ```bash
  curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
    | sudo tee /etc/apt/sources.list.d/ngrok.list \
    && sudo apt update && sudo apt install ngrok
  ```
- **npm:** `npm install -g ngrok`

Authenticate your agent (get your authtoken from [dashboard.ngrok.com](https://dashboard.ngrok.com)):
```bash
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

### 2. Expose Local Port 8000

With your FastAPI server running on `http://localhost:8000`, start the tunnel:

```bash
ngrok http 8000
```

Ngrok provides a public forwarding URL such as `https://abcdef123.ngrok-free.app`.

### 3. Configure Paystack Webhook URL

1. Go to your [Paystack Dashboard](https://dashboard.paystack.com/#/settings/developer).
2. Navigate to **Settings** → **API Keys & Webhooks**.
3. Under **Test Webhook URL** (or Live Webhook URL in production), configure:
   ```
   https://<ngrok-id>.ngrok-free.app/api/webhooks/paystack
   ```
4. Save changes.

### 4. Enabled Webhook Events

Ensure the following events are enabled to receive payment notifications:
- `charge.success`: Triggered when customer completes payment and split settlement succeeds.
- `charge.failed`: Triggered when customer transaction fails or is declined.
- `refund.processed`: Audit-logged without mutating underlying transaction.

---

## Security Hardening & Rate Limiting

IncPay enforces production-grade security standards and rate limiting on all public endpoints via `slowapi`:

| Endpoint | Rate Limit | Purpose |
| :--- | :--- | :--- |
| `GET /api/public/coupon/{code}` | 30 / min | Prevents coupon code enumeration and scraping |
| `POST /api/public/initialize-payment` | 10 / min | Prevents checkout initialization abuse |
| `GET /api/public/verify-payment/{reference}` | 60 / min | Allows rapid client polling upon redirect |
| `GET /api/public/receipt/{reference}` | 10 / min | Protects in-memory PDF rendering from DoS |

### Payment Amount Bounds
- **Minimum listed amount**: `MIN_PAYMENT_AMOUNT = 1.0` (₵1.00)
- **Maximum listed amount**: `MAX_PAYMENT_AMOUNT = 50000.0` (₵50,000.00)
- Amounts are strictly validated as `Decimal` and quantized to 2 decimal places using `ROUND_HALF_UP`.

### Security Headers & Data Leakage Prevention
- **Security Headers**: Injected across all responses (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `HSTS` in production).
- **Public Data Isolation**: Public endpoints sanitize responses to guarantee no seller bank account, phone number, contact email, subaccount ID, platform revenue cut, or internal database UUIDs are leaked.
- **HMAC Constant-Time Verification**: Webhook signatures are compared via `hmac.compare_digest` to prevent timing attacks.

---

## Running Automated Tests

Run the complete test suite (82 passing tests covering edge cases, security, and the full E2E lifecycle):

```bash
# Run all unit, edge case, and end-to-end tests
.venv/bin/python3 -m unittest discover -s tests -v

# Run specific test suites
.venv/bin/python3 -m unittest tests/test_edge_cases_security.py -v
.venv/bin/python3 -m unittest tests/test_end_to_end.py -v
```


