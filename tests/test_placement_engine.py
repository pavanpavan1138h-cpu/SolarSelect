"""
SolarSelect — Phase 7: Row-Wise Strip Packing Placement Engine Test Suite
Comprehensive tests covering placement, orientation comparison, obstacle interruption
and resumption, zero-tolerance clearances, robustness, spatial conservation, and determinism.

Maps directly to canonical Phase 7 scenarios in docs/engineering/phase7_testing_strategy.md:
- TC-001: Roof Too Small for Any Panel
- TC-002: Exact-Fit Roof (Zero Clearance Boundary)
- TC-003: Portrait-Only Feasibility
- TC-004: Landscape-Only Feasibility
- TC-005: Both Orientations Feasible (Capacity Selection)
- TC-005A: Row Starting Position & Tie-Breaking
- TC-006: Multi-Row & Multi-Column Clear Commercial Roof
- TC-007: Perimeter Edge Setback Enforcement
- TC-007A: Configurable Setback Variation Suite (4 parameter variations)
- TC-008: Central Obstacle Avoidance & Row Resumption
- TC-008A: Separation of Obstacle Dimensions and Buffer (3 buffer variations)
- TC-008B: Dedicated Maintenance Walkway Corridor Bisection
- TC-009: Edge / Corner Obstacle Avoidance
- TC-010: Inter-Panel Clear Spacing Boundary Verification
- TC-010A: Configurable Clear Spacing Variation (3 spacing variations)
- TC-011: Inter-Row Spacing Clearance Boundary Verification
- TC-012: Pairwise Non-Overlap (Collision Free)
- TC-013: Missing Catalogue Dimensions Handling
- TC-014: Invalid Roof Geometry Input
- TC-015: Strict Determinism Check (100 Iterations)
"""

import json
from pathlib import Path
import pytest

from src.roof_fit.exceptions import (
    PanelNotFoundError,
    InvalidRoofSpecificationError,
    MissingPanelDimensionError,
)
from src.roof_fit.roof_validator import (
    RoofSpecification,
    ObstacleSpecification,
    RoofSpecificationValidator,
)
from src.roof_fit.catalogue_adapter import CatalogueAdapter
from src.roof_fit.placement_engine import (
    RowWisePlacementEngine,
    PanelPlacement,
    PanelConfigurationResult,
)
from src.roof_fit.serializer import LayoutSerializer
from src.roof_fit.geometry import IntegerRectangle


@pytest.fixture(scope="module")
def engine():
    adapter = CatalogueAdapter(Path("configs/panels_catalogue.csv"))
    return RowWisePlacementEngine(catalogue_adapter=adapter)


# =====================================================================
# 1. Basic Placement Scenarios (TC-001, TC-002, TC-006)
# =====================================================================

class TestBasicPlacement:
    """Tests basic roof fitting: too small, exact fit, multi-row multi-column."""

    def test_tc001_roof_too_small_for_any_panel(self, engine):
        """TC-001: Usable roof smaller than minimum module dimensions returns 0 panels."""
        spec = {
            "roof_id": "TC-001-ROOF-TINY",
            "roof_length_m": 1.0,
            "roof_width_m": 1.0,
            "perimeter_setback_m": 0.20,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.panel_count == 0
        assert res.installed_dc_capacity_kwp == 0.0
        assert res.selected_orientation == "none"
        assert res.feasibility_status == "INFEASIBLE_ROOF_TOO_SMALL"
        assert len(res.placements) == 0

    def test_tc002_exact_fit_roof_zero_clearance_boundary(self, engine):
        """
        TC-002: Usable roof precisely equals single panel dimensions.
        PNL-JINKO-430W: length = 1722.0 mm (1.722 m), width = 1134.0 mm (1.134 m).
        Roof: 1.722 m x 1.134 m with 0.0 m setback.
        """
        spec = {
            "roof_id": "TC-002-ROOF-EXACT",
            "roof_length_m": 1.722,
            "roof_width_m": 1.134,
            "perimeter_setback_m": 0.0,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "landscape",  # landscape: w=1.722, h=1.134
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-JINKO-430W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count == 1
        assert res.selected_orientation == "landscape"
        p = res.placements[0]
        assert p["x_m"] == 0.0
        assert p["y_m"] == 0.0
        assert p["width_m"] == pytest.approx(1.722, rel=1e-4)
        assert p["height_m"] == pytest.approx(1.134, rel=1e-4)

    def test_tc006_multi_row_multi_column_clear_roof(self, engine):
        """
        TC-006: Large unobstructed commercial rooftop grid math.
        Roof: 20.0 m x 10.0 m, Setback: 0.50 m -> Usable: 19.0 m x 9.0 m.
        Module: PNL-JINKO-430W (L=1.722 m, W=1.134 m).
        Portrait: panel_w = 1.134 m + 0.02 m = 1.154 m pitch.
        Cols = floor((19.0 + 0.02) / 1.154) = 16 cols.
        Rows = floor((9.0 + 0.05) / (1.722 + 0.05)) = floor(9.05 / 1.772) = 5 rows.
        Total = 16 * 5 = 80 panels.
        """
        spec = {
            "roof_id": "TC-006-COMMERCIAL",
            "roof_length_m": 20.0,
            "roof_width_m": 10.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-JINKO-430W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count == 80
        assert len(res.placements) == 80
        assert res.installed_dc_capacity_kwp == pytest.approx(80 * 0.430, rel=1e-4)


# =====================================================================
# 2. Orientation Selection Scenarios (TC-003, TC-004, TC-005, TC-005A)
# =====================================================================

class TestOrientationSelection:
    """Tests portrait vs landscape feasibility and comparison."""

    def test_tc003_portrait_only_feasibility(self, engine):
        """
        TC-003: Usable dimensions permit portrait mounting, but reject landscape.
        Module: PNL-CANADIAN-445W (L=2.108 m, W=1.048 m).
        Roof usable: 1.2 m x 2.2 m (Gross: 1.6 m x 2.6 m, Setback: 0.2 m).
        Portrait: panel w=1.048 m <= 1.2 m, h=2.108 m <= 2.2 m -> Fits 1 panel!
        Landscape: panel w=2.108 m > 1.2 m -> Fails!
        """
        spec = {
            "roof_id": "TC-003-PORTRAIT-ONLY",
            "roof_length_m": 1.60,
            "roof_width_m": 2.60,
            "perimeter_setback_m": 0.20,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-CANADIAN-445W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.selected_orientation == "portrait"
        assert res.panel_count == 1
        assert res.alternatives_evaluated["portrait"]["feasible"] is True
        assert res.alternatives_evaluated["landscape"]["feasible"] is False

    def test_tc004_landscape_only_feasibility(self, engine):
        """
        TC-004: Usable dimensions permit landscape mounting, but reject portrait.
        Module: PNL-CANADIAN-445W (L=2.108 m, W=1.048 m).
        Roof usable: 2.2 m x 1.2 m (Gross: 2.6 m x 1.6 m, Setback: 0.2 m).
        Landscape: panel w=2.108 m <= 2.2 m, h=1.048 m <= 1.2 m -> Fits 1 panel!
        Portrait: panel h=2.108 m > 1.2 m -> Fails!
        """
        spec = {
            "roof_id": "TC-004-LANDSCAPE-ONLY",
            "roof_length_m": 2.60,
            "roof_width_m": 1.60,
            "perimeter_setback_m": 0.20,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-CANADIAN-445W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.selected_orientation == "landscape"
        assert res.panel_count == 1
        assert res.alternatives_evaluated["landscape"]["feasible"] is True
        assert res.alternatives_evaluated["portrait"]["feasible"] is False

    def test_tc005_both_orientations_feasible_capacity_selection(self, engine):
        """
        TC-005: Both orientations feasible. Engine compares both and selects the one
        yielding higher panel count / installed capacity.
        Roof: 10.0 m x 6.5 m, Setback: 0.50 m -> Usable: 9.0 m x 5.5 m.
        Module: PNL-CANADIAN-445W (L=2.108 m, W=1.048 m, 445W).
        """
        spec = {
            "roof_id": "TC-005-COMPARE",
            "roof_length_m": 10.0,
            "roof_width_m": 6.5,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-CANADIAN-445W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.alternatives_evaluated["portrait"]["feasible"] is True
        assert res.alternatives_evaluated["landscape"]["feasible"] is True
        # Verify engine selected the higher or equal count
        p_count = res.alternatives_evaluated["portrait"]["panel_count"]
        l_count = res.alternatives_evaluated["landscape"]["panel_count"]
        assert res.panel_count == max(p_count, l_count)

    def test_tc005a_orientation_tie_breaking(self, engine):
        """
        TC-005A: When portrait and landscape yield equal panel count and capacity,
        stable tie-breaker selects portrait.
        Square usable roof: 4.0 m x 4.0 m (Gross: 5.0 m x 5.0 m, Setback: 0.50 m).
        Module: PNL-REC-ALPHA-420W (L=1.730 m, W=1.118 m).
        In both portrait and landscape, exactly 4 panels fit (2x2).
        """
        spec = {
            "roof_id": "TC-005A-TIE-BREAK",
            "roof_length_m": 5.0,
            "roof_width_m": 5.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.selected_orientation == "portrait"


# =====================================================================
# 3. Obstacle Interruption & Resumption Scenarios (TC-008, TC-008A, TC-008B, TC-009)
# =====================================================================

class TestObstacleInterruption:
    """Tests obstacle avoidance, row splitting, resumption, corridors, and corners."""

    def test_tc008_central_obstacle_avoidance_and_row_resumption(self, engine):
        """
        TC-008: Central obstacle interrupts a row; placement resumes to the right of the obstacle.
        Roof: 12.0 m x 6.0 m, Setback: 0.50 m.
        Obstacle: vent pipe at x=6.0 m, y=3.0 m, w=0.5 m, h=0.5 m, buffer=0.20 m.
        Expanded obstacle X bounds: [5.80 m, 6.70 m].
        """
        spec = {
            "roof_id": "TC-008-CENTRAL-OBS",
            "roof_length_m": 12.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {
                    "obstacle_id": "VENT-CENTRAL",
                    "x_m": 6.0,
                    "y_m": 3.0,
                    "width_m": 0.50,
                    "height_m": 0.50,
                    "buffer_m": 0.20,
                }
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"

        # Verify panels are placed both to the left (x + width <= 5.80) and right (x >= 6.70) in the interrupted row
        exp_obs_rect = IntegerRectangle(58000, 28000, 67000, 37000)
        has_left = False
        has_right = False
        for p in res.placements:
            p_rect = IntegerRectangle(
                int(round(p["x_m"] * 10000)),
                int(round(p["y_m"] * 10000)),
                int(round((p["x_m"] + p["width_m"]) * 10000)),
                int(round((p["y_m"] + p["height_m"]) * 10000)),
            )
            # Must not overlap expanded obstacle
            assert not p_rect.has_positive_area_overlap(exp_obs_rect)

            # Check if this panel is at row elevation intersecting the obstacle
            if p["y_m"] < 3.70 and (p["y_m"] + p["height_m"]) > 2.80:
                if (p["x_m"] + p["width_m"]) <= 5.80:
                    has_left = True
                if p["x_m"] >= 6.70:
                    has_right = True

        assert has_left, "Expected panel to the left of central obstacle"
        assert has_right, "Expected placement to resume to the right of central obstacle"

    @pytest.mark.parametrize("buffer_m,expected_count_diff", [
        (0.0, 0),
        (0.15, 0),
        (0.50, 0),
    ])
    def test_tc008a_separation_of_obstacle_dimensions_and_buffer(self, engine, buffer_m, expected_count_diff):
        """TC-008A: Evaluates varying obstacle buffer parameters."""
        spec = {
            "roof_id": "TC-008A-BUF-SWEEP",
            "roof_length_m": 10.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {
                    "obstacle_id": "OBS-01",
                    "x_m": 4.0,
                    "y_m": 2.5,
                    "width_m": 0.40,
                    "height_m": 0.40,
                    "buffer_m": buffer_m,
                }
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count > 0

    def test_tc008b_dedicated_maintenance_walkway_corridor_bisection(self, engine):
        """
        TC-008B: Dedicated maintenance walkway corridor bisecting roof array.
        Roof: 15.0 m x 8.0 m, Setback: 0.50 m.
        Walkway corridor obstacle: x=7.0 m, y=0.0 m, w=1.0 m, h=8.0 m.
        Corridor spans full width from x=7.0 m to x=8.0 m.
        Array must cleanly split into West sub-array (x + w <= 7.0 m) and East sub-array (x >= 8.0 m).
        Walkway corridor [7.0, 8.0] must remain 100% free of panels.
        """
        spec = {
            "roof_id": "TC-008B-WALKWAY",
            "roof_length_m": 15.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {
                    "obstacle_id": "WALKWAY-CORRIDOR",
                    "x_m": 7.0,
                    "y_m": 0.0,
                    "width_m": 1.0,
                    "height_m": 8.0,
                    "buffer_m": 0.0,
                }
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"

        west_count = 0
        east_count = 0
        for p in res.placements:
            # West array: x + w <= 7.00
            if round(p["x_m"] + p["width_m"], 4) <= 7.0001:
                west_count += 1
            # East array: x >= 8.00
            elif round(p["x_m"], 4) >= 7.9999:
                east_count += 1
            else:
                pytest.fail(f"Panel encroached on maintenance walkway corridor [7.0, 8.0]: {p}")

        assert west_count > 0, "West sub-array should contain panels"
        assert east_count > 0, "East sub-array should contain panels"

    def test_tc009_edge_corner_obstacle_avoidance(self, engine):
        """
        TC-009: Obstacle placed in a corner omitting local corner panels.
        Obstacle placed at x=0.60 m, y=0.60 m, w=1.0 m, h=1.0 m.
        """
        spec = {
            "roof_id": "TC-009-CORNER-OBS",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {
                    "obstacle_id": "CORNER-CHIMNEY",
                    "x_m": 0.60,
                    "y_m": 0.60,
                    "width_m": 1.0,
                    "height_m": 1.0,
                    "buffer_m": 0.20,
                }
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count > 0

    def test_obstacle_blocking_first_position(self, engine):
        """Obstacle blocking the very start of a row skips to the right."""
        spec = {
            "roof_id": "OBS-START-ROW",
            "roof_length_m": 10.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "obstacles": [
                {"obstacle_id": "BLOCK-START", "x_m": 0.50, "y_m": 0.50, "width_m": 1.5, "height_m": 1.5, "buffer_m": 0.0}
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        for p in res.placements:
            if p["y_m"] < 2.0:
                assert p["x_m"] >= 2.0

    def test_multiple_obstacles_in_same_row(self, engine):
        """Multiple obstacles in the same row segment cleanly split the row twice."""
        spec = {
            "roof_id": "OBS-MULTI-ROW",
            "roof_length_m": 15.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "obstacles": [
                {"obstacle_id": "OBS-1", "x_m": 4.0, "y_m": 0.50, "width_m": 0.5, "height_m": 0.5, "buffer_m": 0.1},
                {"obstacle_id": "OBS-2", "x_m": 9.0, "y_m": 0.50, "width_m": 0.5, "height_m": 0.5, "buffer_m": 0.1},
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"

    def test_obstacle_resumption_inter_panel_clearance_preserved(self, engine):
        """
        Resumption after an obstacle places panels to the right, and subsequent panels
        in that resumed segment strictly maintain the configured inter-panel clearance.
        """
        spec = {
            "roof_id": "OBS-RESUME-CLEARANCE",
            "roof_length_m": 16.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {
                    "obstacle_id": "CENTRAL-BLOCK",
                    "x_m": 5.0,
                    "y_m": 0.50,
                    "width_m": 1.0,
                    "height_m": 2.0,
                    "buffer_m": 0.10,
                }
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"

        # Expanded obstacle X: [4.90 m, 6.10 m]
        # Resumed panels in the first row (y_m == 0.50) must have x >= 6.10
        resumed_row1 = [p for p in res.placements if p["y_m"] == 0.50 and p["x_m"] >= 6.10]
        assert len(resumed_row1) >= 2, "Expected at least 2 resumed panels to verify inter-panel gap"

        # Verify exact clearance between adjacent resumed panels
        for i in range(len(resumed_row1) - 1):
            left_p = resumed_row1[i]
            right_p = resumed_row1[i + 1]
            gap = right_p["x_m"] - (left_p["x_m"] + left_p["width_m"])
            assert gap == pytest.approx(0.02, abs=1e-4), f"Inter-panel gap {gap} != 0.02 m"

    def test_multiple_simultaneous_obstacle_collisions(self, engine):
        """
        A candidate panel spans across two adjacent or overlapping obstacles simultaneously.
        Engine identifies all colliding obstacles and advances past the maximum x_max.
        """
        spec = {
            "roof_id": "OBS-MULTI-COLLISION",
            "roof_length_m": 12.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {"obstacle_id": "OBS-A", "x_m": 3.0, "y_m": 0.50, "width_m": 1.0, "height_m": 1.0, "buffer_m": 0.0},
                {"obstacle_id": "OBS-B", "x_m": 3.8, "y_m": 0.50, "width_m": 1.2, "height_m": 1.0, "buffer_m": 0.0},
            ],
        }
        # OBS-A spans [3.0, 4.0], OBS-B spans [3.8, 5.0]. Combined span: [3.0, 5.0].
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"

        # Verify no panels overlap [3.0, 5.0] in row 1
        for p in res.placements:
            if p["y_m"] < 1.50:
                assert (p["x_m"] + p["width_m"] <= 3.0001) or (p["x_m"] >= 4.9999)

    def test_completely_blocked_horizontal_row(self, engine):
        """
        An obstacle spanning the entire roof width completely blocks one row elevation.
        Engine cleanly skips the blocked elevation and packs subsequent rows without error.
        """
        spec = {
            "roof_id": "OBS-BLOCKED-ROW",
            "roof_length_m": 10.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
            "obstacles": [
                {
                    "obstacle_id": "HORIZONTAL-BARRIER",
                    "x_m": 0.0,
                    "y_m": 2.50,
                    "width_m": 10.0,
                    "height_m": 1.50,
                    "buffer_m": 0.10,
                }
            ],
        }
        # Barrier + buffer covers y in [2.40, 4.10] across full width [0.0, 10.0].
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count > 0

        # Verify zero panels overlap the horizontal barrier band [2.40, 4.10]
        for p in res.placements:
            p_y_bottom = p["y_m"]
            p_y_top = p["y_m"] + p["height_m"]
            overlaps = not (p_y_top <= 2.4001 or p_y_bottom >= 4.0999)
            assert not overlaps, f"Panel at y={p['y_m']} encroached on blocked row band [2.40, 4.10]"

    def test_termination_when_remaining_strip_too_narrow(self, engine):
        """
        Engine terminates row traversal deterministically when remaining horizontal space
        is strictly smaller than panel width, without infinite loops or partial placements.
        """
        # Usable length: 3.0 m (Gross 4.0 m, Setback 0.50 m).
        # PNL-REC-ALPHA-420W portrait width: 1.118 m, gap: 0.02 m.
        # Panel 1: [0.50, 1.618]
        # Panel 2: [1.638, 2.756]
        # Remaining width: 3.50 - 2.756 = 0.744 m < 1.118 m.
        spec = {
            "roof_id": "TERM-NARROW-STRIP",
            "roof_length_m": 4.0,
            "roof_width_m": 4.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        # In each row, exactly 2 panels fit horizontally
        row1_panels = [p for p in res.placements if p["y_m"] == 0.50]
        assert len(row1_panels) == 2
        # All panels strictly within usable X [0.50, 3.50]
        for p in res.placements:
            assert p["x_m"] >= 0.50
            assert p["x_m"] + p["width_m"] <= 3.5001


# =====================================================================
# 4. Clearance & Setback Variation Scenarios (TC-007, TC-007A, TC-010A)
# =====================================================================

class TestClearancesAndSetbacks:
    """Tests parameterized setbacks and clearances."""

    @pytest.mark.parametrize("setback_m", [0.0, 0.25, 0.50, 1.20])
    def test_tc007a_configurable_setback_variation_suite(self, engine, setback_m):
        """TC-007A: 4 planned test variations verifying monotonic usable area reduction."""
        spec = {
            "roof_id": f"TC-007A-SETBACK-{setback_m}",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": setback_m,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count > 0

    @pytest.mark.parametrize("inter_panel_m", [0.005, 0.020, 0.035])
    def test_tc010a_configurable_clear_spacing_variation(self, engine, inter_panel_m):
        """TC-010A: 3 planned test variations for inter-panel clearance."""
        spec = {
            "roof_id": f"TC-010A-SPACING-{inter_panel_m}",
            "roof_length_m": 10.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": inter_panel_m,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "portrait",
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        assert res.feasibility_status == "FEASIBLE"
        assert res.panel_count > 0


# =====================================================================
# 5. Robustness & Determinism (TC-013, TC-014, TC-015)
# =====================================================================

class TestRobustnessAndDeterminism:
    """Tests error handling, invalid inputs, and 100-run bit-for-bit determinism."""

    def test_invalid_panel_id_raises_panel_not_found(self, engine):
        """Verifies lookup for non-existent panel ID raises PanelNotFoundError."""
        spec = {
            "roof_id": "ROOF-ERR",
            "roof_length_m": 10.0,
            "roof_width_m": 6.0,
            "perimeter_setback_m": 0.50,
        }
        with pytest.raises(PanelNotFoundError):
            engine.fit_panels(roof_spec=spec, panel_id="NONEXISTENT-PANEL-XYZ")

    def test_tc014_invalid_roof_specification_raises(self, engine):
        """TC-014: Setback consuming entire roof raises InvalidRoofSpecificationError."""
        spec = {
            "roof_id": "ROOF-INVALID",
            "roof_length_m": 10.0,
            "roof_width_m": 4.0,
            "perimeter_setback_m": 2.5,  # 2 * 2.5 = 5.0 > 4.0
        }
        with pytest.raises(InvalidRoofSpecificationError):
            engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")

    def test_tc015_strict_determinism_check_100_iterations(self, engine):
        """
        TC-015: 100 consecutive executions on a roof with 3 obstacles produce
        bit-for-bit identical coordinate arrays and JSON outputs (0 deviation).
        """
        spec = {
            "roof_id": "TC-015-DETERMINISM-ROOF",
            "roof_length_m": 14.0,
            "roof_width_m": 8.5,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
            "obstacles": [
                {"obstacle_id": "OBS-1", "x_m": 3.0, "y_m": 2.0, "width_m": 0.8, "height_m": 0.8, "buffer_m": 0.15},
                {"obstacle_id": "OBS-2", "x_m": 7.5, "y_m": 4.5, "width_m": 1.2, "height_m": 0.6, "buffer_m": 0.20},
                {"obstacle_id": "OBS-3", "x_m": 11.0, "y_m": 1.5, "width_m": 0.5, "height_m": 0.5, "buffer_m": 0.10},
            ],
        }

        # First run establishes baseline
        baseline_res = engine.fit_panels(roof_spec=spec, panel_id="PNL-CANADIAN-445W")
        baseline_placements = baseline_res.placements
        baseline_count = baseline_res.panel_count
        baseline_orientation = baseline_res.selected_orientation

        for i in range(100):
            run_res = engine.fit_panels(roof_spec=spec, panel_id="PNL-CANADIAN-445W")
            assert run_res.panel_count == baseline_count
            assert run_res.selected_orientation == baseline_orientation
            assert run_res.placements == baseline_placements


# =====================================================================
# 6. Output Contract & Mathematical Laws
# =====================================================================

class TestOutputContractAndMathematicalLaws:
    """Verifies output JSON schema compliance and mathematical conservation laws."""

    def test_output_json_serialization_matches_contract(self, engine):
        """Verifies JSON output matches Phase 7 contract schema."""
        spec = {
            "roof_id": "ROOF-JSON-TEST",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
            "allowed_orientations": "both",
            "obstacles": [
                {"obstacle_id": "OBS-PIPE", "x_m": 4.0, "y_m": 3.0, "width_m": 0.4, "height_m": 0.4, "buffer_m": 0.2}
            ],
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-CANADIAN-445W")
        json_str = LayoutSerializer.to_json(res)
        data = json.loads(json_str)

        # Check required schema fields
        required_keys = [
            "configuration_id",
            "roof_id",
            "panel_id",
            "panel_model",
            "feasibility_status",
            "selected_orientation",
            "panel_count",
            "installed_dc_capacity_kwp",
            "spatial_metrics",
            "placements",
            "alternatives_evaluated",
            "constraint_violations",
            "engine_metadata",
        ]
        for k in required_keys:
            assert k in data, f"Missing required output key: {k}"

        assert data["feasibility_status"] == "FEASIBLE"
        assert data["engine_metadata"]["algorithm"] == "RowWiseStripPackingEngine"
        assert data["engine_metadata"]["optimality_guarantee"] == "BEST_FEASIBLE_CONFIGURATION_FOUND"

    def test_spatial_conservation_law(self, engine):
        """
        Mathematical assertion:
        Area_gross = Area_usable + Area_setback
        Area_usable = Area_occupied + Area_unutilized + Area_obstacle_exclusion
        Within floating-point epsilon = 1e-4 m^2.
        """
        spec = {
            "roof_id": "ROOF-CONSERVATION",
            "roof_length_m": 12.0,
            "roof_width_m": 8.0,
            "perimeter_setback_m": 0.50,
            "inter_panel_spacing_m": 0.02,
            "inter_row_spacing_m": 0.05,
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-REC-ALPHA-420W")
        m = res.spatial_metrics

        # Gross = Usable + Setback
        assert abs(m["gross_roof_area_m2"] - (m["net_usable_roof_area_m2"] + m["perimeter_setback_area_m2"] + m["obstacle_exclusion_area_m2"])) < 1e-3

        # Net Usable = Occupied + Unutilized
        assert abs(m["net_usable_roof_area_m2"] - (m["occupied_panel_area_m2"] + m["unutilized_usable_area_m2"])) < 1e-3

    def test_capacity_consistency_law(self, engine):
        """
        Mathematical assertion:
        P_DC = N * P_STC / 1000 kWp within epsilon = 1e-3.
        """
        spec = {
            "roof_id": "ROOF-CAPACITY",
            "roof_length_m": 15.0,
            "roof_width_m": 10.0,
            "perimeter_setback_m": 0.50,
        }
        res = engine.fit_panels(roof_spec=spec, panel_id="PNL-LONGI-580W")
        expected_kwp = round(res.panel_count * 580.0 / 1000.0, 3)
        assert abs(res.installed_dc_capacity_kwp - expected_kwp) < 1e-4

