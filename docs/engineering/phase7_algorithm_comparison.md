# Phase 7: Roof-Fit Packing Algorithm Investigation & Comparative Analysis

**Project:** SolarSelect — An End-to-End MLOps System for AI-Driven Rooftop Solar Selection and Yield Forecasting  
**Phase:** Phase 7 — Roof-Fit and Panel Configuration Engine (Prompt 1: Requirements & Engineering Design)  
**Document Status:** **`DRAFT_ALGORITHM_EVALUATION`**  
**Related Documents:**
- [`phase7_requirements.md`](phase7_requirements.md)
- [`phase7_architecture.md`](phase7_architecture.md)
- [`phase7_input_output_contract.md`](phase7_input_output_contract.md)
- [`phase7_testing_strategy.md`](phase7_testing_strategy.md)

---

## 1. Problem Formulation: The 2D Rooftop Solar Packing Problem

The physical arrangement of photovoltaic modules on a building rooftop belongs to the mathematical family of **Two-Dimensional Orthogonal Rectangle Packing Problems (2D-RPP)** with irregular internal exclusions.

Formally, let:
- A gross rectangular roof $R$ be bounded by $[0, L_{\text{roof}}] \times [0, W_{\text{roof}}] \subset \mathbb{R}^2$.
- A perimeter setback width $S_{\text{edge}} \ge 0$ define the net usable bounding box:
  $$U = [S_{\text{edge}},\ L_{\text{roof}} - S_{\text{edge}}] \times [S_{\text{edge}},\ W_{\text{roof}} - S_{\text{edge}}]$$
- A set of $K$ disjoint rectangular obstacles $\{O_1, O_2, \dots, O_K\}$ reside on the roof, each expanded by safety clearance buffer $B_k$. The forbidden obstacle domain is:
  $$\Omega = \bigcup_{k=1}^K O_k^{\text{buffered}}$$
- A target PV module have bare dimensions $(L_m, W_m)$, inter-panel clamp gap $G_p$, and inter-row pitch gap $G_r$. The effective bounding dimensions under orientation $\theta \in \{\text{portrait}, \text{landscape}\}$ are $(w_e, h_e)$.

### Mathematical Objective
Find a finite set of $N$ non-overlapping placement coordinates $\{(x_i, y_i)\}_{i=1}^N$ such that:
$$\max N \quad \text{subject to:}$$
1. **Containment:** $\forall i \in \{1, \dots, N\}, \quad [x_i, x_i + w_e] \times [y_i, y_i + h_e] \subseteq U$
2. **Pairwise Non-Overlap:** $\forall i \neq j, \quad \text{Area}\Big(([x_i, x_i + w_e] \times [y_i, y_i + h_e]) \cap ([x_j, x_j + w_e] \times [y_j, y_j + h_e])\Big) = 0$
3. **Obstacle Clearance:** $\forall i, \quad ([x_i, x_i + w_e] \times [y_i, y_i + h_e]) \cap \Omega = \emptyset$

Because the general 2D rectangle packing problem is strongly **NP-hard**, exact global optimization (e.g. Mixed-Integer Linear Programming or branch-and-cut) scales poorly when obstacles fragment the solution space. Furthermore, purely unconstrained mathematical bin packing can produce disjoint, scattered panel placements that are physically impossible or prohibitively expensive to mount using standard linear racking rails.

---

## 2. Comparative Evaluation of Packing Algorithms

Five candidate algorithmic approaches were investigated for the SolarSelect Phase 7 engine:

### 2.1 Algorithm 1: Uniform Grid Placement (Naive Baseline)
- **Concept:** Discretizes the usable roof area into a regular matrix of grid cells sized exactly $(w_e \times h_e)$. For each cell $(r, c)$, an intersection test is performed against the obstacle set $\Omega$. Cells intersecting an obstacle are pruned.
- **Complexity:** $O(n_x \times n_y \times K)$, which evaluates in sub-millisecond time ($< 0.1\text{ ms}$).
- **Strengths:** 
  - Trivial to implement and mathematically robust.
  - Generates perfectly aligned rectilinear arrays preferred by solar installers for visual symmetry and straightforward rail installation.
- **Weaknesses:**
  - Highly rigid. A small plumbing vent positioned at the corner of a grid line may eliminate an entire panel even if shifting the row by a few centimetres would preserve it.
  - Cannot naturally accommodate mixed orientations or row-staggering.

### 2.2 Algorithm 2: Row-Wise Strip Packing with Obstacle Interruption (Recommended Initial Algorithm)
- **Concept:** Sweeps across the roof along the primary mounting axis (typically parallel to eaves or ridges), establishing continuous horizontal or vertical rows. Within each row, panels are placed sequentially. When an obstacle is encountered, the current strip is interrupted: placement advances to the obstacle's far boundary plus required clearance buffer, and resumes if sufficient remaining row length exists.
- **Complexity:** $O(N_{\text{rows}} \times N_{\text{cols}} \times K)$ with greedy coordinate skipping.
- **Strengths:**
  - **Direct Real-World Racking Alignment:** Solar mounting systems (e.g., Clenergy PostMount, Unirac SolarMount) utilize continuous extruded aluminum rails. Installers require panels to sit on collinear rails. Row-wise placement naturally mirrors real physical installation constraints.
  - Excellent obstacle avoidance: splits individual rows around vents while preserving alignment across adjacent rows.
  - Deterministic analytical sweep; execution time will be empirically benchmarked after implementation across representative roof dimensions.
- **Weaknesses:**
  - Does not explore non-rectilinear, diagonal, or tessellated patterns.
  - As a directional heuristic, different row starting positions (e.g. bottom-up vs top-down) may produce different panel counts on obstacle-fragmented roofs.

### 2.3 Algorithm 3: Maximal Rectangles (MaxRects - Advanced Heuristic)
- **Concept:** Maintains an explicit data structure of all overlapping "Maximal Empty Rectangles" (MERs) within the free space. When a panel is placed, all intersecting free rectangles are split into up to four new sub-rectangles, non-maximal rectangles are pruned, and the next panel is chosen using a heuristic rule (e.g., Best-Area-Fit, Best-Short-Side-Fit, Bottom-Left).
- **Complexity:** $O(N^3 \times K)$, scaling to tens or hundreds of milliseconds as panel counts reach commercial scales ($N > 200$).
- **Strengths:**
  - Exceptional theoretical packing density. Highly effective at squeezing modules into irregular leftover pockets around multiple complex obstacles.
  - Naturally supports multi-size module packing (e.g. mixing 60-cell and 72-cell modules).
- **Weaknesses:**
  - **Poor Structural Realism:** Can place isolated, "floating" panels or staggered patches that require separate, non-continuous mounting rails, dramatically increasing installation labor and hardware cost.
  - Significantly higher implementation and maintenance complexity.

### 2.4 Algorithm 4: Skyline-Based Packing
- **Concept:** Maintains an upper polygonal envelope ("skyline") of placed panels. The algorithm finds the lowest horizontal flat segment of the skyline, tests whether a candidate panel fits, and updates the skyline elevation.
- **Complexity:** $O(N \log N + N \times K)$.
- **Strengths:**
  - Very fast; popular in 2D strip-packing problems (e.g., sheet-metal nesting, texture atlasing).
- **Weaknesses:**
  - Inherently directional (designed for gravity-fed bottom-to-top stacking).
  - Struggles with arbitrary internal obstacles that exist "above" the current skyline.
  - Produces asymmetrical, jagged layouts that violate architectural rooftop aesthetics.

### 2.5 Algorithm 5: Guillotine-Based Binary Tree Packing
- **Concept:** Partitions the bounding box recursively. When a panel is placed in a free box, the remaining space is divided along horizontal or vertical "guillotine cuts" spanning edge-to-edge into two smaller rectangular sub-boxes.
- **Complexity:** $O(N \log N)$ using a binary space partitioning (BSP) tree.
- **Strengths:**
  - Simple recursive data structure.
  - Fast execution and straightforward collision queries.
- **Weaknesses:**
  - Overly restrictive: every cut must extend completely across the sub-box. A small obstacle (e.g., a $150\text{ mm}$ pipe) forces an edge-to-edge guillotine split, destroying valuable contiguous roof area.

---

## 3. Algorithmic Comparison Matrix

| Evaluation Dimension | 1. Uniform Grid Placement | 2. Row-Wise Strip Packing (Recommended) | 3. Maximal Rectangles (MaxRects) | 4. Skyline Packing | 5. Guillotine Packing |
|---|---|---|---|---|---|
| **Implementation Complexity** | Low (1-2 days) | Moderate (2-3 days) | High (1-2 weeks) | Moderate-High | Moderate |
| **Computational Time** | Low (Trivial matrix) | **To be benchmarked post-implementation** | Higher ($O(N^3)$ rectangle splits) | Moderate | Low |
| **Obstacle Avoidance** | Poor (Discards entire cells) | **Excellent** (Interrupts and skips strips) | **Superior** (Splits free space) | Fair (Directional bias) | Poor (Edge-to-edge cuts) |
| **Portrait / Landscape Feasibility** | Evaluates separately | **Evaluates separately & compares** | Natural support | Natural support | Natural support |
| **Racking Rail Realism (Physical Viability)** | High | **Highest** (Mirrors continuous linear rails) | Poor (Produces scattered/floating panels) | Fair | Moderate |
| **Visual Aesthetics (Symmetry)** | Highest | **High** (Structured rows) | Low (Fragmented pockets) | Low (Jagged skyline) | Moderate |
| **Mathematical Optimality** | Sub-optimal | **Heuristic (Best Feasible Found)** | Near-optimal packing ratio | Heuristic | Restricted Heuristic |
| **Fit for SolarSelect Scope** | Baseline reference | **Recommended Primary Engine** | Potential Phase 10 Extension | Rejected | Rejected |

---

## 4. Engineering Recommendation & Strategic Justification

### Primary Recommendation: Row-Wise Strip Packing with Obstacle Interruption
The **Row-Wise Strip Packing Engine** is selected as the authoritative algorithm for Phase 7 implementation:

1. **Physical Engineering Alignment:**
   - In physical PV installations, panels are commonly mounted onto continuous linear aluminum rails (typically 2 rails per row). Row-wise placement models linear rail collinearity, avoiding isolated, un-rackable geometric placements.
2. **Robust Obstacle Interruption:**
   - When encountering a roof obstacle (e.g. vent pipe or skylight), the engine cleanly splits the row, applies the designated clearance buffer ($B_{\text{obstacle}}$), and continues along the same rail elevation if the remaining horizontal run accommodates $\ge 1$ panel.
3. **Comprehensive Orientation Comparison:**
   - For every roof query, the engine executes two independent deterministic passes:
     - **Pass A:** Pure Portrait arrangement ($W_m \parallel X, L_m \parallel Y$)
     - **Pass B:** Pure Landscape arrangement ($L_m \parallel X, W_m \parallel Y$)
   - The engine compares both layouts, identifies feasibility, and selects the orientation yielding the maximum DC capacity ($P_{\text{DC}}$), while preserving the alternative as a user-accessible comparison.
4. **Explicit Algorithmic Scope & Absence of Global Optimality Guarantee:**
   - **Heuristic Nature:** Row-Wise Strip Packing is an engineering heuristic, not a mathematically provable global optimizer.
   - **Geometrically Feasible Placement (No Global Optimality or Installation Approval Claim):** The engine generates geometrically feasible panel placements under the supplied roof geometry, module dimensions, clearances and obstacle assumptions. These results do not establish structural safety, regulatory compliance or installation approval. The algorithm guarantees compliance with its implemented geometric constraints, but does not guarantee real-world installation feasibility or theoretical global maximum panel count.
   - **Row Starting Position Sensitivity:** Different starting offsets (e.g. bottom-to-top vs. top-to-bottom, left-to-right vs. right-to-left) or staggering shifts may produce different panel counts on roofs with irregular obstacle clusters.
   - **Contract Invariance for Future Upgrades:** Future enhancements (such as multi-start row offset sweeps or hybrid rectangular tiling) can be introduced in subsequent phases without breaking or modifying the Phase 7 JSON contract.
   - **Governed Output Designation:** The result is formally designated as **`BEST_FEASIBLE_CONFIGURATION_FOUND`**.

