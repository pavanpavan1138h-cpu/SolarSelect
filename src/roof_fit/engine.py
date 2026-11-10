"""
SolarSelect — Phase 7: Complete Roof-Fit Engine Public Integration Workflow
Provides a single, end-to-end callable workflow connecting:
  1. RoofSpecificationValidator
  2. CatalogueAdapter
  3. UsableAreaGenerator
  4. RowWisePlacementEngine
  5. ConstraintValidator
  6. LayoutSerializer
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from src.roof_fit.roof_validator import (
    RoofSpecification,
    RoofSpecificationValidator,
)
from src.roof_fit.catalogue_adapter import (
    PanelDimensionSpec,
    CatalogueAdapter,
)
from src.roof_fit.usable_area import (
    UsableRoofResult,
    UsableAreaGenerator,
)
from src.roof_fit.placement_engine import (
    RowWisePlacementEngine,
    PanelConfigurationResult,
)
from src.roof_fit.constraint_validator import (
    ConstraintValidator,
    PlacementValidationResult,
)
from src.roof_fit.serializer import (
    LayoutSerializer,
)
from src.roof_fit.exceptions import (
    MissingRoofParameterError,
    InvalidRoofSpecificationError,
    RoofFitError,
)


class RoofFitEngine:
    """
    Public orchestration engine for the Phase 7 Roof-Fit and Panel Configuration workflow.
    Coordinates validation, catalogue retrieval, usable envelope calculation, heuristic
    row-wise strip packing, whole-layout constraint audit, and contract serialization.
    """

    def __init__(
        self,
        catalogue_path: Optional[Union[str, Path]] = None,
        catalogue_adapter: Optional[CatalogueAdapter] = None,
        placement_engine: Optional[RowWisePlacementEngine] = None,
    ) -> None:
        """
        Initializes the RoofFitEngine with optional injected adapters.
        Defaults to the repository catalogue at configs/panels_catalogue.csv.
        """
        if catalogue_adapter is not None:
            self.catalogue = catalogue_adapter
        else:
            self.catalogue = CatalogueAdapter(catalogue_path)

        if placement_engine is not None:
            self.placement_engine = placement_engine
        else:
            self.placement_engine = RowWisePlacementEngine(catalogue_adapter=self.catalogue)

    def fit(
        self,
        roof_spec: Union[RoofSpecification, Dict[str, Any]],
        panel_id: Optional[str] = None,
        allowed_orientations: Optional[str] = None,
    ) -> PanelConfigurationResult:
        """
        Executes the complete roof-fit workflow and returns the typed PanelConfigurationResult.

        Workflow sequence:
          1. Resolve panel_id from explicit argument or roof_spec payload.
          2. Ingest and validate roof specification via RoofSpecificationValidator.
          3. Retrieve verified panel dimensions from read-only catalogue via CatalogueAdapter.
          4. Compute discrete usable interior envelope and expanded obstacle zones via UsableAreaGenerator.
          5. Execute heuristic row-wise strip packing with obstacle interruption via RowWisePlacementEngine.
          6. Audit complete array against physical constraints via ConstraintValidator.
          7. Return structured PanelConfigurationResult.

        Args:
            roof_spec: Raw roof parameters as dictionary or validated RoofSpecification.
            panel_id: Primary key of catalogue panel. If omitted, resolved from roof_spec['panel_id'].
            allowed_orientations: Optional override ('portrait', 'landscape', or 'both').

        Returns:
            PanelConfigurationResult containing optimal orientation, placements, spatial metrics,
            and constraint evaluation.
        """
        # 1. Resolve panel_id
        resolved_panel_id = self._resolve_panel_id(roof_spec, panel_id)

        # 2. Ingest and validate roof specification
        val_roof_spec = RoofSpecificationValidator.validate(roof_spec)

        # 3. Retrieve verified panel dimensions from catalogue (verifies existence)
        panel_spec = self.catalogue.get_panel_specs(resolved_panel_id)

        # 4. Generate usable interior envelope and expanded obstacle keep-out zones
        usable_res = UsableAreaGenerator.generate(val_roof_spec)

        # 5. Execute row-wise strip packing and candidate orientation selection
        config_result = self.placement_engine.fit_panels(
            roof_spec=val_roof_spec,
            panel_id=resolved_panel_id,
            allowed_orientations=allowed_orientations,
        )

        return config_result

    def run(
        self,
        roof_spec: Union[RoofSpecification, Dict[str, Any]],
        panel_id: Optional[str] = None,
        output_format: str = "dict",
        allowed_orientations: Optional[str] = None,
        indent: int = 2,
    ) -> Union[Dict[str, Any], str, PanelConfigurationResult]:
        """
        Main public entry point for Phase 7 execution.
        Executes the complete workflow and serializes the outcome according to the approved contract.

        Args:
            roof_spec: Roof parameters in contract format.
            panel_id: Catalogue panel identifier (optional if specified in roof_spec).
            output_format: Desired return type: 'dict' (default), 'json', or 'result'/'object'.
            allowed_orientations: Optional orientation constraint override.
            indent: JSON indentation if output_format='json'.

        Returns:
            Serialized dictionary, formatted JSON string, or typed PanelConfigurationResult.
        """
        config_result = self.fit(
            roof_spec=roof_spec,
            panel_id=panel_id,
            allowed_orientations=allowed_orientations,
        )

        fmt = output_format.lower()
        if fmt == "dict":
            return LayoutSerializer.to_dict(config_result)
        elif fmt == "json":
            return LayoutSerializer.to_json(config_result, indent=indent)
        elif fmt in ("result", "object"):
            return config_result
        else:
            raise ValueError(
                f"Unsupported output_format: '{output_format}'. "
                f"Must be 'dict', 'json', or 'result'."
            )

    def run_dict(
        self,
        roof_spec: Union[RoofSpecification, Dict[str, Any]],
        panel_id: Optional[str] = None,
        allowed_orientations: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience method returning serialized dictionary matching contract schema."""
        res = self.run(
            roof_spec=roof_spec,
            panel_id=panel_id,
            output_format="dict",
            allowed_orientations=allowed_orientations,
        )
        assert isinstance(res, dict)
        return res

    def run_json(
        self,
        roof_spec: Union[RoofSpecification, Dict[str, Any]],
        panel_id: Optional[str] = None,
        indent: int = 2,
        allowed_orientations: Optional[str] = None,
    ) -> str:
        """Convenience method returning formatted JSON string matching contract schema."""
        res = self.run(
            roof_spec=roof_spec,
            panel_id=panel_id,
            output_format="json",
            allowed_orientations=allowed_orientations,
            indent=indent,
        )
        assert isinstance(res, str)
        return res

    def list_supported_panels(self) -> List[str]:
        """Returns sorted list of all available panel IDs in the loaded catalogue."""
        return self.catalogue.list_all_panel_ids()

    def get_panel_specs(self, panel_id: str) -> PanelDimensionSpec:
        """Retrieves verified panel dimensions and electrical ratings."""
        return self.catalogue.get_panel_specs(panel_id)

    @staticmethod
    def _resolve_panel_id(
        roof_spec: Union[RoofSpecification, Dict[str, Any]], panel_id: Optional[str]
    ) -> str:
        """Resolves panel_id from explicit argument or roof_spec dictionary."""
        if panel_id is not None and str(panel_id).strip():
            return str(panel_id).strip()

        if isinstance(roof_spec, dict) and "panel_id" in roof_spec:
            pid = roof_spec.get("panel_id")
            if pid is not None and str(pid).strip():
                return str(pid).strip()

        raise MissingRoofParameterError("Missing required parameter: 'panel_id'")

