"""
Tests for app.main (FastAPI endpoints).
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint returns 200 and expected content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


# Add more endpoint tests, including error and edge cases
