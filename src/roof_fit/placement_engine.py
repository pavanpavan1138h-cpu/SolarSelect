"""
SolarSelect — Phase 7: Row-Wise Strip Packing Placement Engine
Implements deterministic row-wise panel placement with obstacle interruption
and resumption, orientation comparison, and zero-tolerance physical constraint validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from src.roof_fit.exceptions import (
    RoofFitError,
    PanelNotFoundError,
    InvalidRoofSpecificationError,
)
from src.roof_fit.geometry import IntegerRectangle
from src.roof_fit.quantization import (
    quantize_clearance,
    from_geometry_units,
)
from src.roof_fit.roof_validator import (
    RoofSpecification,
    RoofSpecificationValidator,
)
from src.roof_fit.catalogue_adapter import (
    PanelDimensionSpec,
    CatalogueAdapter,
)
from src.roof_fit.usable_area import (
    ExpandedObstacle,
    UsableRoofResult,
    UsableAreaGenerator,
)
from src.roof_fit.constraint_validator import (
    ConstraintValidator,
    PlacementValidationResult,
)


@dataclass(frozen=True)
class PanelPlacement:
    """Individual placed panel instance with coordinates and grid indices."""
    panel_index: int
    row_id: int
    col_id: int
    x_m: float
    y_m: float
    width_m: float
    height_m: float
    orientation: str
    rect: IntegerRectangle

    def to_dict(self) -> Dict[str, Any]:
        """Serializes placement to dict matching Phase 7 I/O contract."""
        return {
            "panel_index": self.panel_index,
            "row_id": self.row_id,
            "col_id": self.col_id,
            "x_m": self.x_m,
            "y_m": self.y_m,
            "width_m": self.width_m,
            "height_m": self.height_m,
            "orientation": self.orientation,
        }


@dataclass(frozen=True)
class OrientationCandidateResult:
    """Outcome of packing a single orientation (portrait or landscape)."""
    orientation: str
    feasible: bool
    panel_count: int
    dc_capacity_kwp: float
    placements: List[PanelPlacement] = field(default_factory=list)
    rectangles: List[IntegerRectangle] = field(default_factory=list)
    spatial_metrics: Dict[str, float] = field(default_factory=dict)
    unutilized_usable_area_m2: float = 0.0


@dataclass(frozen=True)
class PanelConfigurationResult:
    """Complete Phase 7 configuration result matching the approved contract schema."""
    configuration_id: str
    roof_id: str
    panel_id: str
    panel_model: str
    feasibility_status: str
    selected_orientation: str
    panel_count: int
    installed_dc_capacity_kwp: float
    module_stc_power_wp: float
    spatial_metrics: Dict[str, float]
    placements: List[Dict[str, Any]]
    alternatives_evaluated: Dict[str, Any]
    constraint_violations: List[str]
    engine_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serializes configuration result to dictionary."""
        return {
            "configuration_id": self.configuration_id,
            "roof_id": self.roof_id,
            "panel_id": self.panel_id,
            "panel_model": self.panel_model,
            "feasibility_status": self.feasibility_status,
            "selected_orientation": self.selected_orientation,
            "panel_count": self.panel_count,
            "installed_dc_capacity_kwp": self.installed_dc_capacity_kwp,
            "module_stc_power_wp": self.module_stc_power_wp,
            "spatial_metrics": self.spatial_metrics,
            "placements": self.placements,
            "alternatives_evaluated": self.alternatives_evaluated,
            "constraint_violations": self.constraint_violations,
            "engine_metadata": self.engine_metadata,
        }


class RowWisePlacementEngine:
    """
    Deterministic Row-Wise Strip Packing Engine with Obstacle Interruption and Resumption.
    Evaluates supported panel orientations and identifies the best feasible configuration.
    """

    ALGORITHM_NAME = "RowWiseStripPackingEngine"
    ALGORITHM_VERSION = "1.0.0"
    RATIONALE = "Continuous linear racking rail compliance with obstacle interruption"
    OPTIMALITY_NOTE = "BEST_FEASIBLE_CONFIGURATION_FOUND"
    DISCLAIMER = (
        "The engine generates geometrically feasible panel placements under the supplied roof geometry, "
        "module dimensions, clearances and obstacle assumptions. These results do not establish "
        "structural safety, regulatory compliance or installation approval."
    )

    def __init__(self, catalogue_adapter: Optional[CatalogueAdapter] = None) -> None:
        self.catalogue = catalogue_adapter or CatalogueAdapter()

    def pack_orientation(
        self,
        roof_spec: RoofSpecification,
        panel_spec: PanelDimensionSpec,
        orientation: str,
        usable_res: UsableRoofResult,
    ) -> OrientationCandidateResult:
        """
        Executes deterministic row-wise strip packing for a single orientation.
        Handles obstacle interruption and resumption along the X-axis for every row.
        """
        if orientation == "portrait":
            w_int = panel_spec.width_int
            h_int = panel_spec.length_int
            panel_w_m = panel_spec.width_m
            panel_h_m = panel_spec.length_m
        elif orientation == "landscape":
            w_int = panel_spec.length_int
            h_int = panel_spec.width_int
            panel_w_m = panel_spec.length_m
            panel_h_m = panel_spec.width_m
        else:
            raise ValueError(f"Unsupported orientation: '{orientation}'")

        g_p_int = quantize_clearance(roof_spec.clamping_gap)
        g_r_int = quantize_clearance(roof_spec.walkway_gap)

        env = usable_res.usable_envelope
        x_min, y_min = env.x_min, env.y_min
        x_max, y_max = env.x_max, env.y_max

        # Quick rejection if usable space cannot accommodate a single module
        if (x_max - x_min < w_int) or (y_max - y_min < h_int):
            spatial_metrics = self._compute_spatial_metrics(
                usable_res=usable_res,
                placed_count=0,
                panel_w_m=panel_w_m,
                panel_h_m=panel_h_m,
            )
            return OrientationCandidateResult(
                orientation=orientation,
                feasible=False,
                panel_count=0,
                dc_capacity_kwp=0.0,
                placements=[],
                rectangles=[],
                spatial_metrics=spatial_metrics,
                unutilized_usable_area_m2=spatial_metrics["unutilized_usable_area_m2"],
            )

        placements: List[PanelPlacement] = []
        panel_rectangles: List[IntegerRectangle] = []

        global_panel_index = 0
        row_id = 0
        y_cand = y_min

        # Advance along Y-axis by row height + inter-row walkway gap
        while y_cand + h_int <= y_max:
            row_id += 1
            x_cand = x_min
            col_id = 0

            # Advance along X-axis within the current row
            while x_cand + w_int <= x_max:
                cand_rect = IntegerRectangle(x_cand, y_cand, x_cand + w_int, y_cand + h_int)

                # Identify any expanded obstacle colliding with this candidate panel
                colliding_obs = [
                    obs for obs in usable_res.expanded_obstacles
                    if cand_rect.has_positive_area_overlap(obs.expanded_rect)
                ]

                if not colliding_obs:
                    # No obstacle collision. Verify boundary and non-overlap
                    val_res = ConstraintValidator.validate_candidate(
                        candidate=cand_rect,
                        usable_envelope=env,
                        obstacles=usable_res.expanded_obstacles,
                        placed_panels=panel_rectangles,
                        raise_on_violation=False,
                    )
                    if val_res.is_valid:
                        global_panel_index += 1
                        col_id += 1
                        placement = PanelPlacement(
                            panel_index=global_panel_index,
                            row_id=row_id,
                            col_id=col_id,
                            x_m=round(from_geometry_units(x_cand), 4),
                            y_m=round(from_geometry_units(y_cand), 4),
                            width_m=round(from_geometry_units(w_int), 4),
                            height_m=round(from_geometry_units(h_int), 4),
                            orientation=orientation,
                            rect=cand_rect,
                        )
                        placements.append(placement)
                        panel_rectangles.append(cand_rect)

                        # Advance X past current panel plus required inter-panel clearance
                        x_cand = x_cand + w_int + g_p_int
                    else:
                        # Should not happen under regular grid, advance 1 unit safely
                        x_cand += 1
                else:
                    # Obstacle Interruption:
                    # Resume placement after the right-most edge of all colliding obstacles
                    max_obs_x_max = max(obs.expanded_rect.x_max for obs in colliding_obs)
                    # Advance x_cand strictly past the obstacle exclusion zone
                    x_cand = max(x_cand + 1, max_obs_x_max)

            # Advance to next row
            y_cand = y_cand + h_int + g_r_int

        count = len(placements)
        dc_kwp = round(count * panel_spec.rated_power_wp / 1000.0, 3)
        spatial_metrics = self._compute_spatial_metrics(
            usable_res=usable_res,
            placed_count=count,
            panel_w_m=panel_w_m,
            panel_h_m=panel_h_m,
        )

        return OrientationCandidateResult(
            orientation=orientation,
            feasible=count > 0,
            panel_count=count,
            dc_capacity_kwp=dc_kwp,
            placements=placements,
            rectangles=panel_rectangles,
            spatial_metrics=spatial_metrics,
            unutilized_usable_area_m2=spatial_metrics["unutilized_usable_area_m2"],
        )

    def fit_panels(
        self,
        roof_spec: Union[RoofSpecification, Dict[str, Any]],
        panel_id: str,
        allowed_orientations: Optional[str] = None,
    ) -> PanelConfigurationResult:
        """
        Main entry point for Phase 7 panel configuration.
        Validates specification, extracts panel dimensions, evaluates allowed orientations,
        selects the best feasible configuration, and validates all constraints.
        """
        # 1. Ingest and validate roof specification
        val_spec = RoofSpecificationValidator.validate(roof_spec)

        # 2. Extract verified panel dimensions from catalogue
        panel_spec = self.catalogue.get_panel_specs(panel_id)

        # 3. Generate usable envelope and outward expanded obstacle zones
        usable_res = UsableAreaGenerator.generate(val_spec)

        # 4. Determine orientations to evaluate
        orientations_to_eval = self._get_orientations_to_evaluate(
            user_override=allowed_orientations,
            spec_allowed=val_spec.allowed_orientations,
        )

        # 5. Evaluate orientations deterministically
        eval_results: Dict[str, OrientationCandidateResult] = {}
        for orient in ["portrait", "landscape"]:
            if orient in orientations_to_eval:
                cand = self.pack_orientation(
                    roof_spec=val_spec,
                    panel_spec=panel_spec,
                    orientation=orient,
                    usable_res=usable_res,
                )
                eval_results[orient] = cand
            else:
                eval_results[orient] = OrientationCandidateResult(
                    orientation=orient,
                    feasible=False,
                    panel_count=0,
                    dc_capacity_kwp=0.0,
                )

        # 6. Compare candidate layouts using deterministic tie-breakers
        best_candidate = self._select_best_candidate(
            portrait_res=eval_results.get("portrait"),
            landscape_res=eval_results.get("landscape"),
        )

        # 7. Determine feasibility status
        if best_candidate and best_candidate.panel_count > 0:
            feasibility_status = "FEASIBLE"
            selected_orientation = best_candidate.orientation
            selected_placements = [p.to_dict() for p in best_candidate.placements]
            selected_rectangles = best_candidate.rectangles
            panel_count = best_candidate.panel_count
            dc_capacity_kwp = best_candidate.dc_capacity_kwp
            spatial_metrics = best_candidate.spatial_metrics
        else:
            selected_orientation = "none"
            selected_placements = []
            selected_rectangles = []
            panel_count = 0
            dc_capacity_kwp = 0.0
            spatial_metrics = self._compute_spatial_metrics(
                usable_res=usable_res,
                placed_count=0,
                panel_w_m=panel_spec.width_m,
                panel_h_m=panel_spec.length_m,
            )

            # Determine whether rejection was due to obstacle crowding or small roof
            if usable_res.usable_envelope.width >= min(panel_spec.width_int, panel_spec.length_int) and \
               usable_res.usable_envelope.height >= min(panel_spec.width_int, panel_spec.length_int) and \
               len(usable_res.expanded_obstacles) > 0:
                feasibility_status = "INFEASIBLE_OBSTACLE_COLLISION"
            else:
                feasibility_status = "INFEASIBLE_ROOF_TOO_SMALL"

        # 8. Post-placement layout constraint audit
        violations: List[str] = []
        if selected_rectangles:
            layout_val = ConstraintValidator.validate_layout(
                placed_panels=selected_rectangles,
                usable_envelope=usable_res.usable_envelope,
                obstacles=usable_res.expanded_obstacles,
                raise_on_violation=False,
            )
            violations = [v.message for v in layout_val.violations]
            if not layout_val.is_valid:
                feasibility_status = "INFEASIBLE_CONSTRAINT_VIOLATION"

        # 9. Assemble alternatives evaluated summary
        alternatives_evaluated = {
            "portrait": {
                "feasible": eval_results["portrait"].feasible,
                "panel_count": eval_results["portrait"].panel_count,
                "dc_capacity_kwp": eval_results["portrait"].dc_capacity_kwp,
            },
            "landscape": {
                "feasible": eval_results["landscape"].feasible,
                "panel_count": eval_results["landscape"].panel_count,
                "dc_capacity_kwp": eval_results["landscape"].dc_capacity_kwp,
            },
        }

        # 10. Engine metadata
        engine_metadata = {
            "algorithm": self.ALGORITHM_NAME,
            "algorithm_version": self.ALGORITHM_VERSION,
            "algorithm_selection_rationale": self.RATIONALE,
            "optimality_guarantee": self.OPTIMALITY_NOTE,
            "disclaimer": self.DISCLAIMER,
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        cfg_id = f"CFG-{val_spec.roof_id}-{panel_id}-{selected_orientation.upper()}"

        return PanelConfigurationResult(
            configuration_id=cfg_id,
            roof_id=val_spec.roof_id,
            panel_id=panel_id,
            panel_model=panel_spec.model,
            feasibility_status=feasibility_status,
            selected_orientation=selected_orientation,
            panel_count=panel_count,
            installed_dc_capacity_kwp=dc_capacity_kwp,
            module_stc_power_wp=panel_spec.rated_power_wp,
            spatial_metrics=spatial_metrics,
            placements=selected_placements,
            alternatives_evaluated=alternatives_evaluated,
            constraint_violations=violations,
            engine_metadata=engine_metadata,
        )

    @staticmethod
    def _get_orientations_to_evaluate(
        user_override: Optional[str], spec_allowed: str
    ) -> List[str]:
        """Resolves which orientations should be tested."""
        orient = (user_override or spec_allowed).lower()
        if orient == "portrait":
            return ["portrait"]
        if orient == "landscape":
            return ["landscape"]
        if orient == "both":
            return ["portrait", "landscape"]
        raise InvalidRoofSpecificationError(f"Invalid allowed_orientations: '{orient}'")

    @staticmethod
    def _select_best_candidate(
        portrait_res: Optional[OrientationCandidateResult],
        landscape_res: Optional[OrientationCandidateResult],
    ) -> Optional[OrientationCandidateResult]:
        """
        Compares portrait and landscape candidates using deterministic tie-breakers:
        1. Maximize panel count (primary).
        2. Maximize installed DC capacity.
        3. Minimize unutilized usable area.
        4. Stable orientation preference: portrait preferred over landscape.
        """
        p_valid = portrait_res is not None and portrait_res.feasible and portrait_res.panel_count > 0
        l_valid = landscape_res is not None and landscape_res.feasible and landscape_res.panel_count > 0

        if p_valid and not l_valid:
            return portrait_res
        if l_valid and not p_valid:
            return landscape_res
        if not p_valid and not l_valid:
            # Neither feasible; return portrait if evaluated else landscape
            return portrait_res or landscape_res

        # Both valid: compare primary and tie-breakers
        assert portrait_res is not None and landscape_res is not None

        # 1. Panel count
        if portrait_res.panel_count > landscape_res.panel_count:
            return portrait_res
        if landscape_res.panel_count > portrait_res.panel_count:
            return landscape_res

        # 2. DC capacity (in case of differing module specs)
        if portrait_res.dc_capacity_kwp > landscape_res.dc_capacity_kwp:
            return portrait_res
        if landscape_res.dc_capacity_kwp > portrait_res.dc_capacity_kwp:
            return landscape_res

        # 3. Unutilized usable area (lower is better)
        if portrait_res.unutilized_usable_area_m2 < landscape_res.unutilized_usable_area_m2:
            return portrait_res
        if landscape_res.unutilized_usable_area_m2 < portrait_res.unutilized_usable_area_m2:
            return landscape_res

        # 4. Stable tie-breaker: Portrait preferred
        return portrait_res

    @staticmethod
    def _compute_spatial_metrics(
        usable_res: UsableRoofResult,
        placed_count: int,
        panel_w_m: float,
        panel_h_m: float,
    ) -> Dict[str, float]:
        """Computes comprehensive spatial and packing metrics."""
        gross_m2 = round(usable_res.gross_area_m2, 4)
        usable_env_m2 = round(usable_res.usable_envelope_area_m2, 4)
        setback_m2 = round(max(0.0, gross_m2 - usable_env_m2), 4)

        # Obstacle exclusion area within usable envelope
        obs_m2 = round(max(0.0, usable_env_m2 - usable_res.effective_usable_area_estimate_m2), 4)
        net_usable_m2 = round(usable_res.effective_usable_area_estimate_m2, 4)

        occupied_m2 = round(placed_count * panel_w_m * panel_h_m, 4)
        unutilized_m2 = round(max(0.0, net_usable_m2 - occupied_m2), 4)

        utilization_factor = round(occupied_m2 / gross_m2, 4) if gross_m2 > 0 else 0.0
        packing_efficiency = round(occupied_m2 / net_usable_m2, 4) if net_usable_m2 > 0 else 0.0

        return {
            "gross_roof_area_m2": gross_m2,
            "perimeter_setback_area_m2": setback_m2,
            "obstacle_exclusion_area_m2": obs_m2,
            "net_usable_roof_area_m2": net_usable_m2,
            "occupied_panel_area_m2": occupied_m2,
            "unutilized_usable_area_m2": unutilized_m2,
            "roof_utilization_factor": min(1.0, utilization_factor),
            "usable_space_packing_efficiency": min(1.0, packing_efficiency),
        }

