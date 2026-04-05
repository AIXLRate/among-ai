import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["models"] >= 6

    def test_health_includes_synthesis_model(self):
        r = client.get("/health")
        data = r.json()
        assert "synthesis_model" in data
        assert isinstance(data["synthesis_model"], str)


class TestModelsEndpoint:
    def test_models_returns_list(self):
        r = client.get("/models")
        assert r.status_code == 200
        models = r.json()
        assert isinstance(models, list)
        assert len(models) >= 6

    def test_models_have_required_fields(self):
        r = client.get("/models")
        models = r.json()
        for model in models:
            assert "id" in model
            assert "name" in model
            assert "role" in model
            assert "color" in model
            assert "dark" in model
            assert "glow" in model

    def test_no_duplicate_model_ids_with_same_name(self):
        r = client.get("/models")
        models = r.json()
        names = [m["name"] for m in models]
        assert len(names) == len(set(names)), "Duplicate model names found"


class TestFrontendServing:
    def test_root_serves_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
