"""
Schemas Package.

In IncPay's architecture, we are not using an ORM; data access occurs directly
via the Supabase Python client and Pydantic models. Therefore, the models defined
in `app.models` (e.g., `SellerCreate`, `SellerResponse`, `TransactionCreate`, etc.)
double as the validation schemas and serialization contracts for incoming requests
and outgoing responses.

API-specific composite schemas or view-models (e.g. nested seller+coupon summaries)
can be introduced here in Phase 2 if and when they deviate from the base domain models.
"""
