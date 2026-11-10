"""
SolarSelect — Phase 7: Roof Specification Validator
Validates gross roof dimensions, setbacks, clearances, and obstacle definitions.
Enforces physical plausibility, non-negativity, and boundary constraints.
"""

from dataclasses import dataclass, field
import math
from typing import List, Dict, Any, Union
from src.roof_fit.exceptions import (
    InvalidRoofSpecificationError,
    MissingRoofParameterError,
    InvalidObstacleSpecificationError,
)
from src.roof_fit.quantization import quantize_roof_dimension, quantize_setback


@dataclass(frozen=True)
class ObstacleSpecification:
    """Specification for a rectangular rooftop obstacle and its keep-out zone."""
    obstacle_id: str
    x: float
    y: float
    width: float
    height: float
    buffer: float = 0.0
    description: str = ""

    def __post_init__(self) -> None:
        if not self.obstacle_id or not isinstance(self.obstacle_id, str):
            raise InvalidObstacleSpecificationError("obstacle_id must be a non-empty string.")


@dataclass(frozen=True)
class RoofSpecification:
    """Specification for a rooftop installation envelope."""
    roof_id: str
    length: float
    width: float
    perimeter_setback: float
    azimuth_deg: float = 180.0
    tilt_deg: float = 0.0
    obstacles: List[ObstacleSpecification] = field(default_factory=list)
    clamping_gap: float = 0.020
    walkway_gap: float = 0.050
    allowed_orientations: str = "both"


class RoofSpecificationValidator:
    """Validates roof specifications and obstacles against geometric and physical constraints."""

    @staticmethod
    def _validate_finite_number(val: Any, param_name: str, strictly_positive: bool = False, non_negative: bool = False) -> float:
        """Validates that a parameter is a finite numeric value satisfying sign constraints."""
        if val is None:
            raise MissingRoofParameterError(f"Missing required parameter: '{param_name}'")
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise InvalidRoofSpecificationError(f"Parameter '{param_name}' must be numeric, got {type(val).__name__}")
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            raise InvalidRoofSpecificationError(f"Parameter '{param_name}' must be a finite number, got {f_val}")
        if strictly_positive and f_val <= 0.0:
            raise InvalidRoofSpecificationError(f"Parameter '{param_name}' must be strictly positive (> 0), got {f_val}")
        if non_negative and f_val < 0.0:
            raise InvalidRoofSpecificationError(f"Parameter '{param_name}' cannot be negative (>= 0), got {f_val}")
        return f_val

    @classmethod
    def validate_obstacle(cls, obs_data: Union[ObstacleSpecification, Dict[str, Any]], roof_length: float, roof_width: float) -> ObstacleSpecification:
        """Validates an obstacle specification against gross roof boundaries."""
        if isinstance(obs_data, ObstacleSpecification):
            obs_id = obs_data.obstacle_id
            x = obs_data.x
            y = obs_data.y
            width = obs_data.width
            height = obs_data.height
            buffer = obs_data.buffer
            description = obs_data.description
        elif isinstance(obs_data, dict):
            if "obstacle_id" not in obs_data or not obs_data["obstacle_id"]:
                raise InvalidObstacleSpecificationError("Obstacle dictionary missing valid 'obstacle_id'")
            obs_id = str(obs_data["obstacle_id"])
            x = obs_data.get("x") if "x" in obs_data else obs_data.get("x_m")
            y = obs_data.get("y") if "y" in obs_data else obs_data.get("y_m")
            width = obs_data.get("width") if "width" in obs_data else obs_data.get("width_m")
            height = obs_data.get("height") if "height" in obs_data else obs_data.get("height_m")
            buffer = obs_data.get("buffer") if "buffer" in obs_data else obs_data.get("buffer_m", 0.0)
            description = str(obs_data.get("description", obs_data.get("obstacle_type", "")))
        else:
            raise InvalidObstacleSpecificationError(f"Invalid obstacle type: {type(obs_data)}")

        if not obs_id or not obs_id.strip():
            raise InvalidObstacleSpecificationError("obstacle_id cannot be blank.")

        try:
            x_f = cls._validate_finite_number(x, f"obstacle '{obs_id}' x", non_negative=True)
            y_f = cls._validate_finite_number(y, f"obstacle '{obs_id}' y", non_negative=True)
            w_f = cls._validate_finite_number(width, f"obstacle '{obs_id}' width", strictly_positive=True)
            h_f = cls._validate_finite_number(height, f"obstacle '{obs_id}' height", strictly_positive=True)
            b_f = cls._validate_finite_number(buffer, f"obstacle '{obs_id}' buffer", non_negative=True)
        except InvalidRoofSpecificationError as e:
            raise InvalidObstacleSpecificationError(str(e)) from e
        except MissingRoofParameterError as e:
            raise InvalidObstacleSpecificationError(str(e)) from e

        # Obstacle physical boundary must not exceed gross roof canvas
        if x_f + w_f > roof_length:
            raise InvalidObstacleSpecificationError(
                f"Obstacle '{obs_id}' x-extent ({x_f + w_f:.4f}m) exceeds roof length ({roof_length:.4f}m)"
            )
        if y_f + h_f > roof_width:
            raise InvalidObstacleSpecificationError(
                f"Obstacle '{obs_id}' y-extent ({y_f + h_f:.4f}m) exceeds roof width ({roof_width:.4f}m)"
            )

        return ObstacleSpecification(
            obstacle_id=obs_id.strip(),
            x=x_f,
            y=y_f,
            width=w_f,
            height=h_f,
            buffer=b_f,
            description=description,
        )

    @classmethod
    def validate(cls, spec_data: Union[RoofSpecification, Dict[str, Any]]) -> RoofSpecification:
        """
        Validates a complete roof specification, ensuring positive usable space and valid obstacles.
        """
        if isinstance(spec_data, RoofSpecification):
            roof_id = spec_data.roof_id
            length = spec_data.length
            width = spec_data.width
            setback = spec_data.perimeter_setback
            azimuth = spec_data.azimuth_deg
            tilt = spec_data.tilt_deg
            obstacles_raw = spec_data.obstacles
            clamping_gap = spec_data.clamping_gap
            walkway_gap = spec_data.walkway_gap
            allowed_orientations = spec_data.allowed_orientations
        elif isinstance(spec_data, dict):
            if "roof_id" not in spec_data or not spec_data["roof_id"]:
                raise MissingRoofParameterError("Missing required parameter: 'roof_id'")
            roof_id = str(spec_data["roof_id"])
            length = spec_data.get("length") if "length" in spec_data else spec_data.get("roof_length_m")
            width = spec_data.get("width") if "width" in spec_data else spec_data.get("roof_width_m")
            setback = spec_data.get("perimeter_setback") if "perimeter_setback" in spec_data else spec_data.get("perimeter_setback_m")
            azimuth = spec_data.get("azimuth_deg", 180.0)
            tilt = spec_data.get("tilt_deg", 0.0)
            obstacles_raw = spec_data.get("obstacles", [])
            clamping_gap = spec_data.get("clamping_gap") if "clamping_gap" in spec_data else spec_data.get("inter_panel_spacing_m", 0.020)
            walkway_gap = spec_data.get("walkway_gap") if "walkway_gap" in spec_data else spec_data.get("inter_row_spacing_m", 0.050)
            allowed_orientations = spec_data.get("allowed_orientations", "both")
        else:
            raise InvalidRoofSpecificationError(f"Unsupported specification data type: {type(spec_data)}")

        if not roof_id or not roof_id.strip():
            raise InvalidRoofSpecificationError("roof_id cannot be empty.")

        if allowed_orientations not in ("portrait", "landscape", "both"):
            raise InvalidRoofSpecificationError(
                f"allowed_orientations must be 'portrait', 'landscape', or 'both', got '{allowed_orientations}'"
            )

        length_f = cls._validate_finite_number(length, "length", strictly_positive=True)
        width_f = cls._validate_finite_number(width, "width", strictly_positive=True)
        setback_f = cls._validate_finite_number(setback, "perimeter_setback", non_negative=True)
        clamping_gap_f = cls._validate_finite_number(clamping_gap, "clamping_gap", non_negative=True)
        walkway_gap_f = cls._validate_finite_number(walkway_gap, "walkway_gap", non_negative=True)

        azimuth_f = cls._validate_finite_number(azimuth, "azimuth_deg")
        if not (0.0 <= azimuth_f <= 360.0):
            raise InvalidRoofSpecificationError(f"azimuth_deg must be in [0, 360], got {azimuth_f}")

        tilt_f = cls._validate_finite_number(tilt, "tilt_deg")
        if not (0.0 <= tilt_f <= 90.0):
            raise InvalidRoofSpecificationError(f"tilt_deg must be in [0, 90], got {tilt_f}")

        # Integer quantization check: ensure usable roof envelope has positive dimensions
        length_int = quantize_roof_dimension(length_f)
        width_int = quantize_roof_dimension(width_f)
        setback_int = quantize_setback(setback_f)

        usable_length_int = length_int - 2 * setback_int
        usable_width_int = width_int - 2 * setback_int

        if usable_length_int <= 0 or usable_width_int <= 0:
            raise InvalidRoofSpecificationError(
                f"Perimeter setback ({setback_f}m) consumes entire roof dimensions "
                f"({length_f}m x {width_f}m). Usable interior length={usable_length_int}, width={usable_width_int}."
            )

        if not isinstance(obstacles_raw, list):
            raise InvalidObstacleSpecificationError("obstacles must be provided as a list.")

        validated_obstacles: List[ObstacleSpecification] = []
        seen_ids = set()
        for obs in obstacles_raw:
            val_obs = cls.validate_obstacle(obs, roof_length=length_f, roof_width=width_f)
            if val_obs.obstacle_id in seen_ids:
                raise InvalidObstacleSpecificationError(f"Duplicate obstacle_id found: '{val_obs.obstacle_id}'")
            seen_ids.add(val_obs.obstacle_id)
            validated_obstacles.append(val_obs)

        return RoofSpecification(
            roof_id=roof_id.strip(),
            length=length_f,
            width=width_f,
            perimeter_setback=setback_f,
            azimuth_deg=azimuth_f,
            tilt_deg=tilt_f,
            obstacles=validated_obstacles,
            clamping_gap=clamping_gap_f,
            walkway_gap=walkway_gap_f,
            allowed_orientations=allowed_orientations,
        )

