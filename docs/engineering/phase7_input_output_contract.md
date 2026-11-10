# Phase 7: Roof-Fit Engine — Input / Output Contract Specification

**Project:** SolarSelect — An End-to-End MLOps System for AI-Driven Rooftop Solar Selection and Yield Forecasting  
**Phase:** Phase 7 — Roof-Fit and Panel Configuration Engine (Prompt 1: Requirements & Engineering Design)  
**Document Status:** **`DRAFT_CONTRACT_SPECIFICATION`**  
**Related Documents:**
- [`phase7_requirements.md`](phase7_requirements.md)
- [`phase7_architecture.md`](phase7_architecture.md)
- [`phase7_algorithm_comparison.md`](phase7_algorithm_comparison.md)
- [`phase7_testing_strategy.md`](phase7_testing_strategy.md)
- [`../../configs/panels_catalogue.csv`](../../configs/panels_catalogue.csv)

---

## 1. Input Contract: `RoofSpecification`

The input to the Phase 7 Roof-Fit Engine is defined by the `RoofSpecification` schema. All spatial measurements are strictly denominated in **metres (m)**.

### 1.1 JSON Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RoofSpecification",
  "type": "object",
  "required": [
    "roof_id",
    "roof_length_m",
    "roof_width_m",
    "panel_id"
  ],
  "properties": {
    "roof_id": {
      "type": "string",
      "description": "Unique identifier for the roof plane or property site."
    },
    "roof_length_m": {
      "type": "number",
      "minimum": 0.5,
      "description": "Gross roof length along the X-axis (eave-parallel) in metres."
    },
    "roof_width_m": {
      "type": "number",
      "minimum": 0.5,
      "description": "Gross roof width along the Y-axis (ridge-to-gutter) in metres."
    },
    "panel_id": {
      "type": "string",
      "description": "Primary key referencing configs/panels_catalogue.csv (e.g., PNL-CANADIAN-445W)."
    },
    "perimeter_setback_m": {
      "type": "number",
      "minimum": 0.0,
      "default": 0.5,
      "description": "Perimeter boundary setback in metres. Hard physical boundary constraint; cannot be relaxed by numerical tolerance. Not a universal statutory standard; user or site spec must supply applicable clearance. Default 0.50 m is an illustrative simulation default."
    },
    "inter_panel_spacing_m": {
      "type": "number",
      "minimum": 0.005,
      "default": 0.02,
      "description": "Clear lateral spacing between adjacent modules along rails in metres. Hard physical minimum; cannot be relaxed by numerical tolerance. Separate from clamp dimensions. Default 0.02 m (20 mm) is an illustrative simulation default."
    },
    "inter_row_spacing_m": {
      "type": "number",
      "minimum": 0.01,
      "default": 0.05,
      "description": "Clear spacing between panel rows in metres. Hard physical minimum; cannot be relaxed by numerical tolerance. Default 0.05 m (50 mm) is an illustrative racking clearance, NOT a maintenance walkway. Dedicated walkways must be defined as obstacle corridors."
    },
    "allowed_orientations": {
      "type": "string",
      "enum": ["portrait", "landscape", "both"],
      "default": "both",
      "description": "Mounting orientation constraint."
    },
    "obstacles": {
      "type": "array",
      "default": [],
      "description": "List of internal rooftop exclusion zones and dedicated maintenance walkway corridors. Walkway dimensions are configurable test/site inputs, not universal statutory requirements.",
      "items": {
        "type": "object",
        "required": ["obstacle_id", "x_m", "y_m", "width_m", "height_m"],
        "properties": {
          "obstacle_id": { "type": "string" },
          "obstacle_type": { "type": "string", "default": "generic" },
          "x_m": { "type": "number", "minimum": 0.0 },
          "y_m": { "type": "number", "minimum": 0.0 },
          "width_m": { "type": "number", "minimum": 0.05 },
          "height_m": { "type": "number", "minimum": 0.05 },
          "buffer_m": {
            "type": "number",
            "minimum": 0.0,
            "default": 0.20,
            "description": "Additional clearance buffer surrounding obstacle physical bounds in metres. Hard physical clearance; cannot be relaxed by numerical tolerance. Distinct from physical dimensions. Default 0.20 m is an illustrative simulation default."
          }
        }
      }
    }
  }
}
```

### 1.2 Example Input Payload
```json
{
  "roof_id": "RESIDENTIAL-ROOF-001",
  "roof_length_m": 12.0,
  "roof_width_m": 6.5,
  "panel_id": "PNL-CANADIAN-445W",
  "perimeter_setback_m": 0.50,
  "inter_panel_spacing_m": 0.02,
  "inter_row_spacing_m": 0.05,
  "allowed_orientations": "both",
  "obstacles": [
    {
      "obstacle_id": "VENT-PIPE-1",
      "obstacle_type": "plumbing_vent",
      "x_m": 4.5,
      "y_m": 3.0,
      "width_m": 0.30,
      "height_m": 0.30,
      "buffer_m": 0.20
    }
  ]
}
```

### 1.3 Integer Coordinate Domain & Obstacle Expansion Specification
1. **Integer Coordinate Representation:** All continuous inputs are converted to integer units of tenths of a millimetre ($M = 10{,}000\text{ units/m}$, $1\text{ unit} = 0.0001\text{ m} = 0.1\text{ mm}$) referenced to the bottom-left Cartesian origin $(0,0)$ with $+X$ along length/rails and $+Y$ along width/across rows.
2. **Directional Quantization Rules:**
   - Gross roof bounds floor inward: $L_{\text{int}} = \lfloor L \times M \rfloor, W_{\text{int}} = \lfloor W \times M \rfloor$.
   - Setbacks, module dimensions, inter-panel clearances, and inter-row clearances round up (ceil) outward.
3. **Rectangular Obstacle Buffer Expansion:** For obstacle $k$ with bounds $[x, y, w, h]$ and buffer $B_k$, the expanded exclusion rectangle is:
   $$x_{\text{obs,min,int}} = \lfloor x \times M \rfloor - \lceil B_k \times M \rceil$$
   $$y_{\text{obs,min,int}} = \lfloor y \times M \rfloor - \lceil B_k \times M \rceil$$
   $$x_{\text{obs,max,int}} = \lceil (x + w) \times M \rceil + \lceil B_k \times M \rceil$$
   $$y_{\text{obs,max,int}} = \lceil (y + h) \times M \rceil + \lceil B_k \times M \rceil$$
4. **Integer-Domain Placement & Validation:** Candidate panel bounding boxes $[x_{\text{int}}, x_{\text{int}} + w_{\text{int}}] \times [y_{\text{int}}, y_{\text{int}} + h_{\text{int}}]$ are placed and verified strictly in integer units. No floating-point tolerance may permit a setback, clearance, buffer, or non-overlap violation.
5. **Qualified Mathematical Guarantee:** The mathematical feasibility guarantee applies strictly to the defined 2D rectangular geometry under correct inputs and documented rounding rules. Geometric feasibility does not establish structural safety, regulatory compliance, electrical compatibility, or installation approval.

---

## 2. Output Contract: `PanelConfigurationResult`

The engine returns an unambiguous, machine-readable JSON structure detailing the best feasible configuration, spatial metrics, constraint evaluations, and orientation comparisons.

### 2.1 Output Schema Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PanelConfigurationResult",
  "type": "object",
  "required": [
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
    "engine_metadata"
  ],
  "properties": {
    "configuration_id": { "type": "string" },
    "roof_id": { "type": "string" },
    "panel_id": { "type": "string" },
    "panel_model": { "type": "string" },
    "feasibility_status": {
      "type": "string",
      "enum": [
        "FEASIBLE",
        "INFEASIBLE_ROOF_TOO_SMALL",
        "INFEASIBLE_SETBACKS_EXCEED_ROOF",
        "INFEASIBLE_OBSTACLE_COLLISION",
        "CATALOGUE_RECORD_NOT_FOUND",
        "CATALOGUE_DIMENSIONS_MISSING"
      ]
    },
    "selected_orientation": {
      "type": "string",
      "enum": ["portrait", "landscape", "none"]
    },
    "panel_count": { "type": "integer", "minimum": 0 },
    "installed_dc_capacity_kwp": { "type": "number", "minimum": 0.0 },
    "module_stc_power_wp": { "type": "number", "minimum": 0.0 },
    "spatial_metrics": {
      "type": "object",
      "properties": {
        "gross_roof_area_m2": { "type": "number" },
        "perimeter_setback_area_m2": { "type": "number" },
        "obstacle_exclusion_area_m2": { "type": "number" },
        "net_usable_roof_area_m2": { "type": "number" },
        "occupied_panel_area_m2": { "type": "number" },
        "unutilized_usable_area_m2": { "type": "number" },
        "roof_utilization_factor": { "type": "number" },
        "usable_space_packing_efficiency": { "type": "number" }
      }
    },
    "placements": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "panel_index": { "type": "integer" },
          "row_id": { "type": "integer" },
          "col_id": { "type": "integer" },
          "x_m": { "type": "number" },
          "y_m": { "type": "number" },
          "width_m": { "type": "number" },
          "height_m": { "type": "number" },
          "orientation": { "type": "string" }
        }
      }
    },
    "alternatives_evaluated": {
      "type": "object",
      "properties": {
        "portrait": {
          "type": "object",
          "properties": {
            "feasible": { "type": "boolean" },
            "panel_count": { "type": "integer" },
            "dc_capacity_kwp": { "type": "number" }
          }
        },
        "landscape": {
          "type": "object",
          "properties": {
            "feasible": { "type": "boolean" },
            "panel_count": { "type": "integer" },
            "dc_capacity_kwp": { "type": "number" }
          }
        }
      }
    },
    "constraint_violations": {
      "type": "array",
      "items": { "type": "string" }
    },
    "engine_metadata": {
      "type": "object",
      "properties": {
        "algorithm": { "type": "string" },
        "algorithm_selection_rationale": { "type": "string" },
        "optimality_guarantee": { "type": "string" },
        "disclaimer": { "type": "string" },
        "execution_timestamp": { "type": "string" }
      }
    }
  }
}
```

### 2.2 Example Output Payload (Feasible Case)
```json
{
  "configuration_id": "CFG-RESIDENTIAL-001-CANADIAN-445W-PORTRAIT",
  "roof_id": "RESIDENTIAL-ROOF-001",
  "panel_id": "PNL-CANADIAN-445W",
  "panel_model": "HiKu CS3W-445MS",
  "feasibility_status": "FEASIBLE",
  "selected_orientation": "portrait",
  "panel_count": 24,
  "installed_dc_capacity_kwp": 10.680,
  "module_stc_power_wp": 445.0,
  "spatial_metrics": {
    "gross_roof_area_m2": 78.0000,
    "perimeter_setback_area_m2": 17.5000,
    "obstacle_exclusion_area_m2": 0.4900,
    "net_usable_roof_area_m2": 60.0100,
    "occupied_panel_area_m2": 53.0208,
    "unutilized_usable_area_m2": 6.9892,
    "roof_utilization_factor": 0.6798,
    "usable_space_packing_efficiency": 0.8835
  },
  "placements": [
    {
      "panel_index": 1,
      "row_id": 1,
      "col_id": 1,
      "x_m": 0.5000,
      "y_m": 0.5000,
      "width_m": 1.0480,
      "height_m": 2.1080,
      "orientation": "portrait"
    },
    {
      "panel_index": 2,
      "row_id": 1,
      "col_id": 2,
      "x_m": 1.5680,
      "y_m": 0.5000,
      "width_m": 1.0480,
      "height_m": 2.1080,
      "orientation": "portrait"
    }
  ],
  "alternatives_evaluated": {
    "portrait": {
      "feasible": true,
      "panel_count": 24,
      "dc_capacity_kwp": 10.680
    },
    "landscape": {
      "feasible": true,
      "panel_count": 20,
      "dc_capacity_kwp": 8.900
    }
  },
  "constraint_violations": [],
  "engine_metadata": {
    "algorithm": "RowWisePlacementEngine",
    "algorithm_selection_rationale": "Continuous linear racking rail compliance with obstacle interruption",
    "optimality_guarantee": "BEST_FEASIBLE_CONFIGURATION_FOUND",
    "disclaimer": "The engine generates geometrically feasible panel placements under the supplied roof geometry, module dimensions, clearances and obstacle assumptions. These results do not establish structural safety, regulatory compliance or installation approval.",
    "execution_timestamp": "2026-11-10T12:00:00Z"
  }
}
```

---

## 3. Downstream Consumption Contract: Phase 8 Interface

Phase 8 consumes `PanelConfigurationResult` directly. The integration protocol is defined as:

1. **Daily Specific Yield Scaling:**
   $$\text{Daily Energy Generated (kWh/day)} = Y_{f,\text{predicted}} \times P_{\text{DC}}$$
   Where $Y_{f,\text{predicted}}$ is produced by the frozen Phase 5 ExtraTrees model ($\text{kWh}/\text{kW}_p/\text{day}$), and $P_{\text{DC}}$ is the `installed_dc_capacity_kwp` computed by Phase 7.
2. **Multi-Model Comparison:**
   Phase 8 will evaluate all 12 commercial modules in [`configs/panels_catalogue.csv`](../../configs/panels_catalogue.csv) across the target roof, producing 12 candidate `PanelConfigurationResult` objects.
3. **Multi-Criteria Hardware Ranking:**
   Phase 8 ranks the 12 candidate configurations by:
   - Capacity maximization ($P_{\text{DC}}$)
   - Specific energy generation ($\text{kWh}/\text{year}$)
   - Space utilization efficiency ($\text{W}_p/\text{m}^2$)
   - Financial payback and Levelized Cost of Electricity (LCOE), pending quote ingestion under LIM-009.

