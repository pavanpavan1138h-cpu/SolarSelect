"""
SolarSelect — Phase 7: Roof-Fit and Panel Configuration Engine
Foundational Geometry & Physical Validation Layer
"""

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
from src.roof_fit.geometry import (
    IntegerRectangle,
)
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
from src.roof_fit.placement_engine import (
    PanelPlacement,
    OrientationCandidateResult,
    PanelConfigurationResult,
    RowWisePlacementEngine,
)
from src.roof_fit.serializer import (
    LayoutSerializer,
)
from src.roof_fit.engine import (
    RoofFitEngine,
)

__all__ = [
    # Exceptions
    "RoofFitError",
    "InvalidRoofSpecificationError",
    "MissingRoofParameterError",
    "InvalidObstacleSpecificationError",
    "CatalogueError",
    "PanelNotFoundError",
    "MissingPanelDimensionError",
    "InvalidPanelDimensionError",
    "QuantizationError",
    "ConstraintViolationError",
    "BoundaryContainmentError",
    "ObstacleCollisionError",
    "PanelOverlapError",
    "ClearanceViolationError",
    # Quantization
    "SCALE_FACTOR",
    "to_geometry_units_floor",
    "to_geometry_units_ceil",
    "from_geometry_units",
    "quantize_roof_dimension",
    "quantize_setback",
    "quantize_panel_dimension_m",
    "quantize_panel_dimension_mm",
    "quantize_clearance",
    "quantize_obstacle_buffer",
    "quantize_obstacle_bounds",
    # Geometry
    "IntegerRectangle",
    # Roof validator
    "ObstacleSpecification",
    "RoofSpecification",
    "RoofSpecificationValidator",
    # Catalogue adapter
    "PanelDimensionSpec",
    "CatalogueAdapter",
    # Usable area
    "ExpandedObstacle",
    "UsableRoofResult",
    "UsableAreaGenerator",
    # Constraint validator
    "ConstraintViolation",
    "PlacementValidationResult",
    "ConstraintValidator",
    # Placement engine & Serializer
    "PanelPlacement",
    "OrientationCandidateResult",
    "PanelConfigurationResult",
    "RowWisePlacementEngine",
    "LayoutSerializer",
    # Public integration workflow engine
    "RoofFitEngine",
]

