"""
SolarSelect — Phase 7: Usable Roof Area and Obstacle Envelope Generator
Computes the usable interior roof boundary after setbacks and constructs expanded
keep-out rectangles for all rooftop obstacles using conservative directional quantization.
"""

from dataclasses import dataclass
from typing import List, Optional
from src.roof_fit.geometry import IntegerRectangle
from src.roof_fit.roof_validator import RoofSpecification, ObstacleSpecification
from src.roof_fit.quantization import (
    quantize_roof_dimension,
    quantize_setback,
    quantize_obstacle_bounds,
    quantize_obstacle_buffer,
    to_geometry_units_floor,
    to_geometry_units_ceil,
    from_geometry_units,
)


@dataclass(frozen=True)
class ExpandedObstacle:
    """An obstacle represented by its exact unbuffered and conservatively expanded integer bounds."""
    obstacle_id: str
    unbuffered_rect: IntegerRectangle
    expanded_rect: IntegerRectangle
    buffer_int: int
    buffer_m: float
    description: str = ""


@dataclass(frozen=True)
class UsableRoofResult:
    """Result of roof boundary and obstacle zone generation."""
    roof_id: str
    gross_rect: IntegerRectangle
    usable_envelope: IntegerRectangle
    expanded_obstacles: List[ExpandedObstacle]
    gross_area_m2: float
    usable_envelope_area_m2: float
    effective_usable_area_estimate_m2: float


class UsableAreaGenerator:
    """Generates discrete usable boundary envelopes and obstacle exclusion zones."""

    @classmethod
    def generate(cls, roof_spec: RoofSpecification) -> UsableRoofResult:
        """
        Converts a validated RoofSpecification into discrete integer usable envelopes
        and outward-expanded obstacle exclusion rectangles.
        """
        l_int = quantize_roof_dimension(roof_spec.length)
        w_int = quantize_roof_dimension(roof_spec.width)
        s_int = quantize_setback(roof_spec.perimeter_setback)

        gross_rect = IntegerRectangle(0, 0, l_int, w_int)
        usable_envelope = IntegerRectangle(s_int, s_int, l_int - s_int, w_int - s_int)

        expanded_obstacles: List[ExpandedObstacle] = []
        for obs in roof_spec.obstacles:
            # Unbuffered integer rectangle: floor origin, ceil extent
            obs_x_min = to_geometry_units_floor(obs.x)
            obs_y_min = to_geometry_units_floor(obs.y)
            obs_x_max = to_geometry_units_ceil(obs.x + obs.width)
            obs_y_max = to_geometry_units_ceil(obs.y + obs.height)
            unbuffered_rect = IntegerRectangle(obs_x_min, obs_y_min, obs_x_max, obs_y_max)

            # Expanded bounds outward with buffer
            exp_x_min, exp_y_min, exp_x_max, exp_y_max = quantize_obstacle_bounds(
                obs.x, obs.y, obs.width, obs.height, obs.buffer
            )
            expanded_rect = IntegerRectangle(exp_x_min, exp_y_min, exp_x_max, exp_y_max)
            buffer_int = quantize_obstacle_buffer(obs.buffer)

            expanded_obstacles.append(
                ExpandedObstacle(
                    obstacle_id=obs.obstacle_id,
                    unbuffered_rect=unbuffered_rect,
                    expanded_rect=expanded_rect,
                    buffer_int=buffer_int,
                    buffer_m=obs.buffer,
                    description=obs.description,
                )
            )

        gross_m2 = from_geometry_units(l_int) * from_geometry_units(w_int)
        usable_m2 = from_geometry_units(usable_envelope.width) * from_geometry_units(usable_envelope.height)

        # Estimate effective usable area subtracting obstacle intersections with usable envelope
        # Note: This is an upper-bound estimate of remaining area without grid discretization
        obs_area_in_usable_int = 0
        for exp_obs in expanded_obstacles:
            isect = usable_envelope.intersection(exp_obs.expanded_rect)
            if isect is not None:
                obs_area_in_usable_int += isect.area

        remaining_area_int = max(0, usable_envelope.area - obs_area_in_usable_int)
        effective_m2 = float(remaining_area_int) / float(10_000 * 10_000)

        return UsableRoofResult(
            roof_id=roof_spec.roof_id,
            gross_rect=gross_rect,
            usable_envelope=usable_envelope,
            expanded_obstacles=expanded_obstacles,
            gross_area_m2=gross_m2,
            usable_envelope_area_m2=usable_m2,
            effective_usable_area_estimate_m2=effective_m2,
        )

