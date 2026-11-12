"""Versioned, read-only HTTP routes."""
import csv
from fastapi import APIRouter, Depends, Request
from app.backend.contracts import (PredictionRequest, HistoricalRequest, ProspectiveRequest,
                                   BatchRequest, PredictionResult, BatchResult, RoofRequest, RoofResult,
                                   HistoricalFeatures)
from app.backend.core.errors import APIError, ErrorEnvelope
from app.backend.prediction_service import PredictionService
from src.energy_economics.types import ModelVariant

router = APIRouter(prefix="/api/v1", responses={
    code: {"model": ErrorEnvelope} for code in (404, 409, 422, 500, 503)
})

def optional_provider(request: Request):
    return request.app.state.provider

def require_provider(provider):
    if provider is None or not provider.is_ready():
        raise APIError(503, "MODEL_UNAVAILABLE", "Selected model is unavailable; inspect readiness and operator startup logs.")
    return provider

def get_provider(request: Request):
    return require_provider(request.app.state.provider)

def get_roof_service(request: Request):
    service = request.app.state.roof_service
    if service is None:
        raise APIError(503, "GEOMETRY_UNAVAILABLE", "Catalogue or roof service is unavailable.")
    return service

@router.get("/health/live", tags=["health"])
def live():
    return {"status": "LIVE", "version": "1.0.0"}

@router.get("/health/ready", tags=["health"])
def ready(request: Request):
    s = request.app.state
    if s.provider is None or not s.provider.is_ready() or s.roof_service is None:
        raise APIError(503, "NOT_READY", "Required services are not initialized.", s.startup_status)
    return {"status": "READY", "model_source": s.settings.model_source,
            "services": {"model": "READY", "catalogue": "READY", "roof_fit": "READY"}}

@router.get("/model/info", tags=["model"])
def model_info(provider=Depends(get_provider)):
    return provider.get_provenance(ModelVariant.PRIMARY_EXTRA_TREES)

@router.get("/model/schema", tags=["model"])
def model_schema(request: Request, provider=Depends(get_provider)):
    with (request.app.state.settings.root / "data/processed/unisolar/feature_dictionary.csv").open(encoding="utf-8-sig", newline="") as f:
        dictionary = {r["Feature"]: r for r in csv.DictReader(f)}
    schema = HistoricalFeatures.model_json_schema()
    return {"ordered_feature_names": provider.feature_names, "feature_count": len(provider.feature_names),
            "fields": [{"name": name, "units": dictionary[name]["Unit"],
                        "description": dictionary[name]["Definition"],
                        "constraints": schema["properties"][name]} for name in provider.feature_names],
            "ordering_authority": "Frozen estimator feature_names_in_, cross-checked against final metadata",
            "additional_properties": False}

@router.get("/limitations", tags=["governance"])
def limitations(request: Request):
    return {"limitations": request.app.state.limitations,
            "prediction_energy_basis": "UNVERIFIED_ASSUMED_AC",
            "prospective_status": "PREDICTION_PENDING_LAG_POLICY",
            "recommendation_status": "RECOMMENDATION_NOT_EVALUATED",
            "electrical_status": "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS"}

@router.post("/predict", response_model=PredictionResult, tags=["prediction"])
def predict(body: PredictionRequest, request: Request, provider=Depends(optional_provider)):
    if isinstance(body, ProspectiveRequest):
        raise APIError(409, "PREDICTION_PENDING_LAG_POLICY",
                       "Prospective roofs lack authentic yield history. Supply an approved historical site-day row; a future authorized lag-free model or lag policy is required for new roofs.",
                       {"prediction_status": "PREDICTION_PENDING_LAG_POLICY",
                        "predicted_specific_yield_kwh_per_kwp_day": None})
    provider = require_provider(provider)
    request.state.model_variant = body.model_variant.value
    return PredictionService(provider, request.app.state.limitations).predict([body], request.state.request_id)[0]

@router.post("/predict/batch", response_model=BatchResult, tags=["prediction"])
def predict_batch(body: BatchRequest, request: Request, provider=Depends(get_provider)):
    request.state.model_variant = ",".join(sorted({r.model_variant.value for r in body.rows}))
    return {"results": PredictionService(provider, request.app.state.limitations).predict(body.rows, request.state.request_id),
            "request_id": request.state.request_id}

@router.get("/panels", tags=["catalogue"])
def panels(service=Depends(get_roof_service)):
    return {"panels": [service.catalogue.get_panel(p).to_dict() for p in service.catalogue.list_panel_ids()],
            "count": len(service.catalogue.list_panel_ids()),
            "provenance_qualification": service.catalogue.PROVENANCE_QUALIFICATION}

@router.get("/panels/{panel_id}", tags=["catalogue"])
def panel(panel_id: str, service=Depends(get_roof_service)):
    return service.catalogue.get_panel(panel_id).to_dict()

@router.post("/roof-fit", response_model=RoofResult, tags=["geometry"])
def roof_fit(body: RoofRequest, request: Request, service=Depends(get_roof_service)):
    return {"layout": service.roof_fit(body), "request_id": request.state.request_id}
