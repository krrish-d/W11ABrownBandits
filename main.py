from fastapi import FastAPI
from app.routers import invoice, transform
from app.database import Base, engine

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="E-Invoice API",
    description="API ecosystem for creating, validating, transforming and sending UBL 2.1 XML invoices",
    version="1.0.0"
)

# Connect routers
app.include_router(invoice.router)
app.include_router(transform.router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "E-Invoice API",
        "version": "1.0.0"
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to the E-Invoice API",
        "docs": "/docs"
    }