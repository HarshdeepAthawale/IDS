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


def test_alerts_list_returns_200(client):
    """GET /api/alerts returns 200 and JSON with alerts list or total."""
    r = client.get("/api/alerts")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
    assert "alerts" in data
    assert isinstance(data["alerts"], list)
    assert "total" in data


def test_pcap_analyze_without_file_returns_400(client):
    """POST /api/pcap/analyze without file returns 400."""
    r = client.post("/api/pcap/analyze")
    assert r.status_code == 400
    data = r.get_json()
    assert data is not None
    assert "error" in data
    assert "file" in data["error"].lower() or "required" in data["error"].lower()


def test_pcap_stats_returns_200(client):
    """GET /api/pcap/stats returns 200 and JSON."""
    r = client.get("/api/pcap/stats")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None


def test_training_statistics_returns_200(client):
    """GET /api/training/statistics returns 200 and JSON."""
    r = client.get("/api/training/statistics")
    assert r.status_code == 200
    data = r.get_json()
    assert data is not None
