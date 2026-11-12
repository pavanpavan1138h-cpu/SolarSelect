"""Import only the approved registry snapshot/package; never register or load a model."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.backend.core.config import Settings
from app.backend.model_loaders.verified_registry import local_path, sha256, verify_registry_record


def prepare(archive, root=ROOT):
    handoff_path = root / "configs/registry_peer_champion.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if sha256(archive) != handoff["source_archive_sha256"]:
        raise ValueError("Supplied archive is not the reviewed Person 1 handoff")
    with zipfile.ZipFile(archive) as source:
        manifest_raw = source.read("SolarSelect/PERSON2_INTEGRATION_MANIFEST.json")
        import hashlib
        if hashlib.sha256(manifest_raw).hexdigest() != handoff["source_manifest_sha256"]:
            raise ValueError("Supplied manifest differs from reviewed handoff")
        entries = {v["path"]: v for v in json.loads(manifest_raw)["files"]}
        prefix = f"SolarSelect/mlruns/models/{handoff['model_id']}/artifacts/"
        selected = {"SolarSelect/mlflow.db": (handoff["database_relative_path"], handoff["database_sha256"])}
        for name, expected in handoff["package_sha256"].items():
            selected[prefix + name] = (handoff["artifact_relative_path"] + "/" + name, expected)
        verified = []
        for member, (relative, expected) in selected.items():
            raw = source.read(member)
            if len(raw) != entries[member]["bytes"] or hashlib.sha256(raw).hexdigest() != expected or entries[member]["sha256"] != expected:
                raise ValueError("Imported artifact fingerprint mismatch")
            destination = local_path(root, relative)
            if destination.exists() and destination.read_bytes() != raw:
                raise ValueError("Refusing to overwrite an existing different local artifact")
            verified.append((destination, raw))
        for destination, raw in verified:
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
    database = local_path(root, handoff["database_relative_path"])
    settings = Settings(root=root, model_source="mlflow", tracking_uri="sqlite:///" + database.as_posix(),
                        model_uri=f"models:/{handoff['registered_name']}@{handoff['alias']}",
                        registry_handoff=str(handoff_path))
    version, _, _, _ = verify_registry_record(settings, handoff)
    return {"verified_files": len(verified), "name": version["name"], "version": version["version"],
            "alias": handoff["alias"], "tracking_uri": settings.tracking_uri,
            "handoff_file": str(handoff_path), "registry_writes": False, "model_loading": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive.resolve()), indent=2))
