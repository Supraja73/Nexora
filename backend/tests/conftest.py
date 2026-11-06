import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure database schema is created prior to test execution."""
    init_db()

@pytest.fixture
def client():
    """Provide a TestClient instance for API endpoints."""
    with TestClient(app) as test_client:
        yield test_client
