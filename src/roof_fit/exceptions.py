"""
SolarSelect — Phase 7: Roof-Fit Engine Domain Exceptions
Defines specific, actionable domain exceptions for roof validation, catalogue adaptation,
quantization, and physical constraint violations.
"""


class RoofFitError(Exception):
    """Base exception for all Phase 7 Roof-Fit Engine errors."""
    pass


class InvalidRoofSpecificationError(RoofFitError):
    """Raised when a roof specification contains invalid dimensions, units, or parameters."""
    pass


class MissingRoofParameterError(InvalidRoofSpecificationError):
    """Raised when a mandatory roof parameter is missing."""
    pass


class InvalidObstacleSpecificationError(InvalidRoofSpecificationError):
    """Raised when an obstacle definition is malformed, non-positive, or outside bounds."""
    pass


class CatalogueError(RoofFitError):
    """Base exception for catalogue adapter operations."""
    pass


class PanelNotFoundError(CatalogueError):
    """Raised when a requested panel_id does not exist in the catalogue."""
    pass


class MissingPanelDimensionError(CatalogueError):
    """Raised when a catalogue record lacks required physical dimensions (length_mm, width_mm)."""
    pass


class InvalidPanelDimensionError(CatalogueError):
    """Raised when physical dimensions in catalogue are non-positive or non-finite."""
    pass


class QuantizationError(RoofFitError):
    """Raised when continuous values cannot be safely converted to integer geometry units."""
    pass


class ConstraintViolationError(RoofFitError):
    """Base exception raised when a geometric candidate violates physical invariants."""
    pass


class BoundaryContainmentError(ConstraintViolationError):
    """Raised when a panel protrudes beyond the permissible usable roof envelope."""
    pass


class ObstacleCollisionError(ConstraintViolationError):
    """Raised when a panel penetrates a buffered obstacle exclusion zone."""
    pass


class PanelOverlapError(ConstraintViolationError):
    """Raised when two panel rectangles have positive-area overlap."""
    pass


class ClearanceViolationError(ConstraintViolationError):
    """Raised when inter-panel or inter-row clearance is strictly below configured minimum."""
    pass

