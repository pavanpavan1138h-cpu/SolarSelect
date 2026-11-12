"""Process configuration; only operators can select artifact sources."""
import os
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

@dataclass(frozen=True)
class Settings:
    root: Path = field(default_factory=lambda: Path(os.getenv("SOLARSELECT_ROOT", REPOSITORY_ROOT)).resolve())
    model_source: str = field(default_factory=lambda: os.getenv("MODEL_SOURCE", "local"))
    tracking_uri: str | None = field(default_factory=lambda: os.getenv("MLFLOW_TRACKING_URI"))
    model_uri: str | None = field(default_factory=lambda: os.getenv("MLFLOW_MODEL_URI"))
    registry_handoff: str | None = field(default_factory=lambda: os.getenv("REGISTRY_HANDOFF_FILE"))
