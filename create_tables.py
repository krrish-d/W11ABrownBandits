from app.database import engine, Base
from app.models.invoice import Invoice, LineItem

Base.metadata.create_all(bind=engine)
print("Tables created!")