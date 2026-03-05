from fastapi import FastAPI

app = FastAPI(
    title="E-Invoice API",
    description="API ecosystem for creating, validating, transforming and sending UBL invoices",
    version="1.0.0"
)

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