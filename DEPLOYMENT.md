# IncPay — Production Deployment Runbook

Complete guide for deploying IncPay to production:
- **Backend**: [Render](https://render.com) (FastAPI Python web service)
- **Frontend**: [Vercel](https://vercel.com) (React + Vite single-page application)
- **Database & Auth**: [Supabase](https://supabase.com) (PostgreSQL database & admin auth)
- **Payments**: [Paystack](https://paystack.com) (Live Ghanaian Cedis settlement)
- **Email**: [Resend](https://resend.com) (Transactional PDF receipt delivery)

---

## Pre-Deployment Preparation

Before initiating deployment:
1. Ensure your Paystack account is fully verified with KYC approved and Live API keys enabled.
2. Ensure you have accounts on Render, Vercel, Supabase, and Resend.
3. Push your repository to GitHub (public or private).
4. Run the pre-deployment data purge script to wipe all development/test records from Supabase:
   ```bash
   python3 backend/scripts/purge_test_data.py
   ```
   Type `PURGE ALL` when prompted to purge test transactions, logs, coupons, and sellers.

---

## 1. Backend Deployment — Render

### 1.1 Create Web Service
1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository containing IncPay.
4. Configure service details:
   - **Name**: `incpay-backend`
   - **Region**: Choose the closest region (e.g. Frankfurt / EU Central or London).
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

> [!NOTE]
> Render's Free tier spins down after 15 minutes of inactivity. When a customer scans a QR code, a cold start takes ~30 to 50 seconds. For a live commercial launch, upgrade to the **Starter Plan ($7/month)** for 24/7 high availability and instantaneous responses.

### 1.2 Configure Environment Variables
Under the **Environment** tab on Render, add the following variables:

| Variable | Value / Description | Sensitive? |
| :--- | :--- | :--- |
| `SUPABASE_URL` | Your Supabase project URL (e.g. `https://xxxx.supabase.co`) | No |
| `SUPABASE_KEY` | Your Supabase `service_role` secret key | **YES** |
| `PAYSTACK_SECRET_KEY` | Your Paystack **Live** secret key (`sk_live_...`) | **YES** |
| `PAYSTACK_PUBLIC_KEY` | Your Paystack **Live** public key (`pk_live_...`) | **YES** |
| `FRONTEND_URL` | `https://incpay.vercel.app` (or your initial custom domain) | No |
| `PAYMENT_PAGE_BASE_URL`| `https://incpay.vercel.app` | No |
| `ENVIRONMENT` | `production` | No |
| `MIN_PAYMENT_AMOUNT` | `1.0` | No |
| `MAX_PAYMENT_AMOUNT` | `50000.0` | No |
| `RESEND_API_KEY` | Your production Resend API key (`re_...`) | **YES** |
| `RESEND_FROM_EMAIL` | Verified sender domain (e.g. `receipts@yourdomain.com`) or `onboarding@resend.dev` | No |

5. Click **Create Web Service**.
6. Wait for the build and deployment to complete.
7. Note your public backend URL: `https://incpay-backend.onrender.com`.
8. Verify in your browser: `https://incpay-backend.onrender.com/health` returns `{"status":"ok"}`.

---

## 2. Frontend Deployment — Vercel

### 2.1 Import Project
1. Log into your [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import the same GitHub repository.
4. Configure project settings:
   - **Project Name**: `incpay`
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 2.2 Configure Environment Variables
Under **Environment Variables**, configure the 3 production variables:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://incpay-backend.onrender.com` | Your live Render backend URL (no trailing slash) |
| `VITE_SUPABASE_URL` | `https://xxxx.supabase.co` | Your live Supabase Project URL |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbG...` | Your Supabase public `anon` key |

5. Click **Deploy**.
6. Once deployed, note your Vercel URL: `https://incpay.vercel.app` (or your assigned Vercel subdomain).

---

## 3. Post-Deployment Linking & Verification

### 3.1 Update Backend CORS & Base URLs
1. In your Render Dashboard (`incpay-backend`):
   - Set `FRONTEND_URL` = `https://incpay.vercel.app` (or include both staging and prod: `https://incpay.vercel.app,http://localhost:5173`).
   - Set `PAYMENT_PAGE_BASE_URL` = `https://incpay.vercel.app`.
2. Click **Save Changes** and allow Render to trigger an automated redeploy.

### 3.2 Configure Paystack Live Webhooks
1. Open the [Paystack Dashboard](https://dashboard.paystack.com/#/settings/developer).
2. Switch toggle to **Live mode** in the top-left corner.
3. Navigate to **Settings** → **API Keys & Webhooks**.
4. In the **Live Webhook URL** field, set:
   ```
   https://incpay-backend.onrender.com/api/webhooks/paystack
   ```
5. Ensure the following events are enabled:
   - `charge.success`
   - `charge.failed`
6. Click **Save Changes**.

### 3.3 Paystack Live Keys Switch & Seller Migration
> [!IMPORTANT]
> **Subaccount Migration Notice**:
> Paystack subaccounts created in test mode (`ACCT_test_...`) cannot process real transactions with live keys. When switching to live keys:
> - Live secret and public keys must be configured in Render.
> - All merchants/sellers must be created freshly in the Admin Dashboard (`/admin/sellers`).
> - This provisions genuine live Paystack subaccounts (`ACCT_live_...`) with your commercial partner banks/MoMo telcos.

### 3.4 Full End-to-End Live Verification Test
1. Log into your production Admin Dashboard at `https://incpay.vercel.app/admin/sellers`.
2. Create a live seller with genuine bank or mobile money account details (e.g. agreed discount 20%).
3. Inspect the newly created seller:
   - Verify a live Paystack subaccount code was assigned.
   - Verify the generated coupon code and QR code.
4. Scan the QR code with a mobile device or navigate to `https://incpay.vercel.app/pay/{code}`.
5. Enter a test payment (e.g. ₵2.00).
6. Complete payment via Paystack checkout using a real mobile money wallet or debit card.
7. Confirm that:
   - The customer is redirected to the verified success screen.
   - The transaction appears in `/admin/transactions` with the exact 50/50 platform cut and seller payout split.
   - The customer receives an email with the official attached PDF receipt.
   - The PDF receipt can be downloaded directly from the admin dashboard.
8. Verify the split settlement in your [Paystack Live Dashboard](https://dashboard.paystack.com/#/transfers).

---

## 4. Troubleshooting & Maintenance

### Common Issues
- **CORS Error in Browser Console**:
  Verify that the exact protocol and domain in browser address bar (e.g. `https://incpay.vercel.app`) is included in `FRONTEND_URL` in Render.
- **Paystack Webhook 401 Unauthorized**:
  Verify that `PAYSTACK_SECRET_KEY` on Render exactly matches the **Live Secret Key** in Paystack Settings.
- **Client Route 404 on Refresh in Vercel**:
  Verify `frontend/vercel.json` exists in your repository with the SPA rewrites rule.
