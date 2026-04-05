from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import communicate, invoice, transform, validate
from app.database import Base, engine

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="E-Invoice API",
    description="API ecosystem for creating, validating, transforming and sending UBL 2.1 XML invoices",
    version="1.0.0"
)

# Open CORS for local dev and POC testing (browser + Vite on another origin).
# Tighten allow_origins for production (e.g. your Vercel domain only).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect routers
app.include_router(invoice.router)
app.include_router(transform.router)
app.include_router(validate.router)
app.include_router(communicate.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {
        "message": "Welcome to the E-Invoice API",
        "docs": "/docs"
    }