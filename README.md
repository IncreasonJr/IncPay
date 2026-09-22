# IncPay

IncPay is a payment-bridge platform designed to seamlessly connect sellers and customers, facilitating escrow-backed transactions, flexible settlement flows, and secure multi-channel payments.

---

## Architecture Overview

- **Backend**: Python 3.11+ with FastAPI, Pydantic v2 Settings, and Uvicorn.
- **Frontend**: React 18 with Vite, Tailwind CSS, and React Router.
- **Database**: Supabase (PostgreSQL).
- **Payment Gateway**: Paystack.
- **Deployment Target**: Vercel.

---

## Project Structure

```text
IncPay/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── health.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   └── __init__.py
│   │   └── services/
│   │       └── __init__.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── api/
│   │   │   └── client.js
│   │   ├── pages/
│   │   │   └── Home.jsx
│   │   └── components/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── .env.example
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+ (`python3` and `pip3`)
- Node.js v18+ (tested on Node.js v20) and `npm`

---

### Backend Setup

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase and Paystack credentials
   ```

5. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
   The backend API will be running at `http://localhost:8000`.
   - API Docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health`
   - DB Health check: `http://localhost:8000/api/health/db`

---

### Frontend Setup

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```
   The frontend will be accessible at `http://localhost:5173`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `SUPABASE_URL` | Supabase Project URL | `https://your-project.supabase.co` |
| `SUPABASE_KEY` | Supabase Anon / Service API Key | `your-supabase-key` |
| `PAYSTACK_SECRET_KEY` | Paystack Secret Key | `sk_test_...` |
| `PAYSTACK_PUBLIC_KEY` | Paystack Public Key | `pk_test_...` |
| `FRONTEND_URL` | Allowed origin for CORS | `http://localhost:5173` |
| `ENVIRONMENT` | Runtime environment (`development`, `production`, etc.) | `development` |

### Frontend (`frontend/.env`)

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `VITE_API_URL` | Backend API Base URL | `http://localhost:8000` |
