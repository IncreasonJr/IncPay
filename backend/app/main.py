import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import check_critical_settings, get_settings
from app.limiter import limiter
from app.routers import auth, health, payments, sellers, transactions, webhooks

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="IncPay API",
    description="Payment-bridge platform connecting sellers and customers",
    version="0.1.0",
)

# Attach slowapi rate limiter state and 429 exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Strict CORS origin parsing: exclude wildcards from credentialed origins
allowed_origins = [
    origin.strip()
    for origin in settings.FRONTEND_URL.split(",")
    if origin.strip() and origin.strip() != "*"
]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Startup audit check for critical credentials
@app.on_event("startup")
def on_startup():
    warnings = check_critical_settings(settings)
    for warning in warnings:
        logger.warning(f"[SECURITY WARNING] {warning}")


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
