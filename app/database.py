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


def _add_column_if_missing(conn, table: str, col: str, ddl: str, is_pg: bool) -> None:
    if is_pg:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}"))
    else:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def ensure_schema_compatibility():
    """
    Add newer columns when running against an older SQLite DB file.
    This keeps local development data usable without manual migration steps.
    New *tables* are handled by Base.metadata.create_all; only column
    additions to pre-existing tables need to be listed here.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    is_pg = DATABASE_URL.startswith("postgresql")

    # ---- invoices table ----
    if "invoices" in existing_tables:
        invoice_columns = {col["name"] for col in inspector.get_columns("invoices")}
        invoice_additions = {
            "seller_name":   "TEXT NOT NULL DEFAULT ''",
            "seller_address":"TEXT NOT NULL DEFAULT ''",
            "seller_email":  "TEXT NOT NULL DEFAULT ''",
            "buyer_name":    "TEXT NOT NULL DEFAULT ''",
            "buyer_address": "TEXT NOT NULL DEFAULT ''",
            "buyer_email":   "TEXT NOT NULL DEFAULT ''",
            # New columns added in the expanded feature set
            "owner_id":      "TEXT",
            "template_id":   "TEXT",
            "issue_date":    "DATE",
        }
        with engine.begin() as conn:
            for col, ddl in invoice_additions.items():
                if col not in invoice_columns:
                    _add_column_if_missing(conn, "invoices", col, ddl, is_pg)

    # ---- line_items table ----
    if "line_items" in existing_tables:
        line_item_columns = {col["name"] for col in inspector.get_columns("line_items")}
        if "item_number" not in line_item_columns:
            with engine.begin() as conn:
                _add_column_if_missing(
                    conn, "line_items", "item_number",
                    "TEXT NOT NULL DEFAULT ''", is_pg
                )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()