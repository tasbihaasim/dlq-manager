from app.main import app
from fastapi.testclient import TestClient   
from app.model import WebhookEvent, DLQItem
from unittest.mock import MagicMock, patch

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_dashboard():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_websocket():
    with client.websocket_connect("/ws") as websocket:
        # we can't really test the real-time aspect here, but we can at least check that the connection is established
        assert websocket is not None

def test_get_dlq_items():
    mock_db = MagicMock()
    mock_dlq_item = DLQItem(id=1, status="failed", error_message="Test error", retry_count=0)
    mock_db.query.return_value.all.return_value = [mock_dlq_item]
    with patch("app.main.SessionLocal", return_value=mock_db):
        response = client.get("/dlq_items")
        assert response.status_code == 200
        assert response.json() == [{"id": 1, "status": "failed", "error_message": "Test error", "retry_count": 0}]

def test_retry_dlq_item():
    mock_db = MagicMock()
    mock_dlq_item = DLQItem(id=1, status="failed", error_message="Test error", retry_count=0)
    mock_webhook_event = WebhookEvent(id=1, source="test_source", payload={"key": "value"})
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_dlq_item, mock_webhook_event]
    with patch("app.main.SessionLocal", return_value=mock_db):
        response = client.post("/dlq/1/retry")
        assert response.status_code == 200
        assert response.json() == {"message": "Retry initiated"}
        assert mock_dlq_item.retry_count == 1
        assert mock_dlq_item.status == "retried"
        mock_db.commit.assert_called_once()

def test_delete_dlq_item():
    mock_db = MagicMock()
    mock_dlq_item = DLQItem(id=1, status="failed", error_message="Test error", retry_count=0)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_dlq_item
    with patch("app.main.SessionLocal", return_value=mock_db):
        response = client.delete("/dlq/1")
        assert response.status_code == 200
        assert response.json() == {"message": "DLQ item deleted"}
        mock_db.delete.assert_called_once_with(mock_dlq_item)
        mock_db.commit.assert_called_once()
