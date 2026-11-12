import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from src.roof_fit.engine import RoofFitEngine

def test_catalogue(api_client):
    result = api_client.get("/api/v1/panels").json()
    assert result["count"] == 12
    assert len(result["panels"]) == 12
    for p in result["panels"]:
        assert p["price_per_module"] is None
        assert p["price_per_wp"] is None
    assert api_client.get("/api/v1/panels/INVALID").status_code == 404
    assert api_client.get("/api/v1/panels/PNL-TRINA-330W").json()["panel_id"] == "PNL-TRINA-330W"

@pytest.mark.parametrize("orientation", [None, "portrait", "landscape", "both"])
def test_roof_direct_parity(api_client, roof_body, orientation, monkeypatch):
    # Freeze engine audit time for exact whole-contract comparison, including metadata.
    import src.roof_fit.placement_engine as placement
    fixed = datetime(2026, 11, 11, tzinfo=timezone.utc)
    monkeypatch.setattr(placement, "datetime", SimpleNamespace(now=lambda _: fixed))
    roof_body["orientation_override"] = orientation
    response = api_client.post("/api/v1/roof-fit", json=roof_body)
    assert response.status_code == 200, response.text
    spec = {k: v for k, v in roof_body.items() if k not in ("panel_id", "orientation_override", "inter_panel_clearance", "inter_row_clearance")}
    spec.update(clamping_gap=0.02, walkway_gap=0.5, allowed_orientations=orientation or "both", azimuth_deg=180, tilt_deg=0)
    direct = RoofFitEngine().run_dict(spec, panel_id=roof_body["panel_id"], allowed_orientations=orientation)
    assert response.json()["layout"] == direct
    assert response.json()["recommendation_status"] == "RECOMMENDATION_NOT_EVALUATED"

@pytest.mark.parametrize("field,value,status", [
    ("perimeter_setback", 10, 422), ("perimeter_setback", -1, 422),
    ("orientation_override", "diagonal", 422), ("panel_id", "UNKNOWN", 404),
    ("length", 0.00001, 422), ("length", 201, 422), ("inter_row_clearance", -1, 422)])
def test_bad_roof(api_client, roof_body, field, value, status):
    roof_body[field] = value
    assert api_client.post("/api/v1/roof-fit", json=roof_body).status_code == status

def test_obstacle_bounds_and_duplicate(api_client, roof_body):
    roof_body["obstacles"][0]["x"] = 21
    assert api_client.post("/api/v1/roof-fit", json=roof_body).status_code == 422
    roof_body["obstacles"][0]["x"] = 4
    roof_body["obstacles"] *= 2
    assert api_client.post("/api/v1/roof-fit", json=roof_body).status_code == 422

def test_quantized_setback_not_relaxed(api_client, roof_body):
    roof_body.update(length=1.00009, width=2.0, perimeter_setback=0.50001)
    assert api_client.post("/api/v1/roof-fit", json=roof_body).status_code == 422
