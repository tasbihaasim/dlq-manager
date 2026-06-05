from celery import Celery
import redis
import json
from kombu import Queue
from app.model import WebhookEvent, DLQItem
from app.database import SessionLocal
import os
from dotenv import load_dotenv
load_dotenv()

r = redis.from_url(os.getenv("REDIS_URL"))

celery_app = Celery(
    "tasks",
    broker=os.getenv("RABBITMQ_URL"),
    backend=os.getenv("REDIS_URL")
)

celery_app.conf.task_queues = [
    Queue(
        'celery',
        queue_arguments={
            'x-dead-letter-exchange': 'dlx', # RabbitMQ DLX configuration
            'x-dead-letter-routing-key': 'dlq'
        }
    ),
    Queue('dlq')
]

@celery_app.task(bind=True, max_retries=3)
def process_webhook_event(self, source: str, payload: dict):
    webhook_event = WebhookEvent(source=source, payload=payload, status="received")
    db = SessionLocal()
    try:
        db.add(webhook_event)
        db.commit()
        db.refresh(webhook_event)
        #raise Exception("forced failure") # simulate a failure to trigger retries and eventually the DLQ
        r.publish("webhook_events", json.dumps({"id": webhook_event.id, "source": source, "payload": payload, "status": "received"}))
    except Exception as e:
        db.rollback()
        if self.request.retries >= self.max_retries:
            # this is the last attempt, save to DLQ before giving up
            process_dlq_item.delay(webhook_event.id, source, payload, str(e))

        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    finally:
        db.close()
        
@celery_app.task(bind=True, queue="dlq")
def process_dlq_item(self, webhook_event_id: int, source: str, payload: dict, error_message: str):
    # This function should recieve source, payload and error message
    # create a DLQItem with the status = pending
    # save to PostgreSQL
    # This function will be called when the task fails after retries are exhausted
    dlq_item = DLQItem(webhook_event_id=webhook_event_id, status="pending", retry_count=0, error_message=error_message)
    db = SessionLocal()
    try:                    
        db.add(dlq_item)
        db.commit()
        db.refresh(dlq_item)
        r.publish("webhook_events", json.dumps({"id": dlq_item.id, "source": source, "payload": payload, "error_message": error_message, "status": "failed"}))
    except Exception as e:
        db.rollback()
        print(f"Failed to save DLQ item: {e}")
    finally:        
        db.close()  

    
