from fastapi import FastAPI, HTTPException
from fastapi import Request, Response
from app.database import SessionLocal
from app.model import WebhookEvent, DLQItem
import hmac, hashlib, os
from app.tasks import process_webhook_event



app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/webhook/{source}")
async def get_source(source: str, request:Request):
    secret = os.getenv("WEBHOOK_SECRET")
    raw_body = await request.body()
    payload = await request.json()
    expected = hmac.new(secret.encode(), raw_body, digestmod=hashlib.sha256).hexdigest() #creates an HMAC object using your secret as the key and SHA256 as the hashing algorithm on raw_body
    actual = request.headers.get("X-Zapier-Signature", "").split("sha256=")[-1] # retrieves the signature from the header and removes the "sha256=" prefix to get the actual signature value
    if not hmac.compare_digest(expected, actual):
        return {"error": "Invalid signature"}
    process_webhook_event.delay(source, payload)
    return Response(status_code=202)

@app.get("/webhook/dlq_item")
async def get_dlq_items():
    db = SessionLocal()
    try:
        items = db.query(DLQItem).all()
        return [{"id": i.id, "status": i.status, "error_message": i.error_message, "retry_count": i.retry_count} for i in items]
    finally:
        db.close()

@app.post("/retry/{dlq_item_id}")
async def retry_dlq_item(dlq_item_id: int):
    db = SessionLocal()
    try:
        dlq_item = db.query(DLQItem).filter(DLQItem.id == dlq_item_id).first()
        dlq_item.retry_count += 1
        if not dlq_item:
            raise HTTPException(status_code=404, detail="DLQ item not found")
        webhook_event = db.query(WebhookEvent).filter(WebhookEvent.id == dlq_item.webhook_event_id).first()
        if not webhook_event:
            raise HTTPException(status_code=404, detail="Webhook event not found")
        process_webhook_event.delay(webhook_event.source, webhook_event.payload)
        dlq_item.status = "retried"
        db.commit()
        return {"message": "Retry initiated"}
    finally:
        db.close()

@app.delete("/dlq_item/{dlq_item_id}")
async def delete_dlq_item(dlq_item_id: int):
    db = SessionLocal()
    try:
        dlq_item = db.query(DLQItem).filter(DLQItem.id == dlq_item_id).first()
        if not dlq_item:
            raise HTTPException(status_code=404, detail="DLQ item not found")
        db.delete(dlq_item)
        db.commit()
        return {"message": "DLQ item deleted"}
    finally:
        db.close()