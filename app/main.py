import redis
import json
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi import Request, Response
from app.database import SessionLocal
from app.model import WebhookEvent, DLQItem
import hmac, hashlib, os
from app.tasks import process_webhook_event
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware



r = redis.from_url(os.getenv("REDIS_URL"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/dashboard")
async def dashboard():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # opens the persistent connection with Angular
    pubsub = r.pubsub()
    pubsub.subscribe("webhook_events")  # subscribe to Redis channels for new webhook events and DLQ items
    
    while True:
        message = pubsub.get_message()  # check if Redis published anything
        if message and message["type"] == "message": # if there is a new message, forward it to Angular # checking the type because we only forward actual messages, not subscription confirmations
            data = json.loads(message["data"])
            await websocket.send_json(data)  # forward to Angular
        await asyncio.sleep(0.01)  # small sleep to prevent this loop from consuming too much CPU when idle


@app.get("/dlq_items")
async def get_dlq_items():
    db = SessionLocal()
    try:
        items = db.query(DLQItem).all()
        return [{"id": i.id, "status": i.status, "error_message": i.error_message, "retry_count": i.retry_count} for i in items]
    finally:
        db.close()

@app.post("/dlq/{dlq_item_id}/retry")
async def retry_dlq_item(dlq_item_id: int):
    db = SessionLocal()
    try:
        dlq_item = db.query(DLQItem).filter(DLQItem.id == dlq_item_id).first()
        if not dlq_item:
            raise HTTPException(status_code=404, detail="DLQ item not found")
        dlq_item.retry_count += 1
        webhook_event = db.query(WebhookEvent).filter(WebhookEvent.id == dlq_item.webhook_event_id).first()
        if not webhook_event:
            raise HTTPException(status_code=404, detail="Webhook event not found")
        process_webhook_event.delay(webhook_event.source, webhook_event.payload)
        dlq_item.status = "retried"
        db.commit()
        return {"message": "Retry initiated"}
    finally:
        db.close()

@app.delete("/dlq/{dlq_item_id}")
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

@app.post("/ingest/{source}")
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