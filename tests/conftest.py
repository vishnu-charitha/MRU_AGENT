import os
import pytest
from fastapi.testclient import TestClient

# Ensure test secrets are set before importing api
os.environ.setdefault("AUTH_TOKEN_SECRET", "test-secret-key-12345678901234567890")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_students.db")

from api.main import app
from api.auth import create_access_token


@pytest.fixture(scope="session")
def valid_auth_token():
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
