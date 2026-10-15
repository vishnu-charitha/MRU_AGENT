import os
import pytest
from fastapi.testclient import TestClient

# Explicitly set dedicated test environment variables before importing any application modules
# to guarantee complete test isolation from developer or parent shell environments.
os.environ["AUTH_TOKEN_SECRET"] = "test-secret-key-12345678901234567890"
os.environ["DATABASE_URL"] = "sqlite:///./test_students.db"

from api.main import app
from api.auth import create_access_token
from api.database import SessionLocal, StudentRegistration, init_db, engine
from datetime import datetime, timezone


@pytest.fixture(scope="session", autouse=True)
def setup_test_student():
    # Verify that the test database engine is strictly bound to test_students.db
    assert "test_students.db" in str(engine.url), f"Database engine is not bound to test_students.db: {engine.url}"
    init_db()
    db = SessionLocal()

    try:
        student = db.query(StudentRegistration).filter_by(id="test-student-session-id").first()
        if not student:
            student = StudentRegistration(
                id="test-student-session-id",
                full_name="Default Test Student",
                email="default.test@mru.edu.in",
                mobile_number="+919876543210",
                interested_course="B.Tech",
                consent_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(student)
            db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def valid_auth_token(setup_test_student):
    return create_access_token("test-student-session-id")



@pytest.fixture(scope="session")
def auth_headers(valid_auth_token):
    return {"Authorization": f"Bearer {valid_auth_token}"}


@pytest.fixture(scope="session")
def client(auth_headers):
    # TestClient that automatically includes auth headers
    c = TestClient(app)
    c.headers.update(auth_headers)
    return c


@pytest.fixture(scope="session")
def raw_client():
    # Unauthenticated TestClient
    return TestClient(app)
