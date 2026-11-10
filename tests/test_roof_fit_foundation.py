"""
SolarSelect — Phase 7: Foundation Geometry and Constraint Validation Unit Tests
Comprehensive implementation integrity and regression test suite.

Covers:
- RoofSpecificationValidator
- CatalogueAdapter
- IntegerRectangle
- Quantization (Directional integer scaling, M = 10,000 units/m)
- UsableAreaGenerator
- ConstraintValidator (Zero-tolerance physical constraint checking)

Strict Test Identifier Reconciliation with docs/engineering/phase7_testing_strategy.md:
- TC-007:  Perimeter Edge Setback Enforcement (boundary containment check)
- TC-007A: Boundary Edge Touching (inner perimeter containment)
- TC-008A: Separation of Obstacle Dimensions and Buffer (unbuffered vs buffered)
- TC-010:  Inter-Panel Clear Spacing Boundary Verification (below: fail, at: pass, above: pass)
- TC-011:  Inter-Row Spacing Clearance Boundary Verification (below: fail, at: pass, above: pass)
- TC-012:  Pairwise Non-Overlap (Collision Free)
- TC-013:  Missing Catalogue Dimensions Handling (raises MissingPanelDimensionError)
- TC-014:  Invalid Roof Geometry Input (rejects negative dimensions, excessive setbacks, out-of-bounds obstacles)

Foundation-specific tests not covered by the 20 layout-level TC scenarios are prefixed with FND-*.
"""

from decimal import Decimal
import math
from pathlib import Path
import pytest

from src.roof_fit.exceptions import (
    RoofFitError,
    InvalidRoofSpecificationError,
    MissingRoofParameterError,
    InvalidObstacleSpecificationError,
    CatalogueError,
    PanelNotFoundError,
    MissingPanelDimensionError,
    InvalidPanelDimensionError,
    QuantizationError,
    ConstraintViolationError,
    BoundaryContainmentError,
    ObstacleCollisionError,
    PanelOverlapError,
    ClearanceViolationError,
)
from src.roof_fit.quantization import (
    SCALE_FACTOR,
    to_geometry_units_floor,
    to_geometry_units_ceil,
    from_geometry_units,
    quantize_roof_dimension,
    quantize_setback,
    quantize_panel_dimension_m,
    quantize_panel_dimension_mm,
    quantize_clearance,
    quantize_obstacle_buffer,
    quantize_obstacle_bounds,
)
from src.roof_fit.geometry import IntegerRectangle
from src.roof_fit.roof_validator import (
    ObstacleSpecification,
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
    ConstraintViolation,
    PlacementValidationResult,
    ConstraintValidator,
)


# =====================================================================
# 1. RoofSpecificationValidator Tests
# =====================================================================

class TestRoofSpecificationValidator:
    """Tests specification ingestion, parameter types, bounds, and obstacle sanity."""

    def test_fnd_roof_spec_valid_passes(self):
        """FND-ROOF-SPEC: Verifies nominal roof specification validation."""
        spec_dict = {
            "roof_id": "ROOF_TEST_01",
            "length": 12.0,
            "width": 8.0,
            "perimeter_setback": 0.50,
            "azimuth_deg": 180.0,
            "tilt_deg": 15.0,
            "obstacles": [
                {
                    "obstacle_id": "HVAC_01",
                    "x": 3.0,
                    "y": 4.0,
                    "width": 1.2,
                    "height": 1.0,
                    "buffer": 0.20,
                    "description": "HVAC unit",
                }
            ],
            "clamping_gap": 0.020,
            "walkway_gap": 0.050,
        }
        validated = RoofSpecificationValidator.validate(spec_dict)
        assert isinstance(validated, RoofSpecification)
        assert validated.roof_id == "ROOF_TEST_01"
        assert validated.length == 12.0
        assert validated.width == 8.0
        assert validated.perimeter_setback == 0.50
        assert len(validated.obstacles) == 1
        assert validated.obstacles[0].obstacle_id == "HVAC_01"

    @pytest.mark.parametrize("missing_field", ["roof_id", "length", "width", "perimeter_setback"])
    def test_fnd_roof_missing_required_fields_raise(self, missing_field):
        """FND-ROOF-MISSING: Omission of mandatory parameters raises MissingRoofParameterError."""
        base_dict = {
            "roof_id": "ROOF_TEST_MISSING",
            "length": 10.0,
            "width": 6.0,
            "perimeter_setback": 0.50,
        }
        del base_dict[missing_field]
        with pytest.raises(MissingRoofParameterError):
            RoofSpecificationValidator.validate(base_dict)

    @pytest.mark.parametrize("length,width", [(-10.0, 5.0), (10.0, -5.0), (0.0, 5.0), (10.0, 0.0)])
    def test_tc014_negative_or_zero_dimensions_raise(self, length, width):
        """TC-014: Non-positive gross dimensions raise InvalidRoofSpecificationError."""
        spec_dict = {
            "roof_id": "ROOF_INVALID_DIM",
            "length": length,
            "width": width,
            "perimeter_setback": 0.50,
        }
        with pytest.raises(InvalidRoofSpecificationError):
            RoofSpecificationValidator.validate(spec_dict)

    @pytest.mark.parametrize("val", [float("nan"), float("inf"), float("-inf")])
    def test_tc014_non_finite_dimensions_raise(self, val):
        """TC-014: NaN or infinite dimensions are strictly rejected."""
        spec_dict = {
            "roof_id": "ROOF_NON_FINITE",
            "length": val,
            "width": 8.0,
            "perimeter_setback": 0.50,
        }
        with pytest.raises(InvalidRoofSpecificationError):
            RoofSpecificationValidator.validate(spec_dict)

    def test_tc014_setback_exceeds_roof_dimension_raises(self):
        """TC-014: Setback that consumes the entire roof raises InvalidRoofSpecificationError."""
        spec_dict = {
            "roof_id": "ROOF_EXCESS_SETBACK",
            "length": 10.0,
            "width": 6.0,
            "perimeter_setback": 3.5,  # 2 * 3.5 = 7.0 > width (6.0)
        }
        with pytest.raises(InvalidRoofSpecificationError) as exc_info:
            RoofSpecificationValidator.validate(spec_dict)
        assert "consumes entire roof dimensions" in str(exc_info.value)

    @pytest.mark.parametrize("tilt,azimuth", [(-5.0, 180.0), (95.0, 180.0), (15.0, -10.0), (15.0, 370.0)])
    def test_fnd_roof_invalid_angles_raise(self, tilt, azimuth):
        """FND-ROOF-ANGLES: Verifies tilt and azimuth angle range boundaries."""
        spec_dict = {
            "roof_id": "ROOF_BAD_ANGLES",
            "length": 10.0,
            "width": 6.0,
            "perimeter_setback": 0.50,
            "tilt_deg": tilt,
            "azimuth_deg": azimuth,
        }
        with pytest.raises(InvalidRoofSpecificationError):
            RoofSpecificationValidator.validate(spec_dict)

    def test_tc014_obstacle_outside_roof_raises(self):
        """TC-014: Obstacle whose physical extent exceeds roof boundaries raises error."""
        spec_dict = {
            "roof_id": "ROOF_OUTSIDE_OBS",
            "length": 10.0,
            "width": 6.0,
            "perimeter_setback": 0.50,
            "obstacles": [
                {
                    "obstacle_id": "CHIMNEY_OUTSIDE",
                    "x": 9.5,
                    "y": 2.0,
                    "width": 1.0,  # 9.5 + 1.0 = 10.5 > length (10.0)
                    "height": 1.0,
                    "buffer": 0.20,
                }
            ],
        }
        with pytest.raises(InvalidObstacleSpecificationError) as exc_info:
            RoofSpecificationValidator.validate(spec_dict)
        assert "exceeds roof length" in str(exc_info.value)

    def test_fnd_roof_obstacle_negative_buffer_raises(self):
        """FND-ROOF-BUFFER: Obstacle with negative buffer raises InvalidObstacleSpecificationError."""
        spec_dict = {
            "roof_id": "ROOF_NEG_BUFFER",
            "length": 10.0,
            "width": 6.0,
            "perimeter_setback": 0.50,
            "obstacles": [
                {
                    "obstacle_id": "OBS_NEG",
                    "x": 2.0,
                    "y": 2.0,
                    "width": 1.0,
                    "height": 1.0,
                    "buffer": -0.10,
                }
            ],
        }
        with pytest.raises(InvalidObstacleSpecificationError):
            RoofSpecificationValidator.validate(spec_dict)

    def test_fnd_roof_duplicate_obstacle_id_raises(self):
        """FND-ROOF-DUP-OBS: Duplicate obstacle IDs within the same roof spec raise error."""
        spec_dict = {
            "roof_id": "ROOF_DUP_OBS",
            "length": 10.0,
            "width": 6.0,
            "perimeter_setback": 0.50,
            "obstacles": [
                {"obstacle_id": "DUP_ID", "x": 1.0, "y": 1.0, "width": 1.0, "height": 1.0},
                {"obstacle_id": "DUP_ID", "x": 4.0, "y": 2.0, "width": 1.0, "height": 1.0},
            ],
        }
        with pytest.raises(InvalidObstacleSpecificationError) as exc_info:
            RoofSpecificationValidator.validate(spec_dict)
        assert "Duplicate obstacle_id" in str(exc_info.value)


# =====================================================================
# 2. CatalogueAdapter Tests
# =====================================================================

class TestCatalogueAdapter:
    """Tests loading, caching, lookup, and dimension extraction from configs/panels_catalogue.csv."""

    @pytest.fixture(scope="class")
    def adapter(self):
        return CatalogueAdapter(Path("configs/panels_catalogue.csv"))

    def test_fnd_cat_loads_all_12_catalogue_panels(self, adapter):
        """FND-CAT-LOAD: Verifies all 12 verified catalogue panels are successfully loaded."""
        panel_ids = adapter.list_all_panel_ids()
        assert len(panel_ids) == 12
        assert "PNL-REC-ALPHA-420W" in panel_ids
        assert "PNL-LONGI-580W" in panel_ids
        assert "PNL-TRINA-VERTEX-440W" in panel_ids

    def test_fnd_cat_lookup_by_panel_id_correct_dimensions(self, adapter):
        """FND-CAT-LOOKUP: Confirms exact physical dimensions and metric conversions."""
        spec = adapter.get_panel_specs("PNL-REC-ALPHA-420W")
        assert spec.panel_id == "PNL-REC-ALPHA-420W"
        assert spec.manufacturer == "REC Group"
        assert spec.length_mm == 1730.0
        assert spec.width_mm == 1118.0
        assert spec.rated_power_wp == 420.0
        assert spec.length_m == pytest.approx(1.730, rel=1e-6)
        assert spec.width_m == pytest.approx(1.118, rel=1e-6)
        # Quantized integer dimensions: 1730 mm * 10 = 17300 units; 1118 mm * 10 = 11180 units
        assert spec.length_int == 17300
        assert spec.width_int == 11180

    def test_fnd_cat_missing_panel_id_raises(self, adapter):
        """FND-CAT-MISSING-ID: Lookup for non-existent panel raises PanelNotFoundError."""
        with pytest.raises(PanelNotFoundError):
            adapter.get_panel_specs("NONEXISTENT_PANEL_XYZ")

    def test_fnd_cat_all_12_panels_have_valid_positive_dimensions(self, adapter):
        """FND-CAT-VALID-ALL: Every catalogue panel has positive dimensions and ratings."""
        all_specs = adapter.get_all_panel_specs()
        assert len(all_specs) == 12
        for pid, spec in all_specs.items():
            assert spec.length_mm > 0.0
            assert spec.width_mm > 0.0
            assert spec.length_m > 0.0
            assert spec.width_m > 0.0
            assert spec.length_int > 0
            assert spec.width_int > 0
            assert spec.rated_power_wp > 0.0
            assert spec.area_m2 > 0.0

    def test_tc013_missing_catalogue_dimensions_raises(self, tmp_path):
        """TC-013: Catalogue record with null/NaN length or width raises MissingPanelDimensionError."""
        csv_content = (
            "panel_id,manufacturer,model,length_mm,width_mm,rated_power_wp\n"
            "PNL-NAN-DIM,TestMfr,TestModel,,1134.0,430.0\n"
        )
        test_csv = tmp_path / "test_catalogue_missing.csv"
        test_csv.write_text(csv_content)
        with pytest.raises(MissingPanelDimensionError) as exc_info:
            CatalogueAdapter(test_csv)
        assert "null length or width" in str(exc_info.value)

    def test_fnd_cat_duplicate_panel_id_raises(self, tmp_path):
        """FND-CAT-DUP-ID: Catalogue CSV with duplicate panel_id raises CatalogueError."""
        csv_content = (
            "panel_id,manufacturer,model,length_mm,width_mm,rated_power_wp\n"
            "PNL-DUP-01,TestMfr,TestModel1,1722.0,1134.0,430.0\n"
            "PNL-DUP-01,TestMfr,TestModel2,1722.0,1134.0,430.0\n"
        )
        test_csv = tmp_path / "test_catalogue_dup.csv"
        test_csv.write_text(csv_content)
        with pytest.raises(CatalogueError) as exc_info:
            CatalogueAdapter(test_csv)
        assert "Duplicate panel_id" in str(exc_info.value)

    def test_fnd_cat_invalid_catalogue_path_raises(self):
        """FND-CAT-PATH: Missing file raises CatalogueError."""
        with pytest.raises(CatalogueError):
            CatalogueAdapter(Path("nonexistent/path/catalogue.csv"))


# =====================================================================
# 3. IntegerRectangle Geometry Tests
# =====================================================================

class TestIntegerRectangle:
    """Tests discrete 2D axis-aligned integer rectangle logic."""

    def test_fnd_geo_disjoint_rectangles(self):
        """FND-GEO-DISJOINT: Completely disjoint rectangles do not overlap."""
        rect_a = IntegerRectangle(0, 0, 1000, 1000)
        rect_b = IntegerRectangle(1500, 0, 2500, 1000)
        assert not rect_a.has_positive_area_overlap(rect_b)
        assert not rect_b.has_positive_area_overlap(rect_a)
        assert rect_a.intersection(rect_b) is None

    def test_tc012_touching_edges_zero_area_overlap(self):
        """TC-012: Rectangles touching along edges share 0 area and are not considered overlapping."""
        rect_a = IntegerRectangle(0, 0, 1000, 1000)
        rect_b = IntegerRectangle(1000, 0, 2000, 1000)  # touches at x = 1000
        assert not rect_a.has_positive_area_overlap(rect_b)
        assert not rect_b.has_positive_area_overlap(rect_a)
        assert rect_a.intersection(rect_b) is None

    def test_fnd_geo_touching_corners_zero_area_overlap(self):
        """FND-GEO-CORNERS: Rectangles touching at a single corner share 0 area."""
        rect_a = IntegerRectangle(0, 0, 1000, 1000)
        rect_b = IntegerRectangle(1000, 1000, 2000, 2000)  # touches at (1000, 1000)
        assert not rect_a.has_positive_area_overlap(rect_b)
        assert not rect_b.has_positive_area_overlap(rect_a)
        assert rect_a.intersection(rect_b) is None

    def test_fnd_geo_positive_area_overlap(self):
        """FND-GEO-OVERLAP: Overlapping rectangles are detected and compute correct intersection."""
        rect_a = IntegerRectangle(0, 0, 1000, 1000)
        rect_b = IntegerRectangle(500, 500, 1500, 1500)
        assert rect_a.has_positive_area_overlap(rect_b)
        isect = rect_a.intersection(rect_b)
        assert isect is not None
        assert isect.to_tuple() == (500, 500, 1000, 1000)
        assert isect.area == 500 * 500

    def test_tc007_containment_checks(self):
        """TC-007: Completely inside, partially outside, and completely outside."""
        container = IntegerRectangle(0, 0, 5000, 5000)
        inner = IntegerRectangle(1000, 1000, 4000, 4000)
        partially_outside = IntegerRectangle(4000, 4000, 6000, 5000)
        completely_outside = IntegerRectangle(6000, 6000, 8000, 8000)

        assert container.contains(inner)
        assert not container.contains(partially_outside)
        assert not container.contains(completely_outside)

    def test_tc007a_containment_boundary_touching(self):
        """TC-007A: Rectangle touching interior boundary of container is contained."""
        container = IntegerRectangle(5000, 5000, 15000, 15000)
        touching_inner = IntegerRectangle(5000, 5000, 10000, 10000)
        assert container.contains(touching_inner)

    def test_fnd_geo_gap_calculations(self):
        """FND-GEO-GAP: Verifies horizontal and vertical gap calculation between rectangles."""
        rect_a = IntegerRectangle(0, 0, 1000, 2000)
        rect_b = IntegerRectangle(1200, 0, 2200, 2000)
        rect_c = IntegerRectangle(0, 2500, 1000, 4500)

        # Horizontal gap: 1200 - 1000 = 200
        assert rect_a.horizontal_gap_to(rect_b) == 200
        assert rect_b.horizontal_gap_to(rect_a) == 200

        # Vertical gap: 2500 - 2000 = 500
        assert rect_a.vertical_gap_to(rect_c) == 500
        assert rect_c.vertical_gap_to(rect_a) == 500

    def test_fnd_geo_diagonal_separation_limitation_documented(self):
        """
        FND-GEO-DIAG: Demonstrates that horizontal_gap_to and vertical_gap_to are 1D projections,
        not 2D Euclidean distance. For diagonally separated rectangles:
        rect_a: [0, 0, 1000, 1000]
        rect_b: [2000, 2000, 3000, 3000]
        dx = 1000, dy = 1000, but Euclidean distance is sqrt(1000^2 + 1000^2) = 1414.2 units.
        Confirms engine documents this axis-aligned clearance limitation.
        """
        rect_a = IntegerRectangle(0, 0, 1000, 1000)
        rect_b = IntegerRectangle(2000, 2000, 3000, 3000)
        assert rect_a.horizontal_gap_to(rect_b) == 1000
        assert rect_a.vertical_gap_to(rect_b) == 1000
        euclidean_dist = math.hypot(rect_a.horizontal_gap_to(rect_b), rect_a.vertical_gap_to(rect_b))
        assert euclidean_dist == pytest.approx(1414.213, rel=1e-3)

    def test_fnd_geo_rejects_boolean_coordinates(self):
        """FND-GEO-BOOL: Reject boolean types even though bool subclasses int in Python."""
        with pytest.raises(TypeError):
            IntegerRectangle(True, 0, 1000, 1000)

    def test_fnd_geo_expanded_rectangle(self):
        """FND-GEO-EXPAND: Verifies symmetric outward expansion."""
        rect = IntegerRectangle(1000, 1000, 2000, 2000)
        exp = rect.expanded(200)
        assert exp.to_tuple() == (800, 800, 2200, 2200)


# =====================================================================
# 4. Quantization Tests
# =====================================================================

class TestQuantization:
    """Tests directional conservative quantization with scale factor M = 10,000."""

    def test_fnd_qnt_scale_factor_constant(self):
        assert SCALE_FACTOR == 10_000

    def test_fnd_qnt_directional_rounding_roof_floor(self):
        """Roof dimension uses floor rounding to never overestimate boundary."""
        # 10.00009 m -> 100,000.9 units -> floor to 100,000
        val = quantize_roof_dimension(10.00009)
        assert val == 100000

    def test_fnd_qnt_directional_rounding_setback_ceil(self):
        """Perimeter setback uses ceil rounding to never encroach on setback."""
        # 0.50001 m -> 5,000.1 units -> ceil to 5,001
        val = quantize_setback(0.50001)
        assert val == 5001

    def test_fnd_qnt_directional_rounding_panel_ceil(self):
        """Panel dimensions use ceil rounding to never underestimate panel size."""
        # In metres: 1.73001 m -> 17,300.1 units -> ceil to 17,301
        val_m = quantize_panel_dimension_m(1.73001)
        assert val_m == 17301

        # In millimetres: 1730.01 mm -> 17,300.1 units -> ceil to 17,301
        val_mm = quantize_panel_dimension_mm(1730.01)
        assert val_mm == 17301

    def test_fnd_qnt_directional_rounding_clearances_ceil(self):
        """Clearance uses ceil rounding to strictly enforce spacing."""
        # 0.02001 m -> 200.1 units -> ceil to 201
        val = quantize_clearance(0.02001)
        assert val == 201

    def test_fnd_qnt_directional_rounding_obstacles_outward(self):
        """Obstacle bounds round outward: floor for min, ceil for max, ceil for buffer."""
        # x = 1.00009, y = 2.00009, w = 1.00001, h = 1.00001, buffer = 0.20001
        b = quantize_obstacle_bounds(1.00009, 2.00009, 1.00001, 1.00001, buffer=0.20001)
        assert b == (7999, 17999, 22002, 32002)

    @pytest.mark.parametrize("val", [float("nan"), float("inf"), float("-inf"), None, True, False])
    def test_fnd_qnt_non_finite_and_boolean_inputs_rejected(self, val):
        """Quantization functions strictly reject non-finite and boolean inputs."""
        with pytest.raises(QuantizationError):
            to_geometry_units_floor(val)
        with pytest.raises(QuantizationError):
            to_geometry_units_ceil(val)

    def test_fnd_qnt_unit_boundary_behaviors(self):
        """
        FND-QNT-BOUNDARIES: Tests exact unit boundary, just below, and just above:
        Exact: 1.00000 m -> 10,000 units
        Below: 0.99999 m -> floor=9999, ceil=10000
        Above: 1.00001 m -> floor=10000, ceil=10001
        """
        assert to_geometry_units_floor(1.00000) == 10000
        assert to_geometry_units_ceil(1.00000) == 10000

        assert to_geometry_units_floor(0.99999) == 9999
        assert to_geometry_units_ceil(0.99999) == 10000

        assert to_geometry_units_floor(1.00001) == 10000
        assert to_geometry_units_ceil(1.00001) == 10001

    def test_fnd_qnt_decimal_and_float_policy(self):
        """
        FND-QNT-DEC-FLOAT: Confirms string, Decimal, and float produce identical deterministic units.
        """
        val_str = "0.020"
        val_dec = Decimal("0.020")
        val_flt = 0.020

        assert to_geometry_units_ceil(val_str) == 200
        assert to_geometry_units_ceil(val_dec) == 200
        assert to_geometry_units_ceil(val_flt) == 200

    def test_fnd_qnt_very_small_positive_values(self):
        """FND-QNT-SMALL: Sub-millimeter value (0.01 mm = 0.00001 m = 0.1 integer units)."""
        small_val = 0.00001  # 0.01 mm
        assert to_geometry_units_floor(small_val) == 0
        assert to_geometry_units_ceil(small_val) == 1

    def test_fnd_qnt_deterministic_repeated_conversions(self):
        """FND-QNT-DETERM: 100 repeated conversions return bit-for-bit identical results."""
        val = 1.7224
        expected = to_geometry_units_ceil(val)
        for _ in range(100):
            assert to_geometry_units_ceil(val) == expected


# =====================================================================
# 5. UsableAreaGenerator Tests
# =====================================================================

class TestUsableAreaGenerator:
    """Tests usable envelope generation and outward obstacle expansion."""

    def test_fnd_usable_envelope_calculation(self):
        """Verifies gross minus 2 * setback per dimension."""
        spec = RoofSpecification(
            roof_id="ROOF_ENV_01",
            length=10.0,
            width=8.0,
            perimeter_setback=0.50,
        )
        res = UsableAreaGenerator.generate(spec)
        assert res.gross_rect.to_tuple() == (0, 0, 100000, 80000)
        # Setback = 0.50 m = 5,000 units
        assert res.usable_envelope.to_tuple() == (5000, 5000, 95000, 75000)
        assert res.usable_envelope.width == 90000
        assert res.usable_envelope.height == 70000

    def test_tc008a_obstacle_expansion_with_buffer(self):
        """TC-008A: Separation of obstacle physical dimensions and clearance buffer."""
        obs = ObstacleSpecification(
            obstacle_id="OBS_01",
            x=2.0,
            y=3.0,
            width=1.0,
            height=1.0,
            buffer=0.20,
        )
        spec = RoofSpecification(
            roof_id="ROOF_OBS_01",
            length=10.0,
            width=8.0,
            perimeter_setback=0.50,
            obstacles=[obs],
        )
        res = UsableAreaGenerator.generate(spec)
        assert len(res.expanded_obstacles) == 1
        exp_obs = res.expanded_obstacles[0]
        # x = 20,000, y = 30,000, w = 10,000, h = 10,000
        # buffer = 2,000
        assert exp_obs.unbuffered_rect.to_tuple() == (20000, 30000, 30000, 40000)
        assert exp_obs.expanded_rect.to_tuple() == (18000, 28000, 32000, 42000)

    def test_fnd_obs_buffer_extending_beyond_roof_unclipped(self):
        """
        FND-OBS-UNCLIPPED: Confirms obstacle buffer extending past roof canvas is NOT clipped.
        Obstacle at x=0.5, buffer=1.0 m -> expanded x_min = 5000 - 10000 = -5000.
        """
        obs = ObstacleSpecification(
            obstacle_id="OBS_CORNER",
            x=0.5,
            y=0.5,
            width=1.0,
            height=1.0,
            buffer=1.0,
        )
        spec = RoofSpecification(
            roof_id="ROOF_CORNER",
            length=10.0,
            width=8.0,
            perimeter_setback=0.50,
            obstacles=[obs],
        )
        res = UsableAreaGenerator.generate(spec)
        exp = res.expanded_obstacles[0].expanded_rect
        assert exp.x_min == -5000
        assert exp.y_min == -5000


# =====================================================================
# 6. ConstraintValidator Tests
# =====================================================================

class TestConstraintValidator:
    """Tests zero-tolerance constraint checks: boundary, collision, overlap, clearances."""

    @pytest.fixture
    def usable_env(self):
        # 10m x 8m roof with 0.5m setback -> [5000, 5000, 95000, 75000]
        return IntegerRectangle(5000, 5000, 95000, 75000)

    @pytest.fixture
    def expanded_obstacle(self):
        # Obstacle at [20000, 20000, 30000, 30000] with buffer 2000 -> [18000, 18000, 32000, 32000]
        return ExpandedObstacle(
            obstacle_id="CHIMNEY_01",
            unbuffered_rect=IntegerRectangle(20000, 20000, 30000, 30000),
            expanded_rect=IntegerRectangle(18000, 18000, 32000, 32000),
            buffer_int=2000,
            buffer_m=0.20,
        )

    def test_tc007_panel_inside_usable_envelope_passes(self, usable_env):
        """TC-007: Candidate completely inside usable envelope passes."""
        candidate = IntegerRectangle(10000, 10000, 27300, 21180)
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[])
        assert res.is_valid
        assert len(res.violations) == 0

    def test_tc007_panel_exactly_on_usable_boundary_passes(self, usable_env):
        """TC-007: Candidate placed exactly at the usable boundary edge passes."""
        # Exactly on min boundary [5000, 5000]
        candidate = IntegerRectangle(5000, 5000, 22300, 16180)
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[])
        assert res.is_valid

    def test_tc007_panel_protruding_boundary_fails(self, usable_env):
        """TC-007: Candidate protruding outside usable envelope fails with BoundaryContainmentError."""
        # Starts inside (90000) but ends at 107300 > 95000
        candidate = IntegerRectangle(90000, 10000, 107300, 21180)
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[])
        assert not res.is_valid
        assert any(v.violation_type == "BOUNDARY_EXCLUSION" for v in res.violations)

        with pytest.raises(BoundaryContainmentError):
            ConstraintValidator.check_boundary_containment(candidate, usable_env, raise_on_violation=True)

    def test_fnd_val_obstacle_collision_fails(self, usable_env, expanded_obstacle):
        """FND-VAL-OBS-COLLISION: Panel penetrating expanded obstacle exclusion zone fails."""
        candidate = IntegerRectangle(25000, 25000, 42300, 36180)
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[expanded_obstacle])
        assert not res.is_valid
        assert any(v.violation_type == "OBSTACLE_COLLISION" for v in res.violations)

        with pytest.raises(ObstacleCollisionError):
            ConstraintValidator.check_obstacle_collision(candidate, [expanded_obstacle], raise_on_violation=True)

    def test_fnd_val_panel_touching_obstacle_buffer_edge_passes(self, usable_env, expanded_obstacle):
        """FND-VAL-OBS-EDGE: Candidate touching exact outer edge of expanded obstacle (0 area) passes."""
        candidate = IntegerRectangle(32000, 18000, 49300, 29180)
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[expanded_obstacle])
        assert res.is_valid

    def test_tc012_panel_overlap_fails(self, usable_env):
        """TC-012: Candidate overlapping an existing placed panel fails with PanelOverlapError."""
        placed = [IntegerRectangle(10000, 10000, 27300, 21180)]
        candidate = IntegerRectangle(20000, 15000, 37300, 26180)  # overlaps placed
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[], placed_panels=placed)
        assert not res.is_valid
        assert any(v.violation_type == "PANEL_OVERLAP" for v in res.violations)

        with pytest.raises(PanelOverlapError):
            ConstraintValidator.check_panel_overlap(candidate, placed, raise_on_violation=True)

    def test_tc012_panel_touching_edge_non_overlap(self, usable_env):
        """TC-012: Candidate touching edge of placed panel has 0-area overlap."""
        placed = [IntegerRectangle(10000, 10000, 27300, 21180)]
        # Candidate starts exactly at placed.x_max = 27300
        candidate = IntegerRectangle(27300, 10000, 44600, 21180)
        res = ConstraintValidator.validate_candidate(candidate, usable_env, obstacles=[], placed_panels=placed)
        assert res.is_valid

    # TC-010: Inter-Panel Clear Spacing Boundary Verification (3 discrete pytest invocations)
    @pytest.mark.parametrize("actual_gap,expected_pass", [
        (199, False),  # 1 unit below minimum: FAIL
        (200, True),   # Exact match: PASS
        (201, True),   # 1 unit above minimum: PASS
    ])
    def test_tc010_inter_panel_clearance_boundary(self, actual_gap, expected_pass):
        """
        TC-010: Inter-Panel Clear Spacing Boundary Verification (3 planned pytest invocations):
        Nominal G_panel = 0.020 m (200 units). Step delta = 0.0001 m (1 unit):
        1. 0.0199 m (199 units): FAIL with ClearanceViolationError.
        2. 0.0200 m (200 units): PASS.
        3. 0.0201 m (201 units): PASS.
        """
        required_gap = 200
        panel_a = IntegerRectangle(10000, 10000, 20000, 20000)
        panel_b = IntegerRectangle(20000 + actual_gap, 10000, 30000 + actual_gap, 20000)

        viol = ConstraintValidator.check_inter_panel_gap(panel_a, panel_b, required_gap)
        if expected_pass:
            assert viol is None
        else:
            assert viol is not None
            assert viol.violation_type == "CLAMP_GAP_VIOLATION"
            assert viol.details["deficit_units"] == required_gap - actual_gap
            with pytest.raises(ClearanceViolationError):
                ConstraintValidator.check_inter_panel_gap(panel_a, panel_b, required_gap, raise_on_violation=True)

    # TC-011: Inter-Row Spacing Clearance Boundary Verification (3 discrete pytest invocations)
    @pytest.mark.parametrize("actual_gap,expected_pass", [
        (499, False),  # 1 unit below minimum: FAIL
        (500, True),   # Exact match: PASS
        (501, True),   # 1 unit above minimum: PASS
    ])
    def test_tc011_inter_row_clearance_boundary(self, actual_gap, expected_pass):
        """
        TC-011: Inter-Row Spacing Clearance Boundary Verification (3 planned pytest invocations):
        Nominal G_row = 0.050 m (500 units). Step delta = 0.0001 m (1 unit):
        1. 0.0499 m (499 units): FAIL with ClearanceViolationError.
        2. 0.0500 m (500 units): PASS.
        3. 0.0501 m (501 units): PASS.
        """
        required_gap = 500
        row_lower = IntegerRectangle(10000, 10000, 20000, 20000)
        row_upper = IntegerRectangle(10000, 20000 + actual_gap, 20000, 30000 + actual_gap)

        viol = ConstraintValidator.check_inter_row_gap(row_lower, row_upper, required_gap)
        if expected_pass:
            assert viol is None
        else:
            assert viol is not None
            assert viol.violation_type == "ROW_GAP_VIOLATION"
            assert viol.details["deficit_units"] == required_gap - actual_gap
            with pytest.raises(ClearanceViolationError):
                ConstraintValidator.check_inter_row_gap(row_lower, row_upper, required_gap, raise_on_violation=True)

    def test_fnd_val_multiple_simultaneous_violations_accumulated(self, usable_env, expanded_obstacle):
        """
        FND-VAL-MULTIPLE: Confirms candidate with multiple simultaneous violations
        (boundary exclusion + obstacle collision + panel overlap) produces an aggregate result
        reporting all distinct violations rather than stopping at the first.
        """
        placed = [IntegerRectangle(80000, 60000, 100000, 80000)]
        # Place obstacle in the corner
        obs = ExpandedObstacle(
            obstacle_id="OBS_CORNER",
            unbuffered_rect=IntegerRectangle(85000, 65000, 95000, 75000),
            expanded_rect=IntegerRectangle(85000, 65000, 95000, 75000),
            buffer_int=0,
            buffer_m=0.0,
        )
        # Candidate at [82000, 62000, 98000, 78000]:
        # 1. Protrudes past usable_env (max x=98000 > 95000, max y=78000 > 75000) -> BOUNDARY_EXCLUSION
        # 2. Overlaps placed panel [80000, 60000, 100000, 80000] -> PANEL_OVERLAP
        # 3. Collides with obstacle [85000, 65000, 95000, 75000] -> OBSTACLE_COLLISION
        candidate = IntegerRectangle(82000, 62000, 98000, 78000)

        res = ConstraintValidator.validate_candidate(
            candidate=candidate,
            usable_envelope=usable_env,
            obstacles=[obs],
            placed_panels=placed,
            raise_on_violation=False,
        )
        assert not res.is_valid
        assert len(res.violations) == 3
        v_types = {v.violation_type for v in res.violations}
        assert v_types == {"BOUNDARY_EXCLUSION", "OBSTACLE_COLLISION", "PANEL_OVERLAP"}
