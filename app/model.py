from sqlalchemy import Column
from app.database import Base
from sqlalchemy import Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")

class DLQItem(Base):
    __tablename__ = "dlq_items"
    id = Column(Integer, primary_key=True, index=True)
    webhook_event = relationship("WebhookEvent")
    webhook_event_id = Column(Integer, ForeignKey("webhook_events.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  
    retry_count = Column(Integer, default=0)
    error_message = Column(String, nullable=True)