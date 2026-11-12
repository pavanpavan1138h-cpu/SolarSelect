"""Rule evaluation against the live registry. Rules/thresholds live in monitoring/configs/alert_rules.json."""
import json
from pathlib import Path
from monitoring.metrics import REGISTRY

RULES_PATH = Path(__file__).parent / "configs" / "alert_rules.json"

def load_rules(path=RULES_PATH):
    return json.loads(Path(path).read_text())["rules"]

def _ratio(num, den):
    return None if den <= 0 else num / den

def signals(registry=REGISTRY, drift=None, performance=None):
    total = registry.counter_sum("solarselect_http_requests_total")
    infer = registry.counter_sum("solarselect_inferences_total")
    fails = registry.counter_sum("solarselect_inference_failures_total")
    return {
        "model_loaded": registry.gauges.get(("solarselect_model_loaded", ()), None),
        "http_requests": total,
        "http_5xx_rate": _ratio(registry.counter_sum("solarselect_http_requests_total", status="5xx"), total),
        "http_p95_latency_ms": registry.percentile("solarselect_http_request_duration_ms", 0.95, route="/api/v1/predict"),
        "inference_failure_rate": _ratio(fails, infer + fails),
        "nonfinite_predictions": registry.counter_sum("solarselect_nonfinite_predictions_total"),
        "input_rejection_rate": _ratio(registry.counter_sum("solarselect_input_rejections_total"), total),
        "governance_rejections": registry.counter_sum("solarselect_governance_rejections_total"),
        "feature_drift_max_psi": (drift or {}).get("max_psi"),
        "feature_drift_status": (drift or {}).get("status"),
        "mae_ratio_to_reference": (performance or {}).get("mae_ratio_to_reference"),
    }

OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "==": lambda a, b: a == b}

def evaluate(registry=REGISTRY, drift=None, performance=None, rules=None):
    """Returns the list of firing alerts. A signal that is None (no data) never fires - it is not evidence of health or failure."""
    sig, firing = signals(registry, drift, performance), []
    for rule in rules or load_rules():
        value = sig.get(rule["signal"])
        if value is None:
            continue
        if "min_requests" in rule and sig["http_requests"] < rule["min_requests"]:
            continue
        if OPS[rule["op"]](value, rule["threshold"]):
            firing.append({"name": rule["name"], "severity": rule["severity"], "value": value,
                           "threshold": rule["threshold"], "runbook": rule["runbook"]})
    return firing
