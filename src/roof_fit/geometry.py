"""
SolarSelect — Phase 7: Integer Coordinate Geometry Utilities
Provides exact integer rectangle representations, containment, intersection,
and non-overlap calculations for solar panel placement validation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from src.roof_fit.quantization import from_geometry_units


@dataclass(frozen=True)
class IntegerRectangle:
    """
    Immutable axis-aligned 2D rectangle in integer geometry units.
    Coordinates represent boundaries where:
    x_min <= x_max and y_min <= y_max.
    
    GEOMETRIC LIMITATION & SCOPE:
    Clearance metrics horizontal_gap_to() and vertical_gap_to() measure 1D axis-aligned separation
    along the X-axis and Y-axis respectively. These 1D projection gaps do NOT compute general 2D
    Euclidean distance between diagonally offset rectangles (which would be sqrt(dx^2 + dy^2)).
    This implementation exclusively evaluates axis-aligned (orthogonal) clearance constraints.
    """
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def __post_init__(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (self.x_min, self.y_min, self.x_max, self.y_max)):
            raise TypeError("All coordinates of IntegerRectangle must be integer instances (booleans rejected).")
        if self.x_min > self.x_max or self.y_min > self.y_max:
            raise ValueError(
                f"Invalid rectangle bounds: x_min={self.x_min} > x_max={self.x_max} "
                f"or y_min={self.y_min} > y_max={self.y_max}"
            )

    @property
    def width(self) -> int:
        """Width in integer units."""
        return self.x_max - self.x_min

    @property
    def height(self) -> int:
        """Height in integer units."""
        return self.y_max - self.y_min

    @property
    def area(self) -> int:
        """Area in square integer units."""
        return self.width * self.height

    @property
    def is_empty(self) -> bool:
        """True if width or height is zero or negative."""
        return self.width <= 0 or self.height <= 0

    def contains(self, other: "IntegerRectangle") -> bool:
        """
        Returns True if this rectangle completely encloses 'other'.
        Boundary sharing (touching outer edges) is permissible and considered contained.
        """
        return (
            self.x_min <= other.x_min
            and other.x_max <= self.x_max
            and self.y_min <= other.y_min
            and other.y_max <= self.y_max
        )

    def has_positive_area_overlap(self, other: "IntegerRectangle") -> bool:
        """
        Returns True if and only if this rectangle and 'other' share a strictly positive area.
        Rectangles that only touch along edges or at corners have 0-area overlap and return False.
        """
        overlap_width = min(self.x_max, other.x_max) - max(self.x_min, other.x_min)
        overlap_height = min(self.y_max, other.y_max) - max(self.y_min, other.y_min)
        return overlap_width > 0 and overlap_height > 0

    def intersection(self, other: "IntegerRectangle") -> Optional["IntegerRectangle"]:
        """
        Returns the intersection rectangle if there is strictly positive area overlap,
        otherwise None.
        """
        ix_min = max(self.x_min, other.x_min)
        iy_min = max(self.y_min, other.y_min)
        ix_max = min(self.x_max, other.x_max)
        iy_max = min(self.y_max, other.y_max)

        if ix_min < ix_max and iy_min < iy_max:
            return IntegerRectangle(ix_min, iy_min, ix_max, iy_max)
        return None

    def expanded(self, buffer_int: int) -> "IntegerRectangle":
        """Returns a new IntegerRectangle expanded outward by buffer_int in all 4 directions."""
        if buffer_int < 0:
            raise ValueError(f"Expansion buffer cannot be negative, got {buffer_int}")
        return IntegerRectangle(
            x_min=self.x_min - buffer_int,
            y_min=self.y_min - buffer_int,
            x_max=self.x_max + buffer_int,
            y_max=self.y_max + buffer_int,
        )

    def horizontal_gap_to(self, other: "IntegerRectangle") -> int:
        """
        Computes the clearance gap along the x-axis between self and other.
        If self is to the left of other (self.x_max <= other.x_min), gap = other.x_min - self.x_max.
        If other is to the left of self (other.x_max <= self.x_min), gap = self.x_min - other.x_max.
        If they overlap along x, returns a negative value representing penetration.
        """
        if self.x_max <= other.x_min:
            return other.x_min - self.x_max
        if other.x_max <= self.x_min:
            return self.x_min - other.x_max
        # Overlapping along x
        return -min(self.x_max - other.x_min, other.x_max - self.x_min)

    def vertical_gap_to(self, other: "IntegerRectangle") -> int:
        """
        Computes the clearance gap along the y-axis between self and other.
        If self is below other (self.y_max <= other.y_min), gap = other.y_min - self.y_max.
        If other is below self (other.y_max <= self.y_min), gap = self.y_min - other.y_max.
        If they overlap along y, returns a negative value representing penetration.
        """
        if self.y_max <= other.y_min:
            return other.y_min - self.y_max
        if other.y_max <= self.y_min:
            return self.y_min - other.y_max
        # Overlapping along y
        return -min(self.y_max - other.y_min, other.y_max - self.y_min)

    def to_metres_dict(self) -> Dict[str, float]:
        """Converts integer bounds to floating-point metres dictionary."""
        return {
            "x_min": from_geometry_units(self.x_min),
            "y_min": from_geometry_units(self.y_min),
            "x_max": from_geometry_units(self.x_max),
            "y_max": from_geometry_units(self.y_max),
            "width": from_geometry_units(self.width),
            "height": from_geometry_units(self.height),
            "area_m2": from_geometry_units(self.width) * from_geometry_units(self.height),
        }

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Returns (x_min, y_min, x_max, y_max)."""
        return (self.x_min, self.y_min, self.x_max, self.y_max)

