from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, health, payments, sellers, transactions, webhooks

settings = get_settings()

app = FastAPI(
    title="IncPay API",
    description="Payment-bridge platform connecting sellers and customers",
    version="0.1.0",
)

# Configure CORS using FRONTEND_URL from environment settings
allowed_origins = [
    origin.strip()
    for origin in settings.FRONTEND_URL.split(",")
    if origin.strip()
]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sellers.router)
app.include_router(payments.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)


@app.get("/", summary="Root endpoint")
def root():
    return {
        "name": "IncPay API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
