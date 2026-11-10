# Phase 7: Roof-Fit Engine — Testing & Verification Strategy

**Project:** SolarSelect — An End-to-End MLOps System for AI-Driven Rooftop Solar Selection and Yield Forecasting  
**Phase:** Phase 7 — Roof-Fit and Panel Configuration Engine (Prompt 1: Requirements & Engineering Design)  
**Document Status:** **`DRAFT_TESTING_STRATEGY`**  
**Related Documents:**
- [`phase7_requirements.md`](phase7_requirements.md)
- [`phase7_architecture.md`](phase7_architecture.md)
- [`phase7_algorithm_comparison.md`](phase7_algorithm_comparison.md)
- [`phase7_input_output_contract.md`](phase7_input_output_contract.md)
- [`../../configs/panels_catalogue.csv`](../../configs/panels_catalogue.csv)

---

## 1. Testing Philosophy & Engineering Framework

The Phase 7 placement engine handles physical geometric calculations that directly govern hardware safety, array layout feasibility, and capital expenditure sizing. Consequently, the testing framework enforces uncompromising physical and numerical standards:

1. **Strict Determinism:**
   - 100% of test cases must be deterministic. No pseudo-random number generators, stochastic sweeps, or unseeded initializations are permitted.
2. **Hard Minimum Clearances & Conservative Tolerances:**
   - Minimum inter-panel clear spacing ($G_{\text{panel}}$), inter-row clearance ($G_{\text{row}}$), perimeter setbacks ($S_{\text{edge}}$), and obstacle clearance buffers ($B$) are unyielding physical constraints enforced with zero tolerance relaxation: $\text{actual\_gap} \ge \text{required\_gap}$ strictly. Numerical tolerance **cannot** authorize any gap smaller than the configured minimum. An epsilon tolerance $\epsilon = 10^{-4}\text{ m}^2$ is reserved strictly for spatial conservation polygon area audits and floating-point display rounding.
3. **Automated Unit & Integration Test Coverage:**
   - Tests will be implemented in `tests/test_roof_fit_engine.py` using standard `pytest`. Every constraint invariant (containment, collision-free, setback compliance, clamp gap) must be validated via automated property assertions.
4. **Catalogue Invariance Verification:**
   - Tests verify that all 12 commercial modules in [`configs/panels_catalogue.csv`](../../configs/panels_catalogue.csv) can be processed without exception or data corruption.

---

## 2. Comprehensive Test Matrix & Accounting

The Phase 7 testing framework strictly decouples its four distinct verification accounting metrics (all test counts represent planned specifications prior to engine implementation):

1. **Distinct Logical Test Cases:** Exactly **20** logical test cases (`TC-001` through `TC-015`, including sub-cases `TC-005A`, `TC-007A`, `TC-008A`, `TC-008B`, and `TC-010A`).
2. **Planned pytest Test Invocations:** Exactly **31** discrete planned test function executions (14 single-case tests + 3 in `TC-010` + 3 in `TC-011` + 4 in `TC-007A` + 3 in `TC-008A` + 3 in `TC-010A` + 1 in `TC-015`).
3. **Planned Internal Determinism Iterations:** Exactly **100** consecutive loop executions planned inside the `TC-015` determinism verification test (within a single pytest invocation).
4. **Total Parameter Combinations Tested:** Exactly **16** distinct parameter values specified across the variation and boundary-value test scenarios (4 setbacks in `TC-007A`, 3 buffers in `TC-008A`, 3 clearances in `TC-010A`, 3 clearance boundaries in `TC-010`, 3 clearance boundaries in `TC-011`).

> **Accounting Reconciliation Note:** The earlier reported "125" figure inadvertently mixed pytest invocations ($26$) with internal loop iterations ($100$ in `TC-015`, calculated as $26 - 1 + 100 = 125$). Under strict testing governance, internal loop iterations are never conflated with pytest invocations. The suite specifies **31 planned pytest test invocations** and **100 planned internal determinism iterations**.

| Scenario ID | Test Scenario Name | Primary Verification Objective | Simulated Test Input | Specified Expected Engine Behavior & Mathematical Assertion |
|---|---|---|---|---|
| **TC-001** | **Roof Too Small for Any Panel** | Verify planned handling when usable roof is smaller than minimum module dimension. | Roof: $1.0\text{ m} \times 1.0\text{ m}$, Setback: $0.2\text{ m}$. Module: $1.7\text{ m} \times 1.0\text{ m}$. | Expected: Returns `panel_count = 0`, `installed_dc_capacity_kwp = 0.0`, status `INFEASIBLE_ROOF_TOO_SMALL`. Placements array is empty `[]`. |
| **TC-002** | **Exact-Fit Roof (Zero Clearance Boundary)** | Verify edge-case where usable roof precisely equals single panel dimensions. | Net Usable: $1.722\text{ m} \times 1.134\text{ m}$. Module: $1.722\text{ m} \times 1.134\text{ m}$ (`PNL-JINKO-430W`). | Expected: Returns `panel_count = 1`. Panel occupies $[0, 0, 1.722, 1.134]$. Status `FEASIBLE`. Zero boundary violation. |
| **TC-003** | **Portrait-Only Feasibility** | Verify that landscape is rejected when dimensions permit only portrait mounting. | Roof: $2.5\text{ m} \times 4.0\text{ m}$, Setback: $0.2\text{ m}$. Module: $2.1\text{ m} \times 1.05\text{ m}$. Usable: $2.1\text{ m} \times 3.6\text{ m}$. | Expected: Portrait: 1 panel fits ($2.1\text{ m} \le 3.6\text{ m}$ along Y, $1.05\text{ m} \le 2.1\text{ m}$ along X). Landscape: 0 fit ($2.1\text{ m} > 2.1\text{ m}$ requires clamp space). Selected: `portrait`. |
| **TC-004** | **Landscape-Only Feasibility** | Verify that portrait is rejected when dimensions permit only landscape mounting. | Usable: $3.5\text{ m} \times 1.5\text{ m}$. Module: $2.1\text{ m} \times 1.05\text{ m}$. | Expected: Landscape fits ($2.1\text{ m} \le 3.5\text{ m}$, $1.05\text{ m} \le 1.5\text{ m}$). Portrait fails ($2.1\text{ m} > 1.5\text{ m}$ along Y). Selected: `landscape`. |
| **TC-005** | **Both Orientations Feasible (Capacity Selection)** | Verify engine compares orientations and selects layout with highest panel count / kWp without claiming global optimality. | Usable: $10.0\text{ m} \times 5.0\text{ m}$. Module: $2.0\text{ m} \times 1.0\text{ m}$. | Expected: Evaluates both orientations; selects the orientation maximizing $P_{\text{DC}}$. Records alternative in `alternatives_evaluated`. Status reported as `BEST_FEASIBLE_CONFIGURATION_FOUND`. |
| **TC-005A** | **Row Starting Position Sensitivity** | Demonstrate heuristic nature by comparing top-down vs bottom-up row offsets around an obstacle. | Roof: $10.0\text{ m} \times 6.0\text{ m}$. Obstacle at $y=2.2\text{ m}$. Sweeps starting from $y=S$ vs $y=W-S$. | Expected: Confirms that different starting positions can yield different panel counts; engine selects best feasible found. Does NOT assert global optimality. |
| **TC-006** | **Multi-Row & Multi-Column Clear Roof** | Verify grid math on large unobstructed commercial roof. | Usable: $20.0\text{ m} \times 10.0\text{ m}$. Module: $1.75\text{ m} \times 1.0\text{ m}$, $G_p=0.02, G_r=0.05$. | Expected: Computes columns $n_x = \lfloor (L + G_p) / (W_m + G_p) \rfloor$, rows $n_y = \lfloor (W + G_r) / (L_m + G_r) \rfloor$. Total $N = n_x \times n_y$. Coordinates perfectly regular. |
| **TC-007** | **Perimeter Edge Setback Enforcement** | Verify that no panel breaches the defined setback perimeter under hard boundary inequality. | Roof: $10.0\text{ m} \times 8.0\text{ m}$, Setback: $1.0\text{ m}$. | Expected: Hard constraint: $\forall i: x_i \ge 1.0$, $y_i \ge 1.0$, $x_i + w_i \le 9.0$, $y_i + h_i \le 7.0$ (protrusion $\le 0.0$). Total setback area $= 10 \times 8 - 8 \times 6 = 32.0\text{ m}^2$. |
| **TC-007A** | **Configurable Setback Variation Suite** | Verify engine dynamically adjusts usable boundary across diverse setback inputs. | Test setbacks $S \in \{0.0\text{ m}, 0.25\text{ m}, 0.50\text{ m}, 1.20\text{ m}\}$ (4 planned pytest invocations). | Expected: Usable area scales monotonically: $A_{\text{usable}}(S_1) > A_{\text{usable}}(S_2)$ for $S_1 < S_2$. Panel counts scale appropriately. Zero regulatory compliance claimed. |
| **TC-008** | **Central Obstacle Avoidance** | Verify that an obstacle splits a row without invalidating adjacent rows. | Roof: $12.0\text{ m} \times 6.0\text{ m}$. Obstacle: Vent at $x=6.0, y=3.0, w=0.5, h=0.5, \text{buf}=0.2$. | Expected: Panels placed to left of obstacle ($x \le 5.8$) and right ($x \ge 6.7$). Zero panel rectangles intersect $[5.8, 2.8, 6.7, 3.7]$. Status `FEASIBLE`. |
| **TC-008A** | **Separation of Obstacle Dimensions and Buffer** | Verify that changing obstacle buffer alters exclusion zone while keeping obstacle geometry constant. | Fixed obstacle $0.4\text{ m} \times 0.4\text{ m}$. Evaluate buffers $B \in \{0.0\text{ m}, 0.15\text{ m}, 0.30\text{ m}\}$ (3 planned pytest invocations). | Expected: Effective exclusion width equals $0.4 + 2B$. Proves engine treats physical obstacle bounds and clearance buffers as distinct entities. |
| **TC-008B** | **Dedicated Maintenance Walkway Corridor** | Verify modeling of an explicit maintenance walkway corridor bisecting roof array. Note: Walkway dimension ($1.0\text{ m}$ or $0.8\text{ m}$) is strictly an illustrative test input, not a universal statutory or engineering requirement. Walkway dimensions are fully configurable user inputs. | Roof: $15.0\text{ m} \times 8.0\text{ m}$. Walkway corridor obstacle: $x=7.0\text{ m}, y=0.0\text{ m}, w=1.0\text{ m}, h=8.0\text{ m}$. | Expected: Array splits into two sub-arrays (West array $x + w_i \le 7.0\text{ m}$, East array $x \ge 8.0\text{ m}$). Walkway corridor remains $100\%$ clear. |
| **TC-009** | **Edge / Corner Obstacle Avoidance** | Verify handling of obstacle located along perimeter or in a roof corner. | Obstacle placed at $x=0.6, y=0.6, w=1.0, h=1.0$. | Expected: Local corner panels omitted; remaining grid remains packed. No array misalignment. |
| **TC-010** | **Inter-Panel Clear Spacing Boundary Verification** | Boundary-value test scenarios with specified expected outcomes for hard minimum clear spacing. | Nominal $G_{\text{panel}} = 0.020\text{ m}$ ($20\text{ mm}$), step $\delta = 0.0001\text{ m}$ ($0.1\text{ mm}$):<br/>1. Below: $0.0199\text{ m}$<br/>2. At: $0.0200\text{ m}$<br/>3. Above: $0.0201\text{ m}$<br/>(3 planned pytest invocations). | Specified expected outcome: Gap below minimum ($0.0199\text{ m}$) is specified to FAIL with `ClearanceViolationError`. Gaps at ($0.0200\text{ m}$) and above ($0.0201\text{ m}$) are specified to PASS. Planned assertion enforces $\text{actual\_gap} \ge G_{\text{panel}}$ strictly without numerical tolerance relaxation. |
| **TC-010A** | **Configurable Clear Spacing Variation** | Verify engine dynamically handles custom inter-panel clearances. | Evaluate $G_{\text{panel}} \in \{0.005\text{ m}, 0.020\text{ m}, 0.035\text{ m}\}$ (3 planned pytest invocations). | Expected: Confirms pitch scales as $W_m + G_p$; layout remains collision-free across all spacings. |
| **TC-011** | **Inter-Row Spacing Clearance Boundary Verification** | Boundary-value test scenarios with specified expected outcomes for hard minimum inter-row clearance. | Nominal $G_{\text{row}} = 0.050\text{ m}$ ($50\text{ mm}$), step $\delta = 0.0001\text{ m}$ ($0.1\text{ mm}$):<br/>1. Below: $0.0499\text{ m}$<br/>2. At: $0.0500\text{ m}$<br/>3. Above: $0.0501\text{ m}$<br/>(3 planned pytest invocations). | Specified expected outcome: Row gap below minimum ($0.0499\text{ m}$) is specified to FAIL with `ClearanceViolationError`. Row gaps at ($0.0500\text{ m}$) and above ($0.0501\text{ m}$) are specified to PASS. Planned assertion enforces $\text{actual\_row\_gap} \ge G_{\text{row}}$ strictly without numerical tolerance relaxation. |
| **TC-012** | **Pairwise Non-Overlap (Collision Free)** | Rigorous mathematical check that no two panel polygons overlap under hard zero-tolerance invariant. | Standard commercial roof layout with 30+ panels. | Expected: Pairwise check $\forall i \neq j$: Intersection area $= 0.0$ strictly. Assert collision-free invariant holds unconditionally. |
| **TC-013** | **Missing Catalogue Dimensions Handling** | Verify graceful error handling when querying panel record lacking length/width. | Simulated catalogue record with `length_mm = NaN`. | Expected: Raises `MissingPanelDimensionError` with clear message identifying `panel_id`. Does not crash or invent synthetic defaults. |
| **TC-014** | **Invalid Roof Geometry Input** | Verify rejection of invalid roof dimensions (negative or zero length, setbacks exceeding roof). | Negative roof length ($L = -5.0$), or Setback $S = 4.0\text{ m}$ on Roof Width $W = 6.0\text{ m}$ ($2S > W$). | Expected: Raises `InvalidRoofSpecificationError` or returns status `INFEASIBLE_SETBACKS_EXCEED_ROOF`. |
| **TC-015** | **Strict Determinism Check (100 Iterations)** | Verify that identical inputs generate bit-for-bit identical coordinates across repeated runs. | Single planned pytest invocation running 100 consecutive executions on complex roof with 3 obstacles. | Expected: Output JSON hashes and coordinate arrays match bit-for-bit with 0 deviation ($\Delta = 0.0$). 1 planned pytest invocation, 100 planned internal determinism iterations. |

---

## 3. Mathematical Assertion Equations

The test suite enforces the following mathematical assertions for every generated layout:

### 3.1 Spatial Conservation Law
$$\text{Area}_{\text{gross}} = \text{Area}_{\text{usable}} + \text{Area}_{\text{setback}} + \text{Area}_{\text{obstacle\_exclusive}}$$
$$\text{Area}_{\text{usable}} = \text{Area}_{\text{occupied}} + \text{Area}_{\text{unutilized}}$$
Assert: $|\text{Area}_{\text{gross}} - (\text{Area}_{\text{occupied}} + \text{Area}_{\text{unutilized}} + \text{Area}_{\text{setback}} + \text{Area}_{\text{obstacle\_exclusive}})| < 10^{-4}$

### 3.2 Capacity Consistency Law
$$P_{\text{DC}} = \frac{N \times P_{\text{STC}}}{1000} \quad (\text{kW}_p)$$
Assert: $|P_{\text{DC}} - (N \times P_{\text{STC}} / 1000)| < 10^{-4}$

### 3.3 Packing Density Bound
The packing density within usable roof space cannot exceed theoretical physical limits:
$$\text{Packing Efficiency} = \frac{\text{Area}_{\text{occupied}}}{\text{Area}_{\text{usable}}} < \frac{W_m \times L_m}{(W_m + G_p) \times (L_m + G_r)} < 1.0$$
Assert: $0.0 \le \text{Packing Efficiency} \le 0.98$ for any realistic physical installation.

### 3.4 Hard Minimum Clearance & Boundary Laws
The test suite enforces exact physical clearances without numerical tolerance relaxation:
1. **Inter-Panel Clearance Law:** $\forall i, j \text{ adjacent in row}: \quad x_j - (x_i + w_i) \ge G_{\text{panel}}$ strictly ($\text{actual\_gap} < G_{\text{panel}}$ fails).
2. **Inter-Row Clearance Law:** $\forall \text{ adjacent rows } k, k+1: \quad y_{k+1} - (y_k + h_k) \ge G_{\text{row}}$ strictly ($\text{actual\_row\_gap} < G_{\text{row}}$ fails).
3. **Perimeter Boundary Law:** $\forall i: \quad x_i \ge S_{\text{edge}}, y_i \ge S_{\text{edge}}, x_i + w_i \le L - S_{\text{edge}}, y_i + h_i \le W - S_{\text{edge}}$ strictly (protrusion $\le 0.0$).
4. **Obstacle Buffer Law:** $\forall i, k: \quad \text{dist}(R_i, O_k) \ge B_k$ strictly ($\text{Area}(R_i \cap O_k^{\text{buffered}}) \le 0.0$).

