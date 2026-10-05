import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_chat_unicode_history_btech_eee():
    payload = {
        "question": "for btech eee",
        "history": [
            {
                "role": "user",
                "content": "fee structure"
            },
            {
                "role": "assistant",
                "content": "The fee structure is \u20b91,50,000 per year."
            }
        ]
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

def test_chat_unicode_history_btech_cse():
    payload = {
        "question": "for btech computer science and engineering",
        "history": [
            {
                "role": "user",
                "content": "fee structure"
            },
            {
                "role": "assistant",
                "content": "The fee structure is \u20b91,50,000 per year."
            }
        ]
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
