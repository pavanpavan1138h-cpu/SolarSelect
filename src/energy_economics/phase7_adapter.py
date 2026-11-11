"""
SolarSelect — Phase 8: Phase 7 Integration Adapter
Ingests, validates, and standardizes Phase 7 panel configuration results.
Preserves configuration identity, coordinates multi-candidate batches,
and enforces mathematical cross-checks without recomputing geometry.
"""

import math
from typing import Dict, Any, List, Union

from src.energy_economics.exceptions import Phase7IntegrationError


class Phase7Adapter:
    """
    Ingests and validates Phase 7 RoofFitEngine results.
    Accepts typed PanelConfigurationResult instances or contract-compliant dictionaries.
    """

    REQUIRED_FIELDS = {
        "configuration_id",
        "roof_id",
        "panel_id",
        "feasibility_status",
        "selected_orientation",
        "panel_count",
        "installed_dc_capacity_kwp",
        "module_stc_power_wp",
        "spatial_metrics",
        "placements",
        "constraint_violations",
    }

    @classmethod
    def validate_and_ingest(
        cls, result: Union[Dict[str, Any], Any]
    ) -> Dict[str, Any]:
        """
        Validates and standardizes a single Phase 7 result into a canonical dictionary.

        Args:
            result: Phase 7 PanelConfigurationResult or serialized dictionary.

        Returns:
            Validated dictionary containing all original Phase 7 fields.

        Raises:
            Phase7IntegrationError: If required fields are missing, types are invalid,
            or arithmetic capacity consistency check fails.
        """
        if result is None:
            raise Phase7IntegrationError("Phase 7 result cannot be None.")

        # Convert object with to_dict method (like PanelConfigurationResult)
        if hasattr(result, "to_dict") and callable(getattr(result, "to_dict")):
            raw_dict = result.to_dict()
        elif isinstance(result, dict):
            raw_dict = result
        else:
            raise Phase7IntegrationError(
                f"Unsupported Phase 7 result type: '{type(result).__name__}'. "
                f"Must be dict or PanelConfigurationResult."
            )

        # Check required fields
        missing_fields = cls.REQUIRED_FIELDS - set(raw_dict.keys())
        if missing_fields:
            raise Phase7IntegrationError(
                f"Phase 7 result missing required fields: {sorted(list(missing_fields))}"
            )

        # Validate identifiers
        cfg_id = raw_dict.get("configuration_id")
        if not cfg_id or not str(cfg_id).strip():
            raise Phase7IntegrationError("Phase 7 configuration_id cannot be blank or empty.")

        roof_id = raw_dict.get("roof_id")
        if not roof_id or not str(roof_id).strip():
            raise Phase7IntegrationError("Phase 7 roof_id cannot be blank or empty.")

        panel_id = raw_dict.get("panel_id")
        if not panel_id or not str(panel_id).strip():
            raise Phase7IntegrationError("Phase 7 panel_id cannot be blank or empty.")

        # Validate panel_count
        raw_count = raw_dict.get("panel_count")
        try:
            panel_count = int(raw_count)
            if panel_count < 0:
                raise ValueError()
        except (ValueError, TypeError) as e:
            raise Phase7IntegrationError(
                f"Phase 7 panel_count must be a non-negative integer, got '{raw_count}'."
            ) from e

        # Validate installed_dc_capacity_kwp
        raw_kwp = raw_dict.get("installed_dc_capacity_kwp")
        try:
            installed_kwp = float(raw_kwp)
            if math.isnan(installed_kwp) or math.isinf(installed_kwp) or installed_kwp < 0.0:
                raise ValueError()
        except (ValueError, TypeError) as e:
            raise Phase7IntegrationError(
                f"Phase 7 installed_dc_capacity_kwp must be a finite non-negative float, got '{raw_kwp}'."
            ) from e

        # Validate module_stc_power_wp
        raw_wp = raw_dict.get("module_stc_power_wp")
        try:
            stc_wp = float(raw_wp)
            if math.isnan(stc_wp) or math.isinf(stc_wp) or stc_wp <= 0.0:
                raise ValueError()
        except (ValueError, TypeError) as e:
            raise Phase7IntegrationError(
                f"Phase 7 module_stc_power_wp must be a finite positive float, got '{raw_wp}'."
            ) from e

        # Validate feasibility_status
        feasibility_status = str(raw_dict.get("feasibility_status")).strip().upper()
        if feasibility_status not in ("FEASIBLE", "INFEASIBLE"):
            raise Phase7IntegrationError(
                f"Phase 7 feasibility_status must be 'FEASIBLE' or 'INFEASIBLE', got '{feasibility_status}'."
            )

        # Arithmetic cross-check: |P_DC - (N * P_STC / 1000)| <= 1e-6 * max(1, P_DC)
        calc_kwp = (panel_count * stc_wp) / 1000.0
        tol = 1e-6 * max(1.0, installed_kwp)
        delta = abs(installed_kwp - calc_kwp)
        if delta > tol:
            raise Phase7IntegrationError(
                f"Capacity arithmetic mismatch in Phase 7 result: reported {installed_kwp} kWp, "
                f"calculated ({panel_count} * {stc_wp} Wp / 1000) = {calc_kwp} kWp (delta={delta} > tol={tol})."
            )

        # Validate structure of collections
        if not isinstance(raw_dict.get("spatial_metrics"), dict):
            raise Phase7IntegrationError("Phase 7 spatial_metrics must be a dictionary.")

        if not isinstance(raw_dict.get("placements"), list):
            raise Phase7IntegrationError("Phase 7 placements must be a list.")

        if not isinstance(raw_dict.get("constraint_violations"), list):
            raise Phase7IntegrationError("Phase 7 constraint_violations must be a list.")

        # Return sanitized copy preserving all original fields
        sanitized = dict(raw_dict)
        sanitized["configuration_id"] = str(cfg_id).strip()
        sanitized["roof_id"] = str(roof_id).strip()
        sanitized["panel_id"] = str(panel_id).strip()
        sanitized["panel_count"] = panel_count
        sanitized["installed_dc_capacity_kwp"] = installed_kwp
        sanitized["module_stc_power_wp"] = stc_wp
        sanitized["feasibility_status"] = feasibility_status
        return sanitized

    @classmethod
    def ingest_batch(
        cls, results: List[Union[Dict[str, Any], Any]]
    ) -> List[Dict[str, Any]]:
        """
        Ingests a batch of Phase 7 candidate configurations.

        Args:
            results: List of Phase 7 results.

        Returns:
            List of validated standardized dictionaries.

        Raises:
            Phase7IntegrationError: If results is not a list, is empty, or any candidate fails validation.
        """
        if not isinstance(results, list):
            raise Phase7IntegrationError("Batch ingestion requires a list of Phase 7 results.")

        if len(results) == 0:
            raise Phase7IntegrationError("Batch ingestion list cannot be empty.")

        ingested: List[Dict[str, Any]] = []
        for i, res in enumerate(results):
            try:
                ingested.append(cls.validate_and_ingest(res))
            except Phase7IntegrationError as e:
                raise Phase7IntegrationError(f"Candidate #{i} failed ingestion: {e}") from e

        return ingested

