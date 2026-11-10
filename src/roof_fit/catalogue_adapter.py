"""
SolarSelect — Phase 7: Panel Catalogue Adapter
Provides read-only access to configs/panels_catalogue.csv, extracting and quantizing
panel physical dimensions and electrical ratings for spatial placement.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from src.roof_fit.exceptions import (
    CatalogueError,
    PanelNotFoundError,
    MissingPanelDimensionError,
    InvalidPanelDimensionError,
)
from src.roof_fit.quantization import quantize_panel_dimension_mm


@dataclass(frozen=True)
class PanelDimensionSpec:
    """Immutable representation of a catalogue panel's dimensions and ratings."""
    panel_id: str
    manufacturer: str
    model: str
    length_mm: float
    width_mm: float
    thickness_mm: Optional[float]
    rated_power_wp: float
    length_m: float
    width_m: float
    length_int: int
    width_int: int
    area_m2: float


class CatalogueAdapter:
    """
    Read-only adapter for configs/panels_catalogue.csv.
    Caches panel physical parameters and quantized integer dimensions.
    """

    DEFAULT_CATALOGUE_PATH = Path("configs/panels_catalogue.csv")

    def __init__(self, catalogue_path: Optional[Path] = None) -> None:
        self.catalogue_path = Path(catalogue_path or self.DEFAULT_CATALOGUE_PATH)
        if not self.catalogue_path.exists():
            raise CatalogueError(f"Catalogue file not found: {self.catalogue_path}")
        self._panel_cache: Dict[str, PanelDimensionSpec] = {}
        self._load_catalogue()

    def _load_catalogue(self) -> None:
        """Loads and parses the catalogue CSV into structured immutable specs."""
        try:
            df = pd.read_csv(self.catalogue_path)
        except Exception as e:
            raise CatalogueError(f"Failed to read catalogue CSV at {self.catalogue_path}: {e}") from e

        # In configs/panels_catalogue.csv, model column is named 'model'
        required_cols = {"panel_id", "manufacturer", "model", "length_mm", "width_mm", "rated_power_wp"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise CatalogueError(f"Catalogue CSV missing required columns: {sorted(list(missing_cols))}")

        for _, row in df.iterrows():
            pid = str(row["panel_id"]).strip()
            if not pid or pd.isna(row["panel_id"]):
                continue

            if pid in self._panel_cache:
                raise CatalogueError(f"Duplicate panel_id found in catalogue CSV: '{pid}'")

            # Check dimensions presence
            if pd.isna(row["length_mm"]) or pd.isna(row["width_mm"]):
                raise MissingPanelDimensionError(f"Panel '{pid}' has null length or width.")

            try:
                l_mm = float(row["length_mm"])
                w_mm = float(row["width_mm"])
            except (ValueError, TypeError) as e:
                raise InvalidPanelDimensionError(f"Panel '{pid}' dimensions must be numeric: {e}") from e

            if l_mm <= 0.0 or w_mm <= 0.0:
                raise InvalidPanelDimensionError(f"Panel '{pid}' dimensions must be strictly positive: {l_mm}x{w_mm}")

            # Thickness
            thickness_mm: Optional[float] = None
            if "thickness_mm" in row and not pd.isna(row["thickness_mm"]):
                try:
                    thickness_mm = float(row["thickness_mm"])
                except (ValueError, TypeError):
                    pass

            # Rated power
            try:
                p_wp = float(row["rated_power_wp"])
            except (ValueError, TypeError) as e:
                raise CatalogueError(f"Panel '{pid}' rated_power_wp must be numeric: {e}") from e

            # Quantized integers
            l_int = quantize_panel_dimension_mm(l_mm)
            w_int = quantize_panel_dimension_mm(w_mm)

            spec = PanelDimensionSpec(
                panel_id=pid,
                manufacturer=str(row["manufacturer"]).strip(),
                model=str(row["model"]).strip(),
                length_mm=l_mm,
                width_mm=w_mm,
                thickness_mm=thickness_mm,
                rated_power_wp=p_wp,
                length_m=l_mm / 1000.0,
                width_m=w_mm / 1000.0,
                length_int=l_int,
                width_int=w_int,
                area_m2=(l_mm / 1000.0) * (w_mm / 1000.0),
            )
            self._panel_cache[pid] = spec

    def get_panel_specs(self, panel_id: str) -> PanelDimensionSpec:
        """Retrieves verified dimensions and ratings for a given panel_id."""
        if not panel_id:
            raise PanelNotFoundError("panel_id cannot be empty.")
        clean_id = str(panel_id).strip()
        if clean_id not in self._panel_cache:
            raise PanelNotFoundError(f"Panel ID '{clean_id}' not found in catalogue at {self.catalogue_path}")
        return self._panel_cache[clean_id]

    def list_all_panel_ids(self) -> List[str]:
        """Returns sorted list of all available panel IDs."""
        return sorted(list(self._panel_cache.keys()))

    def get_all_panel_specs(self) -> Dict[str, PanelDimensionSpec]:
        """Returns a copy of all loaded panel specifications."""
        return dict(self._panel_cache)

