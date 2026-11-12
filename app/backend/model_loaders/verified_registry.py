"""Verified local MLflow snapshot adapter. No registry writes or path rewrites.

The approved alias is resolved from the supplied SQLite snapshot in read-only
mode. Its original macOS storage URI is mapped to a hash-verified local package.
Only reviewed sklearn/skops types are allowed before MLflow deserialization.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

from src.energy_economics.exceptions import FeatureValidationError

NAME = "SolarSelect-Yield-PeerCohort"
ALIAS = "champion"
INTEGER_FEATURES = {"day_of_year", "month", "day_of_week", "is_weekend", "has_valid_lag1"}
TRUSTED_TYPES = {"sklearn.tree._tree.Tree"}
PACKAGE_FILES = {
    "MLmodel", "model.skops", "requirements.txt", "conda.yaml",
    "python_env.yaml", "input_example.json", "serving_input_example.json",
}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def local_path(root, relative):
    """Operator configuration must resolve inside this repository."""
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Registry handoff requires a repository-relative path")
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Registry path escapes repository root")
    return resolved


def verify_registry_record(settings, handoff):
    """Read actual registered identity/lineage, never initialize an MLflow store."""
    from sqlalchemy.engine import make_url

    if handoff["registered_name"] != NAME or handoff["alias"] != ALIAS or str(handoff["version"]) != "1":
        raise ValueError("Only the approved Peer Cohort champion version is supported")
    if settings.model_uri != f"models:/{NAME}@{ALIAS}":
        raise ValueError("Configured registry URI does not match approved champion")
    database = local_path(settings.root, handoff["database_relative_path"])
    url = make_url(settings.tracking_uri)
    if url.drivername != "sqlite" or url.query or not url.database or Path(url.database).resolve() != database:
        raise ValueError("Tracking URI does not identify the verified local database")
    if sha256(database) != handoff["database_sha256"]:
        raise ValueError("Registry database fingerprint mismatch")

    conn = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT v.* FROM model_versions v JOIN registered_model_aliases a "
            "ON a.name=v.name AND a.version=v.version WHERE a.name=? AND a.alias=?",
            (NAME, ALIAS),
        ).fetchone()
        if row is None or str(row["version"]) != str(handoff["version"]) or row["status"] != "READY":
            raise ValueError("Approved registry alias is absent or not READY")
        version = dict(row)
        if version["run_id"] != handoff["run_id"] or version["source"] != handoff["registry_source"]:
            raise ValueError("Registry version/run/source lineage mismatch")
        if version["storage_location"] != handoff["original_storage_location"]:
            raise ValueError("Original registry storage URI mismatch")
        logged = conn.execute("SELECT * FROM logged_models WHERE model_id=?", (handoff["model_id"],)).fetchone()
        if logged is None or logged["source_run_id"] != version["run_id"] or logged["status"] != 2:
            raise ValueError("Logged model lineage/status mismatch")
        if logged["artifact_location"] != version["storage_location"]:
            raise ValueError("Logged model and version storage locations disagree")
        run = conn.execute("SELECT status FROM runs WHERE run_uuid=?", (version["run_id"],)).fetchone()
        if run is None or run["status"] != "FINISHED":
            raise ValueError("Registered source run is not FINISHED")
        tags = dict(conn.execute("SELECT key,value FROM tags WHERE run_uuid=?", (version["run_id"],)).fetchall())
        params = dict(conn.execute("SELECT key,value FROM params WHERE run_uuid=?", (version["run_id"],)).fetchall())
        model = conn.execute("SELECT description FROM registered_models WHERE name=?", (NAME,)).fetchone()
        version_tags = dict(conn.execute(
            "SELECT key,value FROM model_version_tags WHERE name=? AND version=?", (NAME, version["version"])
        ).fetchall())
    finally:
        conn.close()

    required_tags = {
        "cohort": "peer", "role": "primary_candidate", "phase": "Phase 5",
        "source": "historical_evaluation", "evaluation_split": "test",
        "acceptance_verdict": "ACCEPTED", "feature_count": "29",
        "dvc_model_path": "models/phase5/final/peer_cohort/final_extra_trees.joblib",
        "dvc_pointer_file": "models/phase5/final/peer_cohort/final_extra_trees.joblib.dvc",
        "dvc_model_md5": handoff["primary_artifact_md5"],
    }
    if any(tags.get(k) != v for k, v in required_tags.items()):
        raise ValueError("Registered source-run governance or DVC lineage mismatch")
    if params.get("model_name") != "Tuned ExtraTreesRegressor" or params.get("target") != "daily_specific_yield_kwh_per_kwp":
        raise ValueError("Registered algorithm/target provenance mismatch")
    if model is None or "kWh/kWp/day" not in (model["description"] or "") or handoff["units"] != "kWh/kWp/day":
        raise ValueError("Registered model description does not substantiate expected units")
    # Missing version tags are not invented. Actual run evidence is checked above;
    # any conflicting version-level evidence must still fail closed.
    allowed = {"cohort": {"peer", "peer_cohort"}, "output_units": {"kWh/kWp/day"},
               "model_variant": {"primary_extra_trees"},
               "primary_artifact_sha256": {handoff["primary_artifact_sha256"]}}
    for key, choices in allowed.items():
        if key in version_tags and version_tags[key] not in choices:
            raise ValueError("Conflicting model-version provenance tag")
    return version, tags, params, version_tags


def verify_package(settings, handoff, reference):
    """Validate all bytes, descriptor and trust policy BEFORE model loading."""
    import yaml

    package = local_path(settings.root, handoff["artifact_relative_path"])
    hashes = handoff["package_sha256"]
    if set(hashes) != PACKAGE_FILES:
        raise ValueError("Registered package inventory is incomplete or unexpected")
    for name, expected in hashes.items():
        path = (package / name).resolve()
        if path.parent != package or sha256(path) != expected:
            raise ValueError("Registered package fingerprint mismatch")
    descriptor = yaml.safe_load((package / "MLmodel").read_text(encoding="utf-8"))
    if descriptor["model_id"] != handoff["model_id"] or descriptor["run_id"] != handoff["run_id"]:
        raise ValueError("MLmodel identity does not match registry")
    if descriptor["artifact_path"] != handoff["original_storage_location"]:
        raise ValueError("MLmodel original artifact location mismatch")
    if set(descriptor["flavors"]) != {"python_function", "sklearn"}:
        raise ValueError("Unapproved MLflow flavor")
    pyfunc = descriptor["flavors"]["python_function"]
    sklearn = descriptor["flavors"]["sklearn"]
    if pyfunc.get("loader_module") != "mlflow.sklearn" or pyfunc.get("model_path") != "model.skops" or pyfunc.get("predict_fn") != "predict" or pyfunc.get("code"):
        raise ValueError("Unapproved pyfunc loader, code or prediction function")
    if sklearn.get("serialization_format") != "skops" or sklearn.get("pickled_model") != "model.skops" or sklearn.get("code"):
        raise ValueError("Only the verified code-free skops package is permitted")
    if set(sklearn.get("skops_trusted_types") or []) != TRUSTED_TYPES or set(handoff["trusted_types"]) != TRUSTED_TYPES:
        raise ValueError("Unapproved skops trusted-type declaration")
    for library, expected in {"mlflow": "3.18.0", "scikit-learn": "1.7.2", "skops": "0.16.0"}.items():
        if importlib.metadata.version(library) != expected:
            raise ValueError(f"Registered package requires reviewed {library} version {expected}")
    if sklearn.get("sklearn_version") != "1.7.2" or descriptor.get("mlflow_version") != "3.18.0":
        raise ValueError("Serialized model library version mismatch")

    signature = {"inputs": json.loads(descriptor["signature"]["inputs"]),
                 "outputs": json.loads(descriptor["signature"]["outputs"])}
    if signature != handoff["signature"]:
        raise ValueError("MLmodel and reviewed handoff signatures differ")
    inputs = signature["inputs"]
    if [v["name"] for v in inputs] != reference.feature_names or len(inputs) != 29:
        raise ValueError("Registered feature names/order differ from frozen reference")
    if any(v.get("required") is not True or v["type"] != ("long" if v["name"] in INTEGER_FEATURES else "double") for v in inputs):
        raise ValueError("Unapproved registered feature types or optional fields")
    if signature["outputs"] != [{"type": "double", "name": "target_daily_yield", "required": True}]:
        raise ValueError("Registered output schema mismatch")
    primary = reference.predictors[next(v for v in reference.predictors if v.value == "primary_extra_trees")]
    if hashlib.md5(primary.primary_path.read_bytes()).hexdigest() != handoff["primary_artifact_md5"]:
        raise ValueError("Frozen reference does not match DVC run lineage")
    pointer = yaml.safe_load((settings.root / "models/phase5/final/peer_cohort/final_extra_trees.joblib.dvc").read_text())
    if pointer["outs"][0]["md5"] != handoff["primary_artifact_md5"]:
        raise ValueError("DVC pointer does not match registered source run")
    import skops.io
    observed = set(skops.io.get_untrusted_types(file=package / "model.skops"))
    if observed != TRUSTED_TYPES:
        raise ValueError("Unexpected serialized types; model was not loaded")
    return package, signature, primary.primary_model


class VerifiedRegistryModel:
    def __init__(self, model, reference, signature, provenance):
        self.model, self.reference = model, reference
        self.signature, self.provenance = signature, provenance

    def prepare_features(self, rows):
        frame = self.reference.validate_features(rows)
        for field in self.signature["inputs"]:
            name = field["name"]
            if field["type"] == "long":
                values = frame[name].to_numpy()
                bounds = np.iinfo(np.int64)
                if not np.all(values % 1 == 0) or np.any(values < bounds.min) or np.any(values >= 2**63):
                    raise FeatureValidationError(f"Registered integer feature '{name}' requires exact integral values")
                frame[name] = frame[name].astype(np.int64)
        return frame

    def predict(self, rows):
        return self.model.predict(self.prepare_features(rows))


def load_verified_registry(settings, handoff, reference):
    if reference is None:
        raise ValueError("Verified registry requires its trusted local reference")
    version, tags, params, version_tags = verify_registry_record(settings, handoff)
    package, signature, frozen = verify_package(settings, handoff, reference)
    import mlflow.pyfunc
    # Alias/version/source resolution above is mandatory. Loading this verified
    # mapped directory avoids global tracking-state changes and macOS URI rewrites.
    model = mlflow.pyfunc.load_model(str(package))
    raw = model._model_impl.get_raw_model()
    from sklearn.ensemble import ExtraTreesRegressor
    if type(raw) is not ExtraTreesRegressor or list(raw.feature_names_in_) != reference.feature_names:
        raise ValueError("Registered estimator type/schema mismatch")
    if raw.get_params(deep=False) != frozen.get_params(deep=False) or len(raw.estimators_) != len(frozen.estimators_):
        raise ValueError("Registered estimator parameters differ from frozen reference")
    for actual, expected in zip(raw.estimators_, frozen.estimators_):
        a, b = actual.tree_.__getstate__(), expected.tree_.__getstate__()
        if a.keys() != b.keys() or any(
            not np.array_equal(a[k], b[k]) if isinstance(a[k], np.ndarray) else a[k] != b[k] for k in a
        ):
            raise ValueError("Registered fitted tree differs from frozen reference")
    provenance = {
        "registered_name": NAME, "registered_alias": ALIAS, "registered_version": str(version["version"]),
        "registered_run_id": version["run_id"], "registered_model_id": handoff["model_id"],
        "registered_artifact_fingerprint": handoff["package_sha256"]["model.skops"][:16],
        "registry_database_fingerprint": handoff["database_sha256"][:16],
        "signature_integer_features": sorted(INTEGER_FEATURES),
        "fitted_trees_equal_to_frozen": len(raw.estimators_),
        "registry_provenance_basis": {
            "raw_run_cohort": tags["cohort"], "normalized_cohort": "peer_cohort",
            "role": tags["role"], "dvc_model_md5": tags["dvc_model_md5"],
            "units_evidence": "registered description + daily-yield target + frozen lineage and parity",
            "model_variant_evidence": "primary_candidate run + verified ExtraTrees/frozen fitted trees",
            "version_tags": version_tags, "artifact_path_resolution": "hash-verified local mapping; original records unchanged",
        },
    }
    return VerifiedRegistryModel(model, reference, signature, provenance), str(version["version"])
