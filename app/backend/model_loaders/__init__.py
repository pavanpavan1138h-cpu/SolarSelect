"""Trusted frozen and verified registry model providers."""
import hashlib
import json
import re
from pathlib import Path
from typing import Protocol
import numpy as np
import pandas as pd
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import ModelVariant
from app.backend.contracts import HistoricalFeatures

UNITS = "kWh/kWp/day"

class ModelProvider(Protocol):
    feature_names: list[str]
    def predict(self, rows, variant: ModelVariant): ...
    def validate_features(self, rows): ...
    def get_provenance(self, variant: ModelVariant): ...
    def is_ready(self) -> bool: ...

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

class LocalFrozenModelProvider:
    def __init__(self, settings):
        self.root = settings.root
        self.metadata = json.loads((self.root / "models/phase5/final_model_metadata.json").read_text())
        manifest = json.loads((Path(__file__).parent / "frozen_manifest.json").read_text())
        # Verify audited trusted bytes BEFORE deserialization; no client-selected paths.
        for rel, expected in manifest.items():
            actual = digest(self.root / rel)
            if rel == "models/phase5/final_model_metadata.json":
                # Git may check this text file out as CRLF on Windows. Accept only
                # that newline conversion; every other metadata byte remains pinned.
                actual = hashlib.sha256((self.root / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if actual != expected:
                raise ValueError("Frozen artifact fingerprint mismatch")
        common = dict(primary_model_path=self.root / Phase5PeerCohortPredictor.DEFAULT_ET_PATH,
                      fallback_linear_path=self.root / Phase5PeerCohortPredictor.DEFAULT_EN_PATH,
                      metadata_path=self.root / Phase5PeerCohortPredictor.DEFAULT_METADATA_PATH)
        self.predictors = {v: Phase5PeerCohortPredictor(v, **common) for v in ModelVariant}
        self.feature_names = self.predictors[ModelVariant.PRIMARY_EXTRA_TREES].feature_names
        if self.feature_names != self.metadata["feature_space"]["predictive_feature_names"]:
            raise ValueError("Metadata and estimator feature ordering differ")
        if self.feature_names != list(HistoricalFeatures.model_fields):
            raise ValueError("HTTP and estimator schemas differ")

    def is_ready(self):
        return len(self.feature_names) == 29 and all(hasattr(p.primary_model, "predict") for p in self.predictors.values())

    def validate_features(self, rows):
        return self.predictors[ModelVariant.PRIMARY_EXTRA_TREES].validate_features(rows)

    def predict(self, rows, variant):
        return self.predictors[variant].predict(rows)

    def get_provenance(self, variant):
        p = self.predictors[variant].get_provenance()
        key = "primary_model" if variant == ModelVariant.PRIMARY_EXTRA_TREES else "fallback_model"
        result = {k: p[k] for k in ("model_name", "model_variant", "cohort", "evaluation_timestamp", "feature_count")}
        result.update(source="local", prediction_target="daily_specific_yield", units=UNITS,
                      feature_schema_fingerprint=p["feature_names_hash"][:16],
                      primary_artifact_fingerprint=p["primary_artifact_sha256"][:16],
                      offline_test_metrics=self.metadata["peer_cohort_models"][key]["test_metrics"],
                      evaluation_provenance=self.metadata["chronological_partitions"]["test_held_out"],
                      training_source="UNISOLAR Campus 1, Melbourne, Australia")
        if "linear_artifact_sha256" in p:
            result["linear_artifact_fingerprint"] = p["linear_artifact_sha256"][:16]
            result["blend_weights"] = p["blend_weights"]
        return result

def load_registry(settings, handoff, reference=None):
    if handoff.get("handoff_format") == "person1-sqlite-skops-v1":
        from app.backend.model_loaders.verified_registry import load_verified_registry
        return load_verified_registry(settings, handoff, reference)
    # Imports remain controlled and optional in the local serving path.
    import mlflow
    from mlflow import MlflowClient
    mlflow.set_tracking_uri(settings.tracking_uri)
    client = MlflowClient(tracking_uri=settings.tracking_uri)
    match = re.fullmatch(r"models:/([A-Za-z0-9_.-]+)@([A-Za-z0-9_.-]+)", settings.model_uri or "")
    if not match:
        raise ValueError("Expected configured models:/name@alias URI")
    name, alias = match.groups()
    version = client.get_model_version_by_alias(name, alias)
    required = {"cohort": "peer_cohort", "output_units": UNITS, "model_variant": "primary_extra_trees"}
    if any(version.tags.get(k) != v for k, v in required.items()):
        raise ValueError("Registry governance tags mismatch")
    if name != handoff["registered_name"] or alias != handoff["alias"] or str(version.version) != str(handoff["version"]):
        raise ValueError("Registry lineage mismatch")
    if version.run_id != handoff["run_id"] or version.tags.get("primary_artifact_sha256") != handoff["primary_artifact_sha256"]:
        raise ValueError("Registry artifact lineage mismatch")
    resolved = f"models:/{name}/{version.version}"
    info = mlflow.models.get_model_info(resolved)
    if info.signature is None or info.signature.inputs.input_names() != handoff["feature_names"]:
        raise ValueError("Registry signature feature ordering mismatch")
    if any(str(i.type) != "DataType.double" for i in info.signature.inputs.inputs):
        raise ValueError("Registry signature must contain numeric double inputs")
    if info.signature.outputs is None or len(info.signature.outputs.inputs) != 1:
        raise ValueError("Registry signature must declare one scalar output")
    if str(info.signature.outputs.inputs[0].type) != "DataType.double":
        raise ValueError("Registry output signature must declare double values")
    return mlflow.pyfunc.load_model(resolved), str(version.version)

class MLflowRegistryProvider:
    def __init__(self, settings):
        if not settings.registry_handoff or not settings.tracking_uri or not settings.model_uri:
            raise ValueError("BLOCKED_PENDING_PERSON1_REGISTRY_HANDOFF")
        h = json.loads(Path(settings.registry_handoff).read_text())
        self.reference = LocalFrozenModelProvider(settings)
        self.feature_names = self.reference.feature_names
        primary = self.reference.predictors[ModelVariant.PRIMARY_EXTRA_TREES]
        if h["feature_names"] != self.feature_names or h["units"] != UNITS or h["cohort"] != "peer_cohort":
            raise ValueError("Registry handoff contract mismatch")
        if h["primary_artifact_sha256"] != primary.primary_sha256:
            raise ValueError("Registry handoff artifact mismatch")
        reference_path = settings.root / "data/processed/unisolar/peer_cohort/test.csv"
        if h["reference_dataset_sha256"] != digest(reference_path):
            raise ValueError("Registry reference fixture mismatch")
        self.model, self.version = load_registry(settings, h, self.reference)
        cases = pd.read_csv(reference_path, nrows=8)[self.feature_names]
        expected = self.reference.predict(cases, ModelVariant.PRIMARY_EXTRA_TREES)
        actual = np.asarray(self.model.predict(cases), dtype=float).reshape(-1)
        if actual.shape != expected.shape or not np.all(np.isfinite(actual)) or not np.allclose(actual, expected, rtol=0, atol=1e-8):
            raise ValueError("Registry prediction parity failed")

    def is_ready(self):
        return self.model is not None

    def validate_features(self, rows):
        return self.reference.validate_features(rows)

    def predict(self, rows, variant):
        if variant != ModelVariant.PRIMARY_EXTRA_TREES:
            from app.backend.core.errors import APIError
            raise APIError(409, "MODEL_VARIANT_NOT_ENABLED", "Registry handoff supports only the primary variant.")
        return np.asarray(self.model.predict(self.validate_features(rows)), dtype=float).reshape(-1)

    def get_provenance(self, variant):
        result = self.reference.get_provenance(ModelVariant.PRIMARY_EXTRA_TREES)
        result.update(source="mlflow", registered_version=self.version, parity_checked_rows=8)
        result.update(getattr(self.model, "provenance", {}))
        return result

def create_provider(settings):
    if settings.model_source == "local":
        return LocalFrozenModelProvider(settings)
    if settings.model_source == "mlflow":
        return MLflowRegistryProvider(settings)
    raise ValueError("Unsupported MODEL_SOURCE")
