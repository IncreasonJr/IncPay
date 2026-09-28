# IncPay Frontend

React single-page application built with Vite and Tailwind CSS. Provides the customer payment and receipt interface as well as the administrative portal for merchant management, QR generation, and transaction ledger auditing.

---

## Getting Started

### Prerequisites
- Node.js 18+
- npm or pnpm

### Local Development Setup
1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Configure `VITE_API_URL` (typically `http://localhost:8000`), `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`.

3. Run Vite development server:
   ```bash
   npm run dev
   ```
   Runs locally on [http://localhost:5173](http://localhost:5173).

4. Production build:
   ```bash
   npm run build
   ```

---

## Production Deployment (Vercel)

The IncPay frontend is pre-configured for seamless continuous deployment to [Vercel](https://vercel.com).

### 1. Deployment Steps
1. Log into your [Vercel Dashboard](https://vercel.com) and click **Add New...** → **Project**.
2. Connect your GitHub repository.
3. Configure the build parameters:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 2. Required Production Environment Variables
Configure these under **Environment Variables** in the Vercel Project Settings:

| Variable | Example Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://incpay-backend.onrender.com` | Deployed Render backend base URL (no trailing slash) |
| `VITE_SUPABASE_URL` | `https://your-project.supabase.co` | Production Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbGciOi...` | Public client anon key for browser Supabase client |

### 3. SPA Route Fallbacks (`vercel.json`)
Client-side routing via React Router is supported across all paths (e.g. `/pay/:couponCode`, `/pay/success`, `/admin/sellers`, `/admin/transactions`) using the included [`vercel.json`](vercel.json) rewrite rule:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
This ensures refreshing deep links in the browser does not trigger 404 errors on Vercel.
