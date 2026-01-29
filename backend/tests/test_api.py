"""
Minimal API tests for IDS backend.
Run from backend dir: python -m pytest tests/ -v
Requires: pip install pytest
"""
import os
import sys

import pytest

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use testing config so sniffer does not start
os.environ.setdefault("FLASK_ENV", "testing")


@pytest.fixture
def app():
    """Create app with testing config."""
    from app import create_app
    return create_app("testing")


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


def test_health_returns_200_and_status(client):
    """GET /api/health returns 200 and JSON with 'status'."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "training")


def test_model_info_returns_200(client):
    """GET /api/training/model-info returns 200 and JSON."""
    r = client.get("/api/training/model-info")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
