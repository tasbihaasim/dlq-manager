from sqlalchemy import Column
from app.database import Base

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    # your columns here

class DLQItem(Base):
    __tablename__ = "dlq_items"
    # your columns here