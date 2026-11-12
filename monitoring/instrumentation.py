"""Wires the registry into the FastAPI app without touching model arithmetic or validation semantics."""
import math
import time
from starlette.responses import PlainTextResponse
from monitoring.metrics import REGISTRY
from monitoring.drift import FeatureWindow

def status_class(code):
    return f"{code // 100}xx"

class MonitoredProvider:
    """Transparent wrapper: delegates everything; records inference health and distributions."""
    def __init__(self, inner, registry=REGISTRY, window=None):
        self._inner, self._r = inner, registry
        self.window = window if window is not None else FeatureWindow()
        try:
            info = inner.get_provenance(next(iter(_variants())))
            registry.info["solarselect_model_info"] = {k: info.get(k, "") for k in ("model_name", "source", "model_variant", "registered_version", "primary_artifact_fingerprint", "feature_schema_fingerprint")}
        except Exception:                      # model identity is best-effort; never block serving
            registry.info["solarselect_model_info"] = {"model_name": "unknown"}
        registry.set_gauge("solarselect_model_loaded", 1.0 if inner.is_ready() else 0.0)

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def is_ready(self):
        ready = self._inner.is_ready()
        self._r.set_gauge("solarselect_model_loaded", 1.0 if ready else 0.0)
        return ready

    def validate_features(self, rows):
        frame = self._inner.validate_features(rows)
        self.window.add(frame)                 # aggregate only; rows are not retained beyond the bounded window
        return frame

    def predict(self, rows, variant):
        t0 = time.perf_counter()
        try:
            out = self._inner.predict(rows, variant)
        except Exception:
            self._r.inc("solarselect_inference_failures_total", variant=variant.value)
            raise
        self._r.observe("solarselect_inference_latency_ms", (time.perf_counter() - t0) * 1000, variant=variant.value)
        self._r.inc("solarselect_inferences_total", variant=variant.value)
        for v in out:
            if not math.isfinite(float(v)):
                self._r.inc("solarselect_nonfinite_predictions_total", variant=variant.value)
            else:
                self._r.observe("solarselect_prediction_value", float(v), buckets=(-1, 0, 1, 2, 3, 4, 5, 7.5, 10), variant=variant.value)
                if v < 0:
                    self._r.inc("solarselect_negative_predictions_total", variant=variant.value)
        return out

def _variants():
    from src.energy_economics.types import ModelVariant
    return [ModelVariant.PRIMARY_EXTRA_TREES]

def monitored_factory(factory, registry=REGISTRY):
    def build(settings):
        provider = factory(settings)
        return MonitoredProvider(provider, registry)
    return build

def install_http_monitoring(app, registry=REGISTRY):
    """Adds request metrics middleware and a hidden /metrics endpoint (excluded from OpenAPI)."""
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        ms = (time.perf_counter() - start) * 1000
        registry.inc("solarselect_http_requests_total", route=route, method=request.method, status=status_class(response.status_code))
        registry.observe("solarselect_http_request_duration_ms", ms, route=route)
        code = getattr(request.state, "error_code", None)
        if code:
            registry.inc("solarselect_api_errors_total", code=code)
            if code in ("PREDICTION_PENDING_LAG_POLICY", "MODEL_VARIANT_NOT_ENABLED"):
                registry.inc("solarselect_governance_rejections_total", code=code)
            if code in ("VALIDATION_ERROR", "INVALID_MODEL_INPUT"):
                registry.inc("solarselect_input_rejections_total", code=code)
        return response

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return PlainTextResponse(registry.render_prometheus(), media_type="text/plain; version=0.0.4")
