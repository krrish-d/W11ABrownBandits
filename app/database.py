import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./invoices.db")

# Some providers still return postgres:// URLs; SQLAlchemy expects postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_compatibility():
    """
    Add newer columns when running against an older SQLite DB file.
    This keeps local development data usable without manual migration steps.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "invoices" in inspector.get_table_names():
        invoice_columns = {col["name"] for col in inspector.get_columns("invoices")}
        invoice_additions = {
            "seller_name": "TEXT NOT NULL DEFAULT ''",
            "seller_address": "TEXT NOT NULL DEFAULT ''",
            "seller_email": "TEXT NOT NULL DEFAULT ''",
            "buyer_name": "TEXT NOT NULL DEFAULT ''",
            "buyer_address": "TEXT NOT NULL DEFAULT ''",
            "buyer_email": "TEXT NOT NULL DEFAULT ''",
        }
        with engine.begin() as conn:
            for col, ddl in invoice_additions.items():
                if col not in invoice_columns:
                    conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {col} {ddl}"))

    if "line_items" in inspector.get_table_names():
        line_item_columns = {col["name"] for col in inspector.get_columns("line_items")}
        if "item_number" not in line_item_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE line_items ADD COLUMN item_number TEXT NOT NULL DEFAULT ''"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()