"""SolarSelect local FastAPI inference server. Launch: python -m uvicorn app.backend.main:app."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from app.backend.core.config import Settings
from app.backend.core.errors import APIError
from app.backend.model_loaders import create_provider
from app.backend.roof_service import RoofService
from app.backend.routes import router
from src.energy_economics.exceptions import FeatureValidationError, Phase5InferenceError, PanelNotFoundError, Phase8Error
from src.roof_fit.exceptions import (InvalidRoofSpecificationError, PanelNotFoundError as RoofPanelNotFound,
                                     QuantizationError, RoofFitError)

logger = logging.getLogger("solarselect.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

def create_app(settings=None, provider_factory=None, roof_factory=None):
    settings = settings or Settings()
    provider_factory = provider_factory or create_provider
    roof_factory = roof_factory or RoofService

    @asynccontextmanager
    async def lifespan(app):
        app.state.provider = None
        app.state.roof_service = None
        app.state.startup_status = {}
        for name, factory in (("model", lambda: provider_factory(settings)),
                              ("geometry", lambda: roof_factory(settings.root))):
            try:
                value = factory()
                if name == "model" and not value.is_ready():
                    raise ValueError("Provider did not become ready")
                setattr(app.state, "provider" if name == "model" else "roof_service", value)
                app.state.startup_status[name] = "READY"
            except Exception as exc:
                # Log type and safe code only: exception text may contain absolute paths/credentials.
                code = "BLOCKED_PENDING_PERSON1_REGISTRY_HANDOFF" if name == "model" and settings.model_source == "mlflow" else "INITIALIZATION_FAILED"
                app.state.startup_status[name] = code
                logger.error(json.dumps({"event": "startup_failed", "service": name,
                                         "code": code, "exception_type": type(exc).__name__}))
        yield
        app.state.provider = None
        app.state.roof_service = None

    app = FastAPI(title="SolarSelect Frozen Model API", version="1.0.0",
                  description="Historical UNISOLAR site-day inference and geometric proposals. Prospective rooftop forecasting remains pending lag policy.",
                  lifespan=lifespan)
    app.state.settings = settings
    app.state.limitations = RoofService.limitations()

    def error_response(request, status, code, message, details=None):
        request.state.error_code = code
        rid = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(status_code=status, content={
            "error": {"code": code, "message": message, "details": details},
            "request_id": rid}, headers={"X-Request-ID": rid})

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        # Generate our own bounded request identifier rather than trusting/logging arbitrary headers.
        request.state.request_id = str(uuid.uuid4())
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(json.dumps({"event": "request_failed", "exception_type": type(exc).__name__,
                                     "request_id": request.state.request_id}))
            response = error_response(request, 500, "INTERNAL_ERROR", "Unexpected internal error.")
        response.headers["X-Request-ID"] = request.state.request_id
        route = request.scope.get("route")
        logger.info(json.dumps({"event": "http_request", "request_id": request.state.request_id,
                                "route": getattr(route, "path", "unmatched"),
                                "status": response.status_code,
                                "duration_ms": round((time.perf_counter()-start)*1000, 3),
                                "model_variant": getattr(request.state, "model_variant", None),
                                "error_code": getattr(request.state, "error_code", None)}))
        return response

    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return error_response(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never echo full payloads, nonfinite numbers, or Pydantic exception context.
        details = [{"location": list(e["loc"]), "type": e["type"], "message": e["msg"]} for e in exc.errors()]
        return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed.", details)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(request, exc.status_code, "HTTP_ERROR", "Route or method unavailable.")

    async def feature_error(request, exc):
        return error_response(request, 422, "INVALID_MODEL_INPUT", "Historical feature validation failed.")
    app.add_exception_handler(FeatureValidationError, feature_error)

    async def model_error(request, exc):
        return error_response(request, 503, "MODEL_UNAVAILABLE", "Selected model could not complete inference.")
    app.add_exception_handler(Phase5InferenceError, model_error)

    async def panel_error(request, exc):
        return error_response(request, 404, "PANEL_NOT_FOUND", "Panel identifier is absent from the catalogue.")
    app.add_exception_handler(PanelNotFoundError, panel_error)
    app.add_exception_handler(RoofPanelNotFound, panel_error)

    async def roof_error(request, exc):
        return error_response(request, 422, "INVALID_ROOF_INPUT", "Roof geometry, setback or obstacle constraints failed validation.")
    app.add_exception_handler(InvalidRoofSpecificationError, roof_error)
    app.add_exception_handler(QuantizationError, roof_error)

    async def service_error(request, exc):
        return error_response(request, 503, "ENGINE_UNAVAILABLE", "Required engineering service could not complete the operation.")
    app.add_exception_handler(RoofFitError, service_error)
    app.add_exception_handler(Phase8Error, service_error)
    app.include_router(router)
    return app

app = create_app()
