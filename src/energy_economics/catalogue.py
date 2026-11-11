"""
SolarSelect — Phase 8: Read-Only Panel Catalogue Reader
Provides clean, read-only access to configs/panels_catalogue.csv for Phase 8.
Preserves all 43 attributes, strictly preserves missing values as None,
and never writes to or modifies the source catalogue files.
"""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from src.energy_economics.exceptions import (
    CatalogueIntegrationError,
    PanelNotFoundError,
)


@dataclass(frozen=True)
class PanelRecord:
    """Immutable representation of a canonical panel record with full attributes."""
    panel_id: str
    manufacturer: str
    model: str
    rated_power_wp: Optional[float]
    length_mm: Optional[float]
    width_mm: Optional[float]
    thickness_mm: Optional[float]
    area_m2: Optional[float]
    weight_kg: Optional[float]
    module_efficiency_pct: Optional[float]
    cell_technology: Optional[str]
    module_type: Optional[str]
    stc_irradiance_w_m2: Optional[float]
    stc_cell_temperature_c: Optional[float]
    pmax_temp_coefficient_pct_per_c: Optional[float]
    voc_temp_coefficient_pct_per_c: Optional[float]
    isc_temp_coefficient_pct_per_c: Optional[float]
    noct_c: Optional[float]
    nmot_c: Optional[float]
    voc_v: Optional[float]
    isc_a: Optional[float]
    vmp_v: Optional[float]
    imp_a: Optional[float]
    max_system_voltage_v: Optional[float]
    max_series_fuse_rating_a: Optional[float]
    product_warranty_years: Optional[float]
    performance_warranty_years: Optional[float]
    annual_degradation_pct: Optional[float]
    end_of_warranty_power_pct: Optional[float]
    price_per_module: Optional[float]
    price_per_wp: Optional[float]
    currency: Optional[str]
    price_basis: Optional[str]
    price_region: Optional[str]
    price_confidence: Optional[str]
    price_observed_date: Optional[str]
    specification_source: Optional[str]
    specification_source_url: Optional[str]
    source_document_name: Optional[str]
    source_page: Optional[str]
    verification_status: Optional[str]
    verification_date: Optional[str]
    notes: Optional[str]
    raw_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts record to dictionary, preserving None for missing attributes."""
        d = {k: v for k, v in self.__dict__.items() if k != "raw_attributes"}
        return d


class ReadOnlyPanelCatalogue:
    """
    Read-only loader and inspector for configs/panels_catalogue.csv.
    Enforces strict immutability, missing value preservation, and field validation.
    """

    DEFAULT_CATALOGUE_PATH = Path("configs/panels_catalogue.csv")

    FLOAT_FIELDS = {
        "rated_power_wp", "length_mm", "width_mm", "thickness_mm", "area_m2",
        "weight_kg", "module_efficiency_pct", "stc_irradiance_w_m2",
        "stc_cell_temperature_c", "pmax_temp_coefficient_pct_per_c",
        "voc_temp_coefficient_pct_per_c", "isc_temp_coefficient_pct_per_c",
        "noct_c", "nmot_c", "voc_v", "isc_a", "vmp_v", "imp_a",
        "max_system_voltage_v", "max_series_fuse_rating_a",
        "product_warranty_years", "performance_warranty_years",
        "annual_degradation_pct", "end_of_warranty_power_pct",
        "price_per_module", "price_per_wp"
    }

    STR_FIELDS = {
        "panel_id", "manufacturer", "model", "cell_technology", "module_type",
        "currency", "price_basis", "price_region", "price_confidence",
        "price_observed_date", "specification_source", "specification_source_url",
        "source_document_name", "source_page", "verification_status",
        "verification_date", "notes"
    }

    REQUIRED_SCHEMA_COLS = {"panel_id", "manufacturer", "model"}

    PROVENANCE_QUALIFICATION = (
        "Technical specifications are extracted from local compiled reference PDF files "
        "under data/reference/panel_datasheets/, which represent compiled specification summaries, "
        "not independently authenticated original manufacturer datasheets. "
        "Original manufacturer source URLs were not independently verified during Phase 6."
    )

    def __init__(self, catalogue_path: Optional[Path] = None) -> None:
        self.catalogue_path = Path(catalogue_path or self.DEFAULT_CATALOGUE_PATH)
        if not self.catalogue_path.exists():
            raise CatalogueIntegrationError(f"Catalogue file not found: {self.catalogue_path}")

        self._records: Dict[str, PanelRecord] = {}
        self._initial_file_hash = self.compute_file_sha256()
        self._load_catalogue()

    def compute_file_sha256(self) -> str:
        """Computes SHA-256 of the source catalogue file on disk."""
        hasher = hashlib.sha256()
        with open(self.catalogue_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def verify_source_integrity(self) -> bool:
        """Verifies that the source catalogue file has not been altered since initialization."""
        current_hash = self.compute_file_sha256()
        return current_hash == self._initial_file_hash

    def _load_catalogue(self) -> None:
        """Parses catalogue CSV, validating schema structure and preserving nulls."""
        try:
            df = pd.read_csv(self.catalogue_path)
        except Exception as e:
            raise CatalogueIntegrationError(
                f"Failed to read catalogue CSV at {self.catalogue_path}: {e}"
            ) from e

        missing_cols = self.REQUIRED_SCHEMA_COLS - set(df.columns)
        if missing_cols:
            raise CatalogueIntegrationError(
                f"Catalogue CSV missing required columns: {sorted(list(missing_cols))}"
            )

        for _, row in df.iterrows():
            raw_pid = row["panel_id"]
            if pd.isna(raw_pid):
                continue
            pid = str(raw_pid).strip()
            if not pid:
                continue

            if pid in self._records:
                raise CatalogueIntegrationError(
                    f"Duplicate panel_id found in catalogue CSV: '{pid}'"
                )

            record_dict: Dict[str, Any] = {"panel_id": pid}

            # Parse string fields
            for s_field in self.STR_FIELDS:
                if s_field == "panel_id":
                    continue
                if s_field in row and not pd.isna(row[s_field]):
                    val_str = str(row[s_field]).strip()
                    record_dict[s_field] = val_str if val_str else None
                else:
                    record_dict[s_field] = None

            # Parse float fields
            for f_field in self.FLOAT_FIELDS:
                if f_field in row and not pd.isna(row[f_field]):
                    try:
                        record_dict[f_field] = float(row[f_field])
                    except (ValueError, TypeError):
                        record_dict[f_field] = None
                else:
                    record_dict[f_field] = None

            record_dict["raw_attributes"] = row.to_dict()
            self._records[pid] = PanelRecord(**record_dict)

    def list_panel_ids(self) -> List[str]:
        """Returns sorted list of panel IDs in the loaded catalogue."""
        return sorted(list(self._records.keys()))

    def has_panel(self, panel_id: str) -> bool:
        """Checks if a panel ID exists in the catalogue."""
        return str(panel_id).strip() in self._records

    def get_panel(self, panel_id: str) -> PanelRecord:
        """Retrieves PanelRecord by ID. Raises PanelNotFoundError if missing."""
        pid = str(panel_id).strip()
        if pid not in self._records:
            raise PanelNotFoundError(f"Panel ID '{pid}' not found in catalogue.")
        return self._records[pid]

    def validate_panel_record(self, panel_id: str) -> Tuple[bool, List[str]]:
        """
        Validates completeness and physicality of a panel record.
        Returns (is_valid, list_of_errors).
        """
        errors: List[str] = []
        if not self.has_panel(panel_id):
            return False, [f"Panel '{panel_id}' does not exist in catalogue."]

        record = self.get_panel(panel_id)

        # Rated power check
        if record.rated_power_wp is None:
            errors.append(f"Panel '{panel_id}' missing rated_power_wp.")
        elif record.rated_power_wp <= 0:
            errors.append(f"Panel '{panel_id}' rated_power_wp must be strictly positive: {record.rated_power_wp}.")

        # Physical dimensions check
        if record.length_mm is None or record.width_mm is None:
            errors.append(f"Panel '{panel_id}' missing length_mm or width_mm.")
        else:
            if record.length_mm <= 0 or record.width_mm <= 0:
                errors.append(
                    f"Panel '{panel_id}' dimensions must be strictly positive: {record.length_mm}x{record.width_mm}mm."
                )

        return len(errors) == 0, errors

    def get_provenance(self, panel_id: str) -> Dict[str, Any]:
        """Returns provenance and verification metadata for a panel with qualification."""
        record = self.get_panel(panel_id)
        return {
            "panel_id": record.panel_id,
            "specification_source": record.specification_source,
            "specification_source_url": record.specification_source_url,
            "source_document_name": record.source_document_name,
            "source_page": record.source_page,
            "verification_status": record.verification_status,
            "verification_date": record.verification_date,
            "notes": record.notes,
            "provenance_qualification": self.PROVENANCE_QUALIFICATION,
        }

