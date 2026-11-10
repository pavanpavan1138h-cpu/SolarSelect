# SolarSelect — Phase 7: Row-Wise Strip Packing Placement Engine Implementation Report

## 1. Objective and Scope

This milestone report documents the implementation, integration, and verification of the **Row-Wise Strip Packing Placement Engine with Obstacle Interruption** for **Phase 7 — Roof-Fit and Panel Configuration Engine** of the SolarSelect project.

- **Primary Goal:** Provide a deterministic, physically constrained 2D heuristic placement engine that packs real commercial solar panels onto rooftop envelopes subject to setbacks, mounting orientations, inter-panel clearances, inter-row clearances, and rooftop obstacle exclusion zones.
- **Scope Boundary:** Implements the approved **Row-Wise Strip Packing with Obstacle Interruption** algorithm. Does not implement alternative algorithms (MaxRects deferred), Phase 8 yield scaling/economics, or structural/electrical safety certifications.
- **Phase 7 Status:** **`PHASE 7 — ROW-WISE PLACEMENT ENGINE IMPLEMENTED (IN PROGRESS)`**

---

## 2. Architecture and Component Integration

The placement engine integrates with the foundational geometry, validation, and catalogue layers developed and audited in Prompts 2 and 2.1:

```
src/roof_fit/
├── __init__.py               # Public package namespace exports
├── exceptions.py             # Actionable domain exceptions (e.g. PanelNotFoundError)
├── quantization.py           # Directional integer quantization (M = 10,000 units/m)
├── geometry.py               # IntegerRectangle, closed-interval containment, positive-area overlap
├── roof_validator.py         # RoofSpecification, ObstacleSpecification, parameter validation
├── catalogue_adapter.py      # Read-only adapter for configs/panels_catalogue.csv
├── usable_area.py            # Discrete usable envelope and outward-expanded obstacle zones
├── constraint_validator.py   # Boundary, collision, overlap, and clearance checking (validate_layout)
├── placement_engine.py       # RowWisePlacementEngine, PanelPlacement, PanelConfigurationResult
└── serializer.py             # LayoutSerializer (dict and JSON contract formatting)
```

### Component Interaction Flow

1. **Specification Ingestion:** [`RoofSpecificationValidator.validate()`](../../src/roof_fit/roof_validator.py) ingests raw roof dimensions, setbacks, clearances, allowed orientations, and obstacles, validating finite numeric values, orientation enums, and gross roof containment.
2. **Hardware Retrieval:** [`CatalogueAdapter.get_panel_specs()`](../../src/roof_fit/catalogue_adapter.py) extracts exact physical dimensions (`length_mm`, `width_mm`, `thickness_mm`) and rated capacity (`rated_power_wp`) from [`configs/panels_catalogue.csv`](../../configs/panels_catalogue.csv).
3. **Envelope & Obstacle Generation:** [`UsableAreaGenerator.generate()`](../../src/roof_fit/usable_area.py) calculates the interior usable envelope and expands obstacle keep-out rectangles outward in integer geometry units.
4. **Row-Wise Packing:** [`RowWisePlacementEngine.fit_panels()`](../../src/roof_fit/placement_engine.py) evaluates supported orientations (portrait, landscape) using row-wise strip packing with obstacle interruption and resumption.
5. **Constraint Audit:** Every placed panel candidate is checked via [`ConstraintValidator.validate_candidate()`](../../src/roof_fit/constraint_validator.py), and the complete layout is audited via [`ConstraintValidator.validate_layout()`](../../src/roof_fit/constraint_validator.py).
6. **Result Packaging:** Results are structured into `PanelConfigurationResult` and formatted by [`LayoutSerializer`](../../src/roof_fit/serializer.py).

---

## 3. Placement Algorithm & Coordinate Sequence

All geometric operations occur strictly in the discrete integer coordinate space $\mathbb{Z}_{\ge 0}^2$ with scale factor:

$$M = 10{,}000\text{ units per metre}\quad (1\text{ integer unit} = 0.0001\text{ m} = 0.1\text{ mm})$$

### Coordinate System & Origin Convention
- **Origin $(0,0)$:** South-West (bottom-left) corner of the gross roof canvas.
- **X-Axis ($+X$):** Horizontal dimension (eave-parallel / mounting rails).
- **Y-Axis ($+Y$):** Vertical dimension (ridge-to-gutter / across rows).
- **Usable Interior Envelope:** $[S_{\text{int}}, S_{\text{int}}, L_{\text{int}} - S_{\text{int}}, W_{\text{int}} - S_{\text{int}}]$.

### Strip Packing Execution Sequence
For a selected orientation with panel width $W_{\text{int}}$ and height $H_{\text{int}}$:

1. **Elevation Initialization:** Set starting row bottom elevation to $y_{\text{row}} = S_{\text{int}}$.
2. **Row Fit Check:** While $y_{\text{row}} + H_{\text{int}} \le W_{\text{int}} - S_{\text{int}}$:
   a. **Lateral Initialization:** Set candidate panel left edge to $x_{\text{cand}} = S_{\text{int}}$.
   b. **Panel Fit Check:** While $x_{\text{cand}} + W_{\text{int}} \le L_{\text{int}} - S_{\text{int}}$:
      - Construct candidate rectangle: $R_{\text{cand}} = [x_{\text{cand}}, y_{\text{row}}, x_{\text{cand}} + W_{\text{int}}, y_{\text{row}} + H_{\text{int}}]$.
      - Query expanded obstacle exclusion zones intersecting $R_{\text{cand}}$:
        $$\mathcal{O}_{\text{colliding}} = \{O_k \mid R_{\text{cand}} \cap O_k^{\text{expanded}} \text{ has positive area}\}$$
      - **Case 1 (Clear Position):** If $\mathcal{O}_{\text{colliding}} = \emptyset$:
        - Validate boundary containment and non-overlap with placed panels via `ConstraintValidator.validate_candidate()`.
        - Record panel placement with indices `(panel_index, row_id, col_id)`.
        - Advance candidate $X$ coordinate past current panel plus required inter-panel clearance $G_{p,\text{int}}$:
          $$x_{\text{cand}} \leftarrow x_{\text{cand}} + W_{\text{int}} + G_{p,\text{int}}$$
      - **Case 2 (Obstacle Interruption):** If $\mathcal{O}_{\text{colliding}} \neq \emptyset$:
        - Resume placement immediately to the right of all colliding obstacles:
          $$x_{\text{cand}} \leftarrow \max\left(x_{\text{cand}} + 1, \max_{O_k \in \mathcal{O}_{\text{colliding}}} O_{k,x\max}^{\text{expanded}}\right)$$
   c. **Row Advancement:** Advance row elevation along the $Y$-axis by panel height plus inter-row walkway gap $G_{r,\text{int}}$:
      $$y_{\text{row}} \leftarrow y_{\text{row}} + H_{\text{int}} + G_{r,\text{int}}$$

---

## 4. Orientation Handling

The engine respects the `allowed_orientations` parameter (`"portrait"`, `"landscape"`, or `"both"`):

| Orientation | Module Width along $X$ | Module Height along $Y$ | Pitch along $X$ | Pitch along $Y$ |
|---|---|---|---|---|
| **Portrait** | $W_{\text{module,int}}$ | $L_{\text{module,int}}$ | $W_{\text{module,int}} + G_{p,\text{int}}$ | $L_{\text{module,int}} + G_{r,\text{int}}$ |
| **Landscape** | $L_{\text{module,int}}$ | $W_{\text{module,int}}$ | $L_{\text{module,int}} + G_{p,\text{int}}$ | $W_{\text{module,int}} + G_{r,\text{int}}$ |

When `"both"` is specified, the engine deterministically executes Pass A (Portrait) and Pass B (Landscape), evaluates feasibility and spatial efficiency for each, and preserves both candidate results in `alternatives_evaluated`.

---

## 5. Obstacle Interruption and Resumption

Obstacles are handled through outward expansion and localized row splitting:

1. **Outward Expansion:** Obstacles are conservatively expanded outward by their configured buffer $B$:
   $$x_{\min,\text{int}} = \lfloor x \times M \rfloor - \lceil B \times M \rceil, \quad x_{\max,\text{int}} = \lceil (x + w) \times M \rceil + \lceil B \times M \rceil$$
   $$y_{\min,\text{int}} = \lfloor y \times M \rfloor - \lceil B \times M \rceil, \quad y_{\max,\text{int}} = \lceil (y + h) \times M \rceil + \lceil B \times M \rceil$$
2. **Buffer Preservation:** Buffers extending past gross roof boundaries are **unclipped**, preserving full safety buffer extents.
3. **Row Splitting & Resumption:** A central obstacle (e.g. vent pipe or skylight) does not invalidate an entire row. Panels are placed to the left ($x + w \le x_{\text{obs,min}}$), interrupted across the obstacle zone, and resume immediately to the right ($x \ge x_{\text{obs,max}}$) if remaining space $\ge W_{\text{int}}$. Resumed panels strictly maintain configured inter-panel clearances (`test_obstacle_resumption_inter_panel_clearance_preserved`).
4. **Multiple Obstacles in One Row:** Multiple obstacles placed along the same horizontal row segment cleanly split the row multiple times (`test_multiple_obstacles_in_same_row`).
5. **Multiple Simultaneous Obstacle Collisions:** When a candidate panel spans across two adjacent or overlapping obstacles simultaneously, the engine queries all colliding obstacles and advances past the maximum $x_{\max}$ among them in a single step (`test_multiple_simultaneous_obstacle_collisions`).
6. **Completely Blocked Row Elevation:** When an obstacle or keep-out zone spans across the entire usable width of the roof, the engine attempts candidate placement at $x_{\min}$, detects collision, skips past the obstacle extent, finds no remaining lateral space, and cleanly advances $y_{\text{row}}$ to the next row elevation above the obstacle (`test_completely_blocked_horizontal_row`).
7. **Clean Termination:** When the remaining lateral or vertical space is strictly smaller than the required module dimensions, inner and outer iteration loops terminate deterministically without infinite cycles or partial placements (`test_termination_when_remaining_strip_too_narrow`, `test_tc001_roof_too_small_for_any_panel`).
8. **Dedicated Maintenance Walkways:** Dedicated maintenance walkways modeled as corridor obstacles (e.g., $1.0\text{ m}$ width spanning $y=0$ to $y=W$) cleanly bisect the array into distinct West and East sub-arrays while maintaining the corridor 100% panel-free (`test_tc008b_dedicated_maintenance_walkway_corridor_bisection`).

---

## 6. Clearance and Containment Enforcement

The engine enforces zero-tolerance physical constraints without negative tolerance relaxation:

1. **Perimeter Setbacks:** $\forall i: x_i \ge S_{\text{edge}}, y_i \ge S_{\text{edge}}, x_i + w_i \le L - S_{\text{edge}}, y_i + h_i \le W - S_{\text{edge}}$ (protrusion margin $\ge 0.0$).
2. **Inter-Panel Clearance:** $\forall i, j \text{ in same row segment}: x_j - (x_i + w_i) \ge G_p$ strictly ($0.1\text{ mm}$ deficit rejected).
3. **Inter-Row Clearance:** $\forall \text{ rows } k, k+1: y_{k+1} - (y_k + h_k) \ge G_r$ strictly ($0.1\text{ mm}$ deficit rejected).
4. **Mutual Non-Overlap:** $\forall i \neq j: \text{Area}(R_i \cap R_j) = 0$ strictly.
5. **Obstacle Keep-Out:** $\forall i, k: \text{Area}(R_i \cap O_k^{\text{expanded}}) = 0$ strictly.
6. **Limitation:** Clearances are evaluated along orthogonal $X$ and $Y$ axes. General 2D diagonal Euclidean distance is not computed.

---

## 7. Candidate Comparison and Deterministic Tie-Breaking

When comparing candidate layouts across orientations, the engine evaluates landscape and portrait layouts for the **same selected panel model**.

The comparison follows a deterministic mathematical hierarchy:

1. **Primary Objective — Panel Count ($N$):** Maximize $N$. The orientation fitting more panels is selected.
2. **Capacity Equality on Equal Counts:** Because the comparison is conducted for a single selected panel model with invariant rated power $P_{\text{STC}}$, installed DC capacity is mathematically identical for equal panel counts:
   $$P_{\text{DC}} = \frac{N \times P_{\text{STC}}}{1{,}000}\quad \Longrightarrow\quad N_1 = N_2 \implies P_{\text{DC},1} = P_{\text{DC},2}$$
3. **Area Equality on Equal Counts:** Similarly, module surface area $A_{\text{panel}} = L_{\text{panel}} \times W_{\text{panel}}$ is invariant to orientation. Therefore, total occupied panel area is identical:
   $$A_{\text{occupied}} = N \times A_{\text{panel}}\quad \Longrightarrow\quad N_1 = N_2 \implies A_{\text{occupied},1} = A_{\text{occupied},2}$$
   Because net usable roof area $A_{\text{net\_usable}}$ is governed strictly by the roof perimeter and obstacle keep-out zones (independent of panel orientation), unutilized usable area is also mathematically identical:
   $$A_{\text{unutilized}} = A_{\text{net\_usable}} - A_{\text{occupied}}\quad \Longrightarrow\quad N_1 = N_2 \implies A_{\text{unutilized},1} = A_{\text{unutilized},2}$$
4. **Effective Tie-Breaker — Stable Orientation Preference:** Because equal panel counts yield mathematically identical capacity and unutilized area for the same panel model, the effective tie-breaker after panel count is the documented stable orientation preference (`"portrait"` over `"landscape"`).
5. **Preserved Comparison Key:** The implemented sorting key in `fit_panels()` maintains this exact structure without arbitrary weighting heuristics:
   ```python
   def sort_key(cand: OrientationCandidateResult):
       orientation_pref = 1 if cand.orientation == "portrait" else 0
       return (
           cand.placed_panel_count,
           cand.installed_dc_capacity_kwp,
           -cand.unutilized_usable_area_m2,
           orientation_pref
       )
   ```

---

## 8. Determinism and Reproducibility

- **Zero Randomness:** The algorithm uses no pseudo-random initializations, stochastic sweeps, or unseeded operations.
- **Ordered Iteration:** Rows and columns advance monotonically from the bottom-left origin.
- **100-Iteration Bit-for-Bit Verification:** Test `TC-015` executes 100 consecutive full placement cycles on a complex roof with 3 obstacles. All 100 executions produce bit-for-bit identical coordinate arrays and JSON hashes ($\Delta = 0.0$).

---

## 9. Output Schema & Example Result

The engine produces output strictly adhering to [`docs/engineering/phase7_input_output_contract.md`](../../docs/engineering/phase7_input_output_contract.md).

### Example JSON Payload (Residential Roof with Vent Pipe)

```json
{
  "configuration_id": "CFG-ROOF-JSON-TEST-PNL-CANADIAN-445W-PORTRAIT",
  "roof_id": "ROOF-JSON-TEST",
  "panel_id": "PNL-CANADIAN-445W",
  "panel_model": "HiKu CS3W-445MS",
  "feasibility_status": "FEASIBLE",
  "selected_orientation": "portrait",
  "panel_count": 30,
  "installed_dc_capacity_kwp": 13.35,
  "module_stc_power_wp": 445.0,
  "spatial_metrics": {
    "gross_roof_area_m2": 96.0,
    "perimeter_setback_area_m2": 19.0,
    "obstacle_exclusion_area_m2": 0.64,
    "net_usable_roof_area_m2": 76.36,
    "occupied_panel_area_m2": 66.2768,
    "unutilized_usable_area_m2": 10.0832,
    "roof_utilization_factor": 0.6904,
    "usable_space_packing_efficiency": 0.8679
  },
  "placements": [
    {
      "panel_index": 1,
      "row_id": 1,
      "col_id": 1,
      "x_m": 0.5,
      "y_m": 0.5,
      "width_m": 1.048,
      "height_m": 2.108,
      "orientation": "portrait"
    }
  ],
  "alternatives_evaluated": {
    "portrait": {
      "feasible": true,
      "panel_count": 30,
      "dc_capacity_kwp": 13.35
    },
    "landscape": {
      "feasible": true,
      "panel_count": 25,
      "dc_capacity_kwp": 11.125
    }
  },
  "constraint_violations": [],
  "engine_metadata": {
    "algorithm": "RowWiseStripPackingEngine",
    "algorithm_version": "1.0.0",
    "algorithm_selection_rationale": "Continuous linear racking rail compliance with obstacle interruption",
    "optimality_guarantee": "BEST_FEASIBLE_CONFIGURATION_FOUND",
    "disclaimer": "The engine generates geometrically feasible panel placements under the supplied roof geometry, module dimensions, clearances and obstacle assumptions. These results do not establish structural safety, regulatory compliance or installation approval.",
    "execution_timestamp": "2026-11-10T14:10:05.123456+00:00"
  }
}
```

---

## 10. Test Scenarios and Canonical Test IDs

The placement engine test suite in [`tests/test_placement_engine.py`](../../tests/test_placement_engine.py) implements the canonical Phase 7 scenarios defined in [`docs/engineering/phase7_testing_strategy.md`](../../docs/engineering/phase7_testing_strategy.md) alongside focused obstacle-interruption and clearance-preservation verification cases:

| Test ID | Canonical Scenario Name | Verified Outcome |
|---|---|---|
| `TC-001` | Roof Too Small for Any Panel | Returns `panel_count = 0`, status `INFEASIBLE_ROOF_TOO_SMALL`. |
| `TC-002` | Exact-Fit Roof (Zero Clearance Boundary) | Usable roof precisely equals single panel dimensions; returns `panel_count = 1`. |
| `TC-003` | Portrait-Only Feasibility | Dimensions permit portrait mounting; landscape rejected; selects portrait. |
| `TC-004` | Landscape-Only Feasibility | Dimensions permit landscape mounting; portrait rejected; selects landscape. |
| `TC-005` | Both Orientations Feasible | Compares portrait and landscape; selects orientation maximizing capacity. |
| `TC-005A` | Orientation Tie-Breaking | Equal count and capacity selects portrait as stable deterministic default. |
| `TC-006` | Multi-Row & Multi-Column Clear Commercial Roof | Large commercial roof ($20\text{ m} \times 10\text{ m}$) correctly places 80 modules across 5 rows. |
| `TC-007A` | Configurable Setback Variation Suite | 4 parameter variations ($S \in \{0.0, 0.25, 0.50, 1.20\}\text{ m}$) scale usable envelope monotonically. |
| `TC-008` | Central Obstacle Avoidance & Row Resumption | Row splits around central vent; resumes placement to the right of obstacle buffer. |
| `TC-008A` | Separation of Obstacle Dimensions and Buffer | 3 buffer variations ($B \in \{0.0, 0.15, 0.50\}\text{ m}$) alter exclusion zone independently. |
| `TC-008B` | Dedicated Maintenance Walkway Corridor Bisection | Array cleanly bisects into West and East sub-arrays; corridor remains 100% clear. |
| `TC-009` | Edge / Corner Obstacle Avoidance | Corner obstacle omits local panels; remaining grid remains packed. |
| `TC-010A` | Configurable Clear Spacing Variation | 3 spacing variations ($G_p \in \{0.005, 0.020, 0.035\}\text{ m}$) scale pitch collision-free. |
| `TC-014` | Invalid Roof Geometry Input | Excessive setbacks consuming roof raise `InvalidRoofSpecificationError`. |
| `TC-015` | Strict Determinism Check (100 Iterations) | 100 consecutive runs yield bit-for-bit identical coordinate arrays and JSON hashes. |
| `OBS-RESUME` | Obstacle Resumption Clearance Preservation | Dedicated check verifying resumed panels strictly maintain $G_p$ spacing. |
| `OBS-MULTI` | Multiple Simultaneous Obstacle Collisions | Dedicated check verifying candidate spanning 2 obstacles jumps past combined $x_{\max}$. |
| `OBS-BLOCK` | Completely Blocked Horizontal Row | Dedicated check verifying row elevation completely blocked advances cleanly to next row. |
| `OBS-TERM` | Termination on Insufficient Space | Dedicated check verifying loop terminates when remaining horizontal strip $< W_{\text{panel}}$. |
| Law 3.1 | Spatial Conservation Law | Gross area equals usable plus setback; net usable equals occupied plus unutilized. |
| Law 3.2 | Capacity Consistency Law | Installed DC capacity matches $N \times P_{\text{STC}} / 1000\text{ kW}_p$ within $10^{-3}\text{ kW}_p$. |

---

## 11. Test Execution Evidence and Pytest Accounting

### 11.1 Comprehensive Pytest Command Accounting

During the implementation and verification of the Phase 7 Row-Wise Placement Engine, exactly **10 pytest commands** were executed across the workspace:

| Command Executed | Category | Test Items Evaluated | Result |
|---|---|---|---|
| `pytest -q tests/test_roof_fit_foundation.py` | Foundation Sanity Check 1 | 70 collected, 70 executed | 70 passed in 0.24s |
| `pytest -q tests/test_roof_fit_foundation.py` | Foundation Sanity Check 2 | 70 collected, 70 executed | 70 passed in 0.24s |
| `pytest -q tests/test_roof_fit_foundation.py` | Foundation Sanity Check 3 | 70 collected, 70 executed | 70 passed in 0.24s |
| `pytest -v --durations=10 tests/test_placement_engine.py` | Placement Suite Execution 1 | 28 collected, 28 executed | 28 passed in 0.65s |
| `pytest -v --durations=10 tests/` | Full Suite Execution 1 | 98 collected, 98 executed | 98 passed in 0.72s |
| `pytest --collect-only -q tests/test_placement_engine.py` | Collection-Only Command 1 | 28 collected | 28 items in 0.53s |
| `pytest -v --durations=10 tests/` | Full Suite Execution 2 | 98 collected, 98 executed | 98 passed in 0.70s |
| `pytest -v --durations=10 tests/test_placement_engine.py` | Placement Suite Execution 2 (with 4 obstacle tests) | 32 collected, 32 executed | 32 passed in 0.68s |
| `pytest -v --durations=10 tests/` | Full Suite Execution 3 (Final Full Suite) | 102 collected, 102 executed | 102 passed in 0.69s |
| `pytest --collect-only -q tests/` | Collection-Only Command 2 | 102 collected | 102 items in 0.58s |

#### Command Category Breakdown:
- **Total Pytest Commands Executed:** 10 commands.
- **Full-Suite Executions (`tests/`):** 3 commands (Execution 1: 98 items; Execution 2: 98 items; Execution 3: 102 items).
- **Placement-Only Executions (`tests/test_placement_engine.py`):** 2 commands (Execution 1: 28 items; Execution 2: 32 items).
- **Foundation-Only Executions (`tests/test_roof_fit_foundation.py`):** 3 commands (70 items each).
- **Collection-Only Commands (`--collect-only`):** 2 commands (28 items and 102 items).

### 11.2 Final Full-Suite Test Execution Output

```
$ pytest -v --durations=10 tests/
============================= test session starts ==============================
platform darwin -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0 -- /opt/anaconda3/bin/python
cachedir: .pytest_cache
rootdir: /Users/apple/Documents/5th sem el/MLOps_EL/SolarSelect
plugins: anyio-4.10.0
collected 102 items

tests/test_placement_engine.py::TestBasicPlacement::test_tc001_roof_too_small_for_any_panel PASSED [  0%]
tests/test_placement_engine.py::TestBasicPlacement::test_tc002_exact_fit_roof_zero_clearance_boundary PASSED [  1%]
tests/test_placement_engine.py::TestBasicPlacement::test_tc006_multi_row_multi_column_clear_roof PASSED [  2%]
tests/test_placement_engine.py::TestOrientationSelection::test_tc003_portrait_only_feasibility PASSED [  3%]
tests/test_placement_engine.py::TestOrientationSelection::test_tc004_landscape_only_feasibility PASSED [  4%]
tests/test_placement_engine.py::TestOrientationSelection::test_tc005_both_orientations_feasible_capacity_selection PASSED [  5%]
tests/test_placement_engine.py::TestOrientationSelection::test_tc005a_orientation_tie_breaking PASSED [  6%]
tests/test_placement_engine.py::TestObstacleInterruption::test_tc008_central_obstacle_avoidance_and_row_resumption PASSED [  7%]
tests/test_placement_engine.py::TestObstacleInterruption::test_tc008a_separation_of_obstacle_dimensions_and_buffer[0.0-0] PASSED [  8%]
tests/test_placement_engine.py::TestObstacleInterruption::test_tc008a_separation_of_obstacle_dimensions_and_buffer[0.15-0] PASSED [  9%]
tests/test_placement_engine.py::TestObstacleInterruption::test_tc008a_separation_of_obstacle_dimensions_and_buffer[0.5-0] PASSED [ 10%]
tests/test_placement_engine.py::TestObstacleInterruption::test_tc008b_dedicated_maintenance_walkway_corridor_bisection PASSED [ 11%]
tests/test_placement_engine.py::TestObstacleInterruption::test_tc009_edge_corner_obstacle_avoidance PASSED [ 12%]
tests/test_placement_engine.py::TestObstacleInterruption::test_obstacle_blocking_first_position PASSED [ 13%]
tests/test_placement_engine.py::TestObstacleInterruption::test_multiple_obstacles_in_same_row PASSED [ 14%]
tests/test_placement_engine.py::TestObstacleInterruption::test_obstacle_resumption_inter_panel_clearance_preserved PASSED [ 15%]
tests/test_placement_engine.py::TestObstacleInterruption::test_multiple_simultaneous_obstacle_collisions PASSED [ 16%]
tests/test_placement_engine.py::TestObstacleInterruption::test_completely_blocked_horizontal_row PASSED [ 17%]
tests/test_placement_engine.py::TestObstacleInterruption::test_termination_when_remaining_strip_too_narrow PASSED [ 18%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc007a_configurable_setback_variation_suite[0.0] PASSED [ 19%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc007a_configurable_setback_variation_suite[0.25] PASSED [ 20%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc007a_configurable_setback_variation_suite[0.5] PASSED [ 21%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc007a_configurable_setback_variation_suite[1.2] PASSED [ 22%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc010a_configurable_clear_spacing_variation[0.005] PASSED [ 23%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc010a_configurable_clear_spacing_variation[0.02] PASSED [ 24%]
tests/test_placement_engine.py::TestClearancesAndSetbacks::test_tc010a_configurable_clear_spacing_variation[0.035] PASSED [ 25%]
tests/test_placement_engine.py::TestRobustnessAndDeterminism::test_invalid_panel_id_raises_panel_not_found PASSED [ 26%]
tests/test_placement_engine.py::TestRobustnessAndDeterminism::test_tc014_invalid_roof_specification_raises PASSED [ 27%]
tests/test_placement_engine.py::TestRobustnessAndDeterminism::test_tc015_strict_determinism_check_100_iterations PASSED [ 28%]
tests/test_placement_engine.py::TestOutputContractAndMathematicalLaws::test_output_json_serialization_matches_contract PASSED [ 29%]
tests/test_placement_engine.py::TestOutputContractAndMathematicalLaws::test_spatial_conservation_law PASSED [ 30%]
tests/test_placement_engine.py::TestOutputContractAndMathematicalLaws::test_capacity_consistency_law PASSED [ 31%]
tests/test_roof_fit_foundation.py::TestRoofSpecificationValidator::test_fnd_roof_spec_valid_passes PASSED [ 32%]
... [70 Foundation tests passed] ...
tests/test_roof_fit_foundation.py::TestConstraintValidator::test_fnd_val_multiple_simultaneous_violations_accumulated PASSED [100%]

============================= slowest 10 durations =============================
0.08s call     tests/test_placement_engine.py::TestRobustnessAndDeterminism::test_tc015_strict_determinism_check_100_iterations
0.01s setup    tests/test_placement_engine.py::TestBasicPlacement::test_tc001_roof_too_small_for_any_panel
0.01s setup    tests/test_roof_fit_foundation.py::TestCatalogueAdapter::test_tc013_missing_catalogue_dimensions_raises

============================= 102 passed in 0.69s ==============================
```

### 11.3 Final Test Item Reconciliation
- **Placement Engine Test Items:** 32 collected, 32 executed, 32 passed (100%).
- **Foundation Layer Test Items:** 70 collected, 70 executed, 70 passed (100%).
- **Final Full-Suite Test Items Collected:** 102.
- **Final Full-Suite Test Items Executed:** 102.
- **Passed:** 102 (100%).
- **Failed:** 0.
- **Skipped:** 0.
- **Execution Duration:** 0.69 seconds.

---

## 12. Engineering Assumptions

1. **Rooftop Planarity:** The placement engine assumes a 2D planar rectangular roof plane.
2. **Axis-Aligned Rails:** Module placement is aligned with Cartesian axes ($X$ parallel to eave, $Y$ up-slope).
3. **Obstacle Keep-Out Geometry:** Obstacles are modeled as axis-aligned bounding boxes with uniform expansion buffers.
4. **Heuristic Strip Packing:** Placement proceeds row-wise from the bottom-left origin ($S_{\text{int}}, S_{\text{int}}$). This models continuous linear racking rails common in residential and commercial PV installations.

---

## 13. Limitations & Disclaimers

1. **No Global Optimality Guarantee:** The algorithm is a deterministic strip-packing heuristic and does not guarantee finding a theoretical global maximum panel count.
2. **No Installation Certification:** Geometric feasibility does not establish structural load bearing, wind uplift resistance, electrical string feasibility, or fire code compliance.
3. **Axis-Aligned Clearance Only:** Lateral clearances and row gaps are evaluated orthogonally; diagonal Euclidean distances are not computed.
4. **No Financial Recommendations:** Financial metrics (LCOE, payback) and annual kWh yield generation belong to Phase 8.

---

## 14. Reproducibility Instructions

To reproduce all test results:

```bash
# 1. Activate project environment
cd /Users/apple/Documents/5th\ sem\ el/MLOps_EL/SolarSelect

# 2. Run placement engine tests (32 tests)
pytest -v --durations=10 tests/test_placement_engine.py

# 3. Run complete Phase 7 test suite (102 tests)
pytest -v --durations=10 tests/

# 4. Validate catalogue integrity
python3 src/validate_panel_catalogue.py
```

---

## 15. Files Created or Modified

| File | Status | Description |
|---|---|---|
| [`src/roof_fit/placement_engine.py`](../../src/roof_fit/placement_engine.py) | **CREATED** | `RowWisePlacementEngine`, `PanelPlacement`, `OrientationCandidateResult`, `PanelConfigurationResult`. |
| [`src/roof_fit/serializer.py`](../../src/roof_fit/serializer.py) | **CREATED** | `LayoutSerializer` for standard JSON contract serialization. |
| [`tests/test_placement_engine.py`](../../tests/test_placement_engine.py) | **CREATED / UPDATED** | 32 automated test items covering canonical scenarios `TC-001`–`TC-015` and focused obstacle-handling verification. |
| [`src/roof_fit/roof_validator.py`](../../src/roof_fit/roof_validator.py) | **MODIFIED** | Added `allowed_orientations` support and contract JSON schema key aliases. |
| [`src/roof_fit/constraint_validator.py`](../../src/roof_fit/constraint_validator.py) | **MODIFIED** | Added `validate_layout()` method for full-array post-placement assertions. |
| [`src/roof_fit/__init__.py`](../../src/roof_fit/__init__.py) | **MODIFIED** | Exported placement engine and serializer classes. |

---

## 16. Implementation Status

$$\mathbf{PHASE\ 7\ —\ ROW-WISE\ PLACEMENT\ ENGINE\ IMPLEMENTED\ (IN\ PROGRESS)}$$

The placement engine is implemented, mathematically verified, zero-tolerance enforced, and fully integrated with the catalogue and foundation layers. Phase 7 is ready for Prompt 4 (Serialization, Schema Validation & End-to-End Pipeline Integration).

