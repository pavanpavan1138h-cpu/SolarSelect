"""
SolarSelect — Phase 7: Integer Geometry Quantization
Provides directional conservative conversion between continuous metric coordinates
and discrete integer geometry units (scale factor M = 10,000 units/m, 1 unit = 0.1 mm).
"""

from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, InvalidOperation
import math
from typing import Union, Tuple
from src.roof_fit.exceptions import QuantizationError

# Scale factor: 10,000 integer units per metre (1 unit = 0.0001 m = 0.1 mm)
SCALE_FACTOR: int = 10_000
SCALE_DECIMAL: Decimal = Decimal(str(SCALE_FACTOR))


def _to_decimal(val: Union[float, int, str, Decimal]) -> Decimal:
    """
    Safely converts an input numeric value to Decimal, rejecting non-finite values and booleans.
    
    Deterministic Float Policy:
    When a Python float is provided, it is converted via Decimal(str(val)). In Python 3, str(float)
    produces the shortest deterministic decimal representation that rounds back to the same float
    (e.g., str(0.02) -> '0.02' -> Decimal('0.02')), avoiding binary floating-point representation
    drift (e.g. Decimal(0.02) -> Decimal('0.020000000000000000416...')).
    """
    if val is None:
        raise QuantizationError("Cannot quantize None value.")
    if isinstance(val, bool):
        raise QuantizationError(f"Boolean value {val} cannot be quantized as a numeric coordinate.")
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise QuantizationError(f"Cannot quantize non-finite float: {val}")
        return Decimal(str(val))
    if isinstance(val, (int, str)):
        try:
            d = Decimal(str(val))
            if not d.is_finite():
                raise QuantizationError(f"Value is not finite: {val}")
            return d
        except InvalidOperation as e:
            raise QuantizationError(f"Invalid decimal string: {val}") from e
    if isinstance(val, Decimal):
        if not val.is_finite():
            raise QuantizationError(f"Decimal is not finite: {val}")
        return val
    raise QuantizationError(f"Unsupported type for quantization: {type(val)}")


def to_geometry_units_floor(val: Union[float, int, str, Decimal]) -> int:
    """
    Quantizes a continuous value (in metres) to integer units using floor (downward).
    Used for roof outer dimensions and obstacle minimum coordinates.
    """
    d = _to_decimal(val)
    units = d * SCALE_DECIMAL
    return int(units.to_integral_value(rounding=ROUND_FLOOR))


def to_geometry_units_ceil(val: Union[float, int, str, Decimal]) -> int:
    """
    Quantizes a continuous value (in metres) to integer units using ceiling (upward).
    Used for setbacks, module dimensions, clearances, buffers, and obstacle maximum coordinates.
    """
    d = _to_decimal(val)
    units = d * SCALE_DECIMAL
    return int(units.to_integral_value(rounding=ROUND_CEILING))


def from_geometry_units(val_int: int) -> float:
    """Converts integer geometry units back to metres as a float."""
    if not isinstance(val_int, int):
        raise QuantizationError(f"Expected int, got {type(val_int)}")
    return float(val_int) / float(SCALE_FACTOR)


def quantize_roof_dimension(val_m: Union[float, int, str, Decimal]) -> int:
    """Floor quantization for gross roof dimensions in metres (underestimate available roof)."""
    val_int = to_geometry_units_floor(val_m)
    if val_int <= 0:
        raise QuantizationError(f"Quantized roof dimension must be strictly positive, got {val_int}")
    return val_int


def quantize_setback(val_m: Union[float, int, str, Decimal]) -> int:
    """Ceiling quantization for perimeter setback in metres (overestimate boundary clearance)."""
    val_int = to_geometry_units_ceil(val_m)
    if val_int < 0:
        raise QuantizationError(f"Quantized setback cannot be negative, got {val_int}")
    return val_int


def quantize_panel_dimension_m(val_m: Union[float, int, str, Decimal]) -> int:
    """Ceiling quantization for panel dimensions in metres (overestimate physical extent)."""
    val_int = to_geometry_units_ceil(val_m)
    if val_int <= 0:
        raise QuantizationError(f"Quantized panel dimension must be strictly positive, got {val_int}")
    return val_int


def quantize_panel_dimension_mm(val_mm: Union[float, int, str, Decimal]) -> int:
    """
    Ceiling quantization for panel dimensions given in millimetres.
    1 mm = 10 integer units (since 1 unit = 0.1 mm = 0.0001 m).
    """
    d = _to_decimal(val_mm)
    # 1 mm = 0.001 m -> val_mm / 1000 * 10000 = val_mm * 10
    units = d * Decimal("10")
    val_int = int(units.to_integral_value(rounding=ROUND_CEILING))
    if val_int <= 0:
        raise QuantizationError(f"Quantized panel dimension must be strictly positive, got {val_int}")
    return val_int


def quantize_clearance(val_m: Union[float, int, str, Decimal]) -> int:
    """Ceiling quantization for clearances (inter-panel gap, inter-row walkway gap)."""
    val_int = to_geometry_units_ceil(val_m)
    if val_int < 0:
        raise QuantizationError(f"Quantized clearance cannot be negative, got {val_int}")
    return val_int


def quantize_obstacle_buffer(val_m: Union[float, int, str, Decimal]) -> int:
    """Ceiling quantization for obstacle safety buffer in metres."""
    val_int = to_geometry_units_ceil(val_m)
    if val_int < 0:
        raise QuantizationError(f"Quantized obstacle buffer cannot be negative, got {val_int}")
    return val_int


def quantize_obstacle_bounds(
    x: Union[float, int, str, Decimal],
    y: Union[float, int, str, Decimal],
    width: Union[float, int, str, Decimal],
    height: Union[float, int, str, Decimal],
    buffer: Union[float, int, str, Decimal] = 0.0,
) -> Tuple[int, int, int, int]:
    """
    Directionally quantizes obstacle bounds outward, including buffer:
    x_min = floor(x * M) - ceil(buffer * M)
    y_min = floor(y * M) - ceil(buffer * M)
    x_max = ceil((x + width) * M) + ceil(buffer * M)
    y_max = ceil((y + height) * M) + ceil(buffer * M)
    """
    x_d = _to_decimal(x)
    y_d = _to_decimal(y)
    w_d = _to_decimal(width)
    h_d = _to_decimal(height)
    b_d = _to_decimal(buffer)

    if w_d <= 0 or h_d <= 0:
        raise QuantizationError(f"Obstacle width and height must be strictly positive, got w={w_d}, h={h_d}")
    if b_d < 0:
        raise QuantizationError(f"Obstacle buffer cannot be negative, got {b_d}")

    b_units = int((b_d * SCALE_DECIMAL).to_integral_value(rounding=ROUND_CEILING))
    
    x_min_units = int((x_d * SCALE_DECIMAL).to_integral_value(rounding=ROUND_FLOOR)) - b_units
    y_min_units = int((y_d * SCALE_DECIMAL).to_integral_value(rounding=ROUND_FLOOR)) - b_units
    
    x_max_units = int(((x_d + w_d) * SCALE_DECIMAL).to_integral_value(rounding=ROUND_CEILING)) + b_units
    y_max_units = int(((y_d + h_d) * SCALE_DECIMAL).to_integral_value(rounding=ROUND_CEILING)) + b_units

    return (x_min_units, y_min_units, x_max_units, y_max_units)

