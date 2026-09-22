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
