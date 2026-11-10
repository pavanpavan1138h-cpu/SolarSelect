"""
SolarSelect — Phase 7: Complete Roof-Fit Engine Integration Test Suite
Verifies end-to-end workflow execution connecting:
  RoofSpecificationValidator -> CatalogueAdapter -> UsableAreaGenerator
  -> RowWisePlacementEngine -> ConstraintValidator -> LayoutSerializer

Covers all 8 required integration test categories:
  A. Basic End-to-End Execution
  B. Catalogue Integration
  C. Geometry Integration
  D. Orientation Integration
  E. Infeasible Layouts
  F. Serialization & Contract Conformance
  G. Determinism (100-run identical outputs)
  H. Failure Propagation & Exception Mapping
"""

import json
from pathlib import Path
import pytest

from src.roof_fit.engine import RoofFitEngine
from src.roof_fit.exceptions import (
    PanelNotFoundError,
    InvalidRoofSpecificationError,
    MissingRoofParameterError,
    InvalidObstacleSpecificationError,
    MissingPanelDimensionError,
)
from src.roof_fit.roof_validator import RoofSpecification, ObstacleSpecification
from src.roof_fit.placement_engine import PanelConfigurationResult
from src.roof_fit.catalogue_adapter import CatalogueAdapter
from src.roof_fit.geometry import IntegerRectangle


@pytest.fixture(scope="module")
def engine():
    """Initializes RoofFitEngine with verified repository catalogue."""
    return RoofFitEngine(catalogue_path=Path("configs/panels_catalogue.csv"))


# =====================================================================
# A. Basic End-to-End Execution Scenarios
# =====================================================================

class TestBasicEndToEndExecution:
    """Verifies end-to-end workflow execution from user input to serialized output."""

    def test_e2e_valid_roof_and_panel_produces_valid_dict(self, engine):
        """Standard residential rooftop returns conforming dictionary with placed panels."""
        spec = {
            "roof_id": "E2E-RES-01",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "panel_id": "PNL-REC-ALPHA-420W",
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
        }
        res_dict = engine.run(spec)

        assert isinstance(res_dict, dict)
        assert res_dict["feasibility_status"] == "FEASIBLE"
        assert res_dict["roof_id"] == "E2E-RES-01"
        assert res_dict["panel_id"] == "PNL-REC-ALPHA-420W"
        assert res_dict["panel_count"] > 0
        assert res_dict["installed_dc_capacity_kwp"] > 0.0
        assert len(res_dict["placements"]) == res_dict["panel_count"]
        assert len(res_dict["constraint_violations"]) == 0

        # Check first placement coordinate fields
        p0 = res_dict["placements"][0]
        assert "panel_index" in p0
        assert "row_id" in p0
        assert "col_id" in p0
        assert "x_m" in p0
        assert "y_m" in p0
        assert "width_m" in p0
        assert "height_m" in p0
        assert "orientation" in p0

    def test_e2e_execution_via_explicit_panel_id_argument(self, engine):
        """Workflow accepts panel_id as explicit argument rather than inside dict."""
        spec = {
            "roof_id": "E2E-ARG-PID",
            "roof_length_m": 10.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
        }
        res_dict = engine.run(spec, panel_id="PNL-JINKO-430W")
        assert res_dict["feasibility_status"] == "FEASIBLE"
        assert res_dict["panel_id"] == "PNL-JINKO-430W"
        assert res_dict["panel_count"] > 0

    def test_e2e_execution_with_typed_roof_specification(self, engine):
        """Workflow accepts pre-constructed RoofSpecification instance."""
        spec = RoofSpecification(
            roof_id="E2E-TYPED-SPEC",
            length=15.0,
            width=10.0,
            perimeter_setback=0.50,
            clamping_gap=0.02,
            walkway_gap=0.05,
            allowed_orientations="both",
        )
        res_obj = engine.fit(spec, panel_id="PNL-CANADIAN-445W")
        assert isinstance(res_obj, PanelConfigurationResult)
        assert res_obj.feasibility_status == "FEASIBLE"
        assert res_obj.panel_count > 0


# =====================================================================
# B. Catalogue Integration Scenarios
# =====================================================================

class TestCatalogueIntegration:
    """Verifies that all 12 catalogue panels integrate cleanly through the workflow."""

    def test_all_12_catalogue_panels_fit_successfully(self, engine):
        """Every single panel model in configs/panels_catalogue.csv can be placed."""
        panel_ids = engine.list_supported_panels()
        assert len(panel_ids) == 12

        spec = {
            "roof_id": "CAT-ALL-CHECK",
            "roof_length_m": 20.0,
            "roof_width_m": 12.0,
            "perimeter_setback_m": 0.50,
        }

        for pid in panel_ids:
            res = engine.run(spec, panel_id=pid)
            assert res["feasibility_status"] == "FEASIBLE"
            assert res["panel_count"] > 0
            assert res["installed_dc_capacity_kwp"] > 0.0
            assert res["module_stc_power_wp"] > 0.0

    def test_unknown_panel_id_raises_panel_not_found(self, engine):
        """Non-existent panel ID raises PanelNotFoundError."""
        spec = {
            "roof_id": "CAT-UNKNOWN",
            "roof_length_m": 10.0,
            "roof_width_m": 10.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-FABRICATED-999W",
        }
        with pytest.raises(PanelNotFoundError) as exc_info:
            engine.run(spec)
        assert "PNL-FABRICATED-999W" in str(exc_info.value)

    def test_missing_panel_id_in_both_args_raises_missing_parameter(self, engine):
        """Omission of panel_id from both roof_spec and run() arguments raises error."""
        spec = {
            "roof_id": "CAT-MISSING-PID",
            "roof_length_m": 10.0,
            "roof_width_m": 10.0,
            "perimeter_setback_m": 0.50,
        }
        with pytest.raises(MissingRoofParameterError) as exc_info:
            engine.run(spec)
        assert "panel_id" in str(exc_info.value)


# =====================================================================
# C. Geometry Integration Scenarios
# =====================================================================

class TestGeometryIntegration:
    """Verifies setbacks, obstacles, buffers, corridors, and clearance preservation."""

    def test_setback_enforcement_boundary(self, engine):
        """All panel placements strictly remain within [setback, length - setback]."""
        setback = 0.75
        spec = {
            "roof_id": "GEO-SETBACK",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": setback,
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        res = engine.run_dict(spec)
        assert res["feasibility_status"] == "FEASIBLE"

        for p in res["placements"]:
            assert p["x_m"] >= setback - 1e-4
            assert p["y_m"] >= setback - 1e-4
            assert round(p["x_m"] + p["width_m"], 4) <= round(12.0 - setback + 1e-4, 4)
            assert round(p["y_m"] + p["height_m"], 4) <= round(8.0 - setback + 1e-4, 4)

    def test_obstacle_and_buffer_avoidance(self, engine):
        """Panels do not encroach on obstacle bounds expanded outward by buffer."""
        spec = {
            "roof_id": "GEO-OBS-BUF",
            "roof_length_m": 14.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
            "obstacles": [
                {
                    "obstacle_id": "SKYLIGHT-1",
                    "x_m": 6.0,
                    "y_m": 3.0,
                    "width_m": 1.20,
                    "height_m": 1.50,
                    "buffer_m": 0.30,
                }
            ],
        }
        res = engine.run_dict(spec)
        assert res["feasibility_status"] == "FEASIBLE"

        # Expanded obstacle box: x in [5.70, 7.50], y in [2.70, 4.80]
        obs_box = IntegerRectangle(57000, 27000, 75000, 48000)
        for p in res["placements"]:
            p_box = IntegerRectangle(
                int(round(p["x_m"] * 10000)),
                int(round(p["y_m"] * 10000)),
                int(round((p["x_m"] + p["width_m"]) * 10000)),
                int(round((p["y_m"] + p["height_m"]) * 10000)),
            )
            assert not p_box.has_positive_area_overlap(obs_box)

    def test_walkway_corridor_bisection_respected(self, engine):
        """Dedicated maintenance walkway corridor divides roof into distinct sub-arrays."""
        spec = {
            "roof_id": "GEO-WALKWAY",
            "roof_length_m": 16.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
            "obstacles": [
                {
                    "obstacle_id": "WALKWAY-SPLIT",
                    "x_m": 8.0,
                    "y_m": 0.0,
                    "width_m": 1.0,
                    "height_m": 8.0,
                    "buffer_m": 0.0,
                }
            ],
        }
        res = engine.run_dict(spec)
        assert res["feasibility_status"] == "FEASIBLE"

        west_panels = [p for p in res["placements"] if p["x_m"] + p["width_m"] <= 8.0001]
        east_panels = [p for p in res["placements"] if p["x_m"] >= 7.9999]
        corridor_encroachments = [
            p for p in res["placements"]
            if not (p["x_m"] + p["width_m"] <= 8.0001 or p["x_m"] >= 7.9999)
        ]

        assert len(west_panels) > 0
        assert len(east_panels) > 0
        assert len(corridor_encroachments) == 0
        assert len(west_panels) + len(east_panels) == res["panel_count"]


# =====================================================================
# D. Orientation Integration Scenarios
# =====================================================================

class TestOrientationIntegration:
    """Verifies orientation constraints and deterministic tie-breaking."""

    def test_portrait_only_forced(self, engine):
        """Forced portrait orientation constraint produces portrait-only layout."""
        spec = {
            "roof_id": "ORIENT-PORTRAIT-ONLY",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "allowed_orientations": "portrait",
            "panel_id": "PNL-CANADIAN-445W",
        }
        res = engine.run_dict(spec)
        assert res["selected_orientation"] == "portrait"
        for p in res["placements"]:
            assert p["orientation"] == "portrait"

    def test_landscape_only_forced(self, engine):
        """Forced landscape orientation constraint produces landscape-only layout."""
        spec = {
            "roof_id": "ORIENT-LANDSCAPE-ONLY",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "allowed_orientations": "landscape",
            "panel_id": "PNL-CANADIAN-445W",
        }
        res = engine.run_dict(spec)
        assert res["selected_orientation"] == "landscape"
        for p in res["placements"]:
            assert p["orientation"] == "landscape"

    def test_both_orientations_evaluated_with_tie_breaker(self, engine):
        """When both orientations are allowed, alternatives are preserved in output."""
        spec = {
            "roof_id": "ORIENT-BOTH-COMPARE",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "allowed_orientations": "both",
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        res = engine.run_dict(spec)
        assert "portrait" in res["alternatives_evaluated"]
        assert "landscape" in res["alternatives_evaluated"]
        assert res["alternatives_evaluated"]["portrait"]["feasible"] is True
        assert res["alternatives_evaluated"]["landscape"]["feasible"] is True


# =====================================================================
# E. Infeasible Layout Scenarios
# =====================================================================

class TestInfeasibleLayouts:
    """Verifies correct contract status when no panels can fit."""

    def test_roof_too_small_returns_infeasible_status(self, engine):
        """Roof smaller than single panel returns INFEASIBLE_ROOF_TOO_SMALL."""
        spec = {
            "roof_id": "INFEAS-TINY",
            "roof_length_m": 1.20,
            "roof_width_m": 1.20,
            "perimeter_setback_m": 0.20,
            "panel_id": "PNL-CANADIAN-445W",  # Dimensions: 2.108m x 1.048m
        }
        res = engine.run_dict(spec)
        assert res["feasibility_status"] == "INFEASIBLE_ROOF_TOO_SMALL"
        assert res["panel_count"] == 0
        assert res["installed_dc_capacity_kwp"] == 0.0
        assert res["selected_orientation"] == "none"
        assert len(res["placements"]) == 0

    def test_completely_blocked_roof_returns_infeasible_obstacle_collision(self, engine):
        """Roof completely occupied by obstacle returns INFEASIBLE_OBSTACLE_COLLISION."""
        spec = {
            "roof_id": "INFEAS-BLOCKED",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
            "obstacles": [
                {
                    "obstacle_id": "FULL-ROOF-CHILLER",
                    "x_m": 0.50,
                    "y_m": 0.50,
                    "width_m": 9.0,
                    "height_m": 7.0,
                    "buffer_m": 0.0,
                }
            ],
        }
        res = engine.run_dict(spec)
        assert res["feasibility_status"] == "INFEASIBLE_OBSTACLE_COLLISION"
        assert res["panel_count"] == 0


# =====================================================================
# F. Serialization & Contract Conformance Scenarios
# =====================================================================

class TestSerializationContract:
    """Verifies JSON schema compliance, decimal precision, and absence of leaked objects."""

    def test_json_string_output_validity_and_parsing(self, engine):
        """JSON output is valid parseable JSON conforming to required types."""
        spec = {
            "roof_id": "SERIAL-JSON-PARSE",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        json_str = engine.run_json(spec, indent=2)
        assert isinstance(json_str, str)

        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["roof_id"] == "SERIAL-JSON-PARSE"
        assert isinstance(parsed["panel_count"], int)
        assert isinstance(parsed["installed_dc_capacity_kwp"], float)
        assert isinstance(parsed["spatial_metrics"], dict)
        assert isinstance(parsed["placements"], list)
        assert isinstance(parsed["engine_metadata"], dict)

    def test_no_internal_python_objects_leak(self, engine):
        """All values in serialized dictionary are primitive types (str, int, float, list, dict)."""
        spec = {
            "roof_id": "SERIAL-PRIMITIVES",
            "roof_length_m": 8.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-JINKO-430W",
        }
        res = engine.run_dict(spec)
        # Attempt serializing to verify no dataclasses, tuples or custom objects leak
        dumped = json.dumps(res)
        assert len(dumped) > 0


# =====================================================================
# G. Determinism Scenarios
# =====================================================================

class TestWorkflowDeterminism:
    """Verifies bit-for-bit repeatability across repeated end-to-end executions."""

    def test_100_runs_produce_identical_serialized_output(self, engine):
        """100 consecutive end-to-end runs produce bit-for-bit identical JSON."""
        spec = {
            "roof_id": "DET-100-RUN",
            "roof_length_m": 14.0,
            "roof_width_m": 9.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
            "panel_id": "PNL-CANADIAN-445W",
            "obstacles": [
                {"obstacle_id": "VENT-1", "x_m": 4.0, "y_m": 2.5, "width_m": 0.5, "height_m": 0.5, "buffer_m": 0.2},
                {"obstacle_id": "VENT-2", "x_m": 9.0, "y_m": 5.0, "width_m": 0.8, "height_m": 0.6, "buffer_m": 0.1},
            ],
        }

        # Baseline execution
        base_res = engine.run_dict(spec)
        base_placements = base_res["placements"]
        base_count = base_res["panel_count"]
        base_kwp = base_res["installed_dc_capacity_kwp"]

        # 100 repeated executions
        for iteration in range(100):
            run_res = engine.run_dict(spec)
            assert run_res["panel_count"] == base_count, f"Panel count differed at iteration {iteration}"
            assert run_res["installed_dc_capacity_kwp"] == base_kwp
            assert run_res["placements"] == base_placements, f"Placements differed at iteration {iteration}"


# =====================================================================
# H. Failure Propagation & Exception Mapping
# =====================================================================

class TestFailurePropagation:
    """Verifies that upstream domain exceptions propagate cleanly."""

    def test_invalid_negative_dimension_raises_invalid_roof_specification(self, engine):
        """Negative roof dimension raises InvalidRoofSpecificationError."""
        spec = {
            "roof_id": "FAIL-NEG-DIM",
            "roof_length_m": -10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        with pytest.raises(InvalidRoofSpecificationError):
            engine.run(spec)

    def test_missing_required_roof_dimension_raises_missing_parameter(self, engine):
        """Omission of roof width raises MissingRoofParameterError."""
        spec = {
            "roof_id": "FAIL-MISSING-WIDTH",
            "roof_length_m": 10.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        with pytest.raises(MissingRoofParameterError):
            engine.run(spec)

    def test_excessive_setback_consuming_roof_raises_invalid_roof_specification(self, engine):
        """Setbacks greater than half the roof dimension consume interior space and raise error."""
        spec = {
            "roof_id": "FAIL-BIG-SETBACK",
            "roof_length_m": 4.0,
            "roof_width_m": 4.0,
            "perimeter_setback_m": 2.50,  # 2 * 2.50 = 5.0m > 4.0m
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        with pytest.raises(InvalidRoofSpecificationError) as exc_info:
            engine.run(spec)
        assert "consumes entire roof dimensions" in str(exc_info.value)

    def test_obstacle_outside_roof_raises_invalid_obstacle_specification(self, engine):
        """Obstacle coordinates exceeding gross roof dimensions raise InvalidObstacleSpecificationError."""
        spec = {
            "roof_id": "FAIL-OUT-OF-BOUNDS-OBS",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
            "obstacles": [
                {"obstacle_id": "OFF-ROOF", "x_m": 11.0, "y_m": 4.0, "width_m": 1.0, "height_m": 1.0}
            ],
        }
        with pytest.raises(InvalidObstacleSpecificationError):
            engine.run(spec)

    def test_invalid_orientation_override_raises_invalid_roof_specification(self, engine):
        """Invalid allowed_orientations string raises InvalidRoofSpecificationError."""
        spec = {
            "roof_id": "FAIL-BAD-ORIENT",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "allowed_orientations": "diagonal",
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        with pytest.raises(InvalidRoofSpecificationError):
            engine.run(spec)

    def test_unsupported_output_format_raises_value_error(self, engine):
        """Invalid output_format argument raises ValueError."""
        spec = {
            "roof_id": "FAIL-BAD-FMT",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        with pytest.raises(ValueError) as exc_info:
            engine.run(spec, output_format="xml")
        assert "Unsupported output_format" in str(exc_info.value)

    def test_final_constraint_validation_failure_prevents_feasible_status(self, engine, monkeypatch):
        """
        If a post-placement constraint violation is detected during final layout validation,
        the workflow must not produce a FEASIBLE result.
        """
        from src.roof_fit.constraint_validator import ConstraintValidator, PlacementValidationResult, ConstraintViolation

        # Simulate a synthetic constraint violation during whole-layout audit
        def mock_validate_layout(*args, **kwargs):
            return PlacementValidationResult(
                is_valid=False,
                violations=[
                    ConstraintViolation(
                        violation_type="PANEL_OVERLAP",
                        message="Simulated synthetic layout violation for failure test",
                    )
                ],
            )

        monkeypatch.setattr(ConstraintValidator, "validate_layout", mock_validate_layout)

        spec = {
            "roof_id": "FAIL-AUDIT-SIM",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "panel_id": "PNL-REC-ALPHA-420W",
        }
        res = engine.run_dict(spec)
        assert res["feasibility_status"] != "FEASIBLE"
        assert res["feasibility_status"] == "INFEASIBLE_CONSTRAINT_VIOLATION"
        assert len(res["constraint_violations"]) > 0
        assert "Simulated synthetic layout violation" in res["constraint_violations"][0]

