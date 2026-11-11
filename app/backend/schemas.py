"""
SolarSelect — Phase 9 Pydantic Boundary Schemas
Defines clean API/Service contract structures aligned with Phase 7 and Phase 8.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ObstacleInputSchema(BaseModel):
    obstacle_id: str = Field(..., description="Unique obstacle identifier")
    x: float = Field(..., ge=0.0, description="Bottom-left X coordinate (m)")
    y: float = Field(..., ge=0.0, description="Bottom-left Y coordinate (m)")
    width: float = Field(..., gt=0.0, description="Width along eave axis (m)")
    height: float = Field(..., gt=0.0, description="Height along slope axis (m)")
    buffer: float = Field(0.0, ge=0.0, description="Keep-out clearance buffer (m)")


class RoofConfigurationRequestSchema(BaseModel):
    roof_id: str = Field(..., min_length=1, description="Roof identifier")
    length: float = Field(..., gt=0.0, description="Roof length along eave axis (m)")
    width: float = Field(..., gt=0.0, description="Roof width along slope axis (m)")
    perimeter_setback: float = Field(0.5, ge=0.0, description="Edge safety setback (m)")
    panel_id: str = Field(..., description="Target Phase 6 panel identifier")
    orientation_override: Optional[str] = Field(
        None, description="Optional forced orientation ('portrait', 'landscape', or None for auto)"
    )
    inter_panel_clearance: float = Field(0.02, ge=0.0, description="Horizontal gap between modules (m)")
    inter_row_clearance: float = Field(0.5, ge=0.0, description="Vertical walkway/row gap (m)")
    obstacles: List[ObstacleInputSchema] = Field(default_factory=list)


class SystemStatusSchema(BaseModel):
    platform_name: str
    version: str
    layer_a_forecasting: Dict[str, Any]
    layer_b_hardware: Dict[str, Any]
    layer_b_geometry: Dict[str, Any]
    layer_b_economics: Dict[str, Any]

