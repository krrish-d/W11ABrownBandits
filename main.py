from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---- Routers (original) ----
from app.routers import communicate, invoice, transform, validate

# ---- Routers (new features) ----
from app.routers import auth, clients, payments, recurring, audit, dashboard, templates, webhooks

from app.database import Base, engine, ensure_schema_compatibility

# ---- Ensure all models are registered with SQLAlchemy before create_all ----
import app.models.invoice          # noqa: F401
import app.models.communication    # noqa: F401
import app.models.user             # noqa: F401
import app.models.client           # noqa: F401
import app.models.payment          # noqa: F401
import app.models.recurring        # noqa: F401
import app.models.audit            # noqa: F401
import app.models.template         # noqa: F401
import app.models.invoice_import   # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----- Startup -----
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()

    from app.services.scheduler import start_scheduler
    start_scheduler()

    yield

    # ----- Shutdown -----
    from app.services.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(
    title="E-Invoice API",
    description=(
        "API ecosystem for creating, validating, transforming and sending UBL 2.1 XML invoices. "
        "Includes auth, client management, payment tracking, dashboard analytics, "
        "recurring invoices, audit logs, branded templates, and optional accounting webhooks (stubs)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- v1 routers ----
app.include_router(invoice.router)
app.include_router(invoice.legacy_router)
app.include_router(transform.router)
app.include_router(validate.router)
app.include_router(communicate.router)

# ---- New feature routers ----
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(payments.router)
app.include_router(recurring.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(templates.router)
app.include_router(webhooks.router)

# ---- v2 versions of original routers ----
app.include_router(invoice.router, prefix="/v2")
app.include_router(transform.router, prefix="/v2")
app.include_router(validate.router, prefix="/v2")
app.include_router(communicate.router, prefix="/v2")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "message": "Welcome to the E-Invoice API",
        "docs": "/docs",
        "version": "2.0.0",
    }
