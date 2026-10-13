import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.database import SessionLocal, StudentRegistration
from api.auth import create_access_token
from datetime import timedelta


def test_unauthenticated_chat_access_blocked(raw_client):
    """Direct chat request without Authorization header must return 401."""
    response = raw_client.post("/api/chat", json={"question": "What is B.Tech?"})
    assert response.status_code == 401
    assert "Authorization header is required" in response.json()["detail"]


def test_invalid_token_chat_access_blocked(raw_client):
    """Direct chat request with an invalid/malformed token must return 401."""
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = raw_client.post("/api/chat", json={"question": "What is B.Tech?"}, headers=headers)
    assert response.status_code == 401
    assert "Invalid session token" in response.json()["detail"]


def test_expired_token_chat_access_blocked(raw_client):
    """Direct chat request with an expired token must return 401."""
    expired_token = create_access_token("test-student-id", expires_delta=timedelta(seconds=-10))
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = raw_client.post("/api/chat", json={"question": "What is B.Tech?"}, headers=headers)
    assert response.status_code == 401
    assert "Session has expired" in response.json()["detail"]


def test_valid_registration_creates_persisted_record(raw_client):
    """Registering a student persists record in database and returns valid token."""
    payload = {
        "full_name": "Test Student",
        "email": "test.student@example.edu",
        "mobile_number": "9876543210",
        "interested_course": "B.Tech",
        "consent": True,
    }
    response = raw_client.post("/api/students/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "student_id" in data
    assert "token" in data

    # Verify directly in the database
    db = SessionLocal()
    try:
        record = db.query(StudentRegistration).filter_by(id=data["student_id"]).first()
        assert record is not None
        assert record.full_name == "Test Student"
        assert record.email == "test.student@example.edu"
        assert record.mobile_number == "+919876543210"
        assert record.interested_course == "B.Tech"
        assert record.consent_at is not None
        assert record.created_at is not None
    finally:
        db.close()

    # Validate session endpoint with the returned token
    session_response = raw_client.get(
        "/api/students/session",
        headers={"Authorization": f"Bearer {data['token']}"}
    )
    assert session_response.status_code == 200
    assert session_response.json()["valid"] is True
    assert session_response.json()["student_id"] == data["student_id"]


def test_registration_missing_required_fields(raw_client):
    """Missing fields must return 422 Unprocessable Entity."""
    # Missing email
    response = raw_client.post("/api/students/register", json={
        "full_name": "Test Student",
        "mobile_number": "+919876543210",
        "interested_course": "B.Tech",
        "consent": True,
    })
    assert response.status_code == 422


def test_registration_invalid_email(raw_client):
    """Invalid email format must return 422."""
    response = raw_client.post("/api/students/register", json={
        "full_name": "Test Student",
        "email": "invalid-email-address",
        "mobile_number": "+919876543210",
        "interested_course": "B.Tech",
        "consent": True,
    })
    assert response.status_code == 422
    assert "valid email" in response.json()["detail"].lower()


def test_registration_invalid_mobile(raw_client):
    """Invalid mobile number must return 422."""
    response = raw_client.post("/api/students/register", json={
        "full_name": "Test Student",
        "email": "student@example.com",
        "mobile_number": "12345",  # Too short / invalid Indian prefix
        "interested_course": "B.Tech",
        "consent": True,
    })
    assert response.status_code == 422
    assert "valid 10-digit indian mobile number" in response.json()["detail"].lower()


def test_registration_missing_consent(raw_client):
    """Registration without explicit consent must return 422."""
    response = raw_client.post("/api/students/register", json={
        "full_name": "Test Student",
        "email": "student@example.com",
        "mobile_number": "+919876543210",
        "interested_course": "B.Tech",
        "consent": False,
    })
    assert response.status_code == 422
    assert "consent is mandatory" in response.json()["detail"].lower()


def test_database_write_failure_does_not_unlock_chat(raw_client):
    """If DB write fails, registration must fail with 500 and not issue a valid token."""
    with patch("api.routes.students.Session.commit", side_effect=Exception("Database lock/write failure")):
        response = raw_client.post("/api/students/register", json={
            "full_name": "Test Student",
            "email": "student@example.com",
            "mobile_number": "+919876543210",
            "interested_course": "B.Tech",
            "consent": True,
        })
        assert response.status_code == 500
        assert "could not save registration" in response.json()["detail"].lower()
