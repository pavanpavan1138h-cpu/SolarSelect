from fastapi.testclient import TestClient
from app.backend.main import create_app
from app.backend.core.config import Settings

def test_live_without_model(api_settings):
    def fail(_):
        raise RuntimeError("private path must never be returned")
    with TestClient(create_app(api_settings, provider_factory=fail)) as c:
        assert c.get("/api/v1/health/live").status_code == 200
        response = c.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json()["error"]["details"]["model"] == "INITIALIZATION_FAILED"
        assert "private path" not in response.text

def test_real_ready(real_client):
    assert real_client.get("/api/v1/health/ready").status_code == 200

def test_docs(api_client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert api_client.get(path).status_code == 200
    spec = api_client.get("/openapi.json").json()
    required = ["health/live", "health/ready", "model/info", "model/schema", "limitations",
                "predict", "predict/batch", "panels", "panels/{panel_id}", "roof-fit"]
    assert all("/api/v1/" + p in spec["paths"] for p in required)
    assert len(spec["components"]["schemas"]["HistoricalFeatures"]["required"]) == 29

def test_geometry_startup_failure(api_settings, real_provider):
    def fail(_):
        raise RuntimeError("bad catalogue")
    with TestClient(create_app(api_settings, provider_factory=lambda _: real_provider, roof_factory=fail)) as c:
        assert c.get("/api/v1/health/ready").status_code == 503
        assert c.get("/api/v1/panels").status_code == 503

def test_actual_missing_artifacts_fail_ready(tmp_path):
    # A separate nonexistent configured root; never rename or edit trusted artifacts.
    with TestClient(create_app(Settings(root=tmp_path, model_source="local"))) as c:
        assert c.get("/api/v1/health/live").status_code == 200
        assert c.get("/api/v1/health/ready").status_code == 503
        assert c.get("/api/v1/model/info").status_code == 503
        assert str(tmp_path) not in c.get("/api/v1/health/ready").text
