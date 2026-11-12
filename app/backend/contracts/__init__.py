"""Version 1 HTTP contracts, independent of the existing Streamlit schemas."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.energy_economics.types import ModelVariant

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Positive = Annotated[Number, Field(gt=0)]
NonNegative = Annotated[Number, Field(ge=0)]

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

class HistoricalFeatures(Contract):
    kWp: Positive
    lat: Annotated[Number, Field(ge=-90, le=90)]
    Lon: Annotated[Number, Field(ge=-180, le=180)]
    day_of_year: Annotated[Number, Field(ge=1, le=366)]
    month: Annotated[Number, Field(ge=1, le=12)]
    day_of_week: Annotated[Number, Field(ge=0, le=6)]
    is_weekend: Annotated[Number, Field(ge=0, le=1)]
    sin_doy: Number
    cos_doy: Number
    sin_month: Number
    cos_month: Number
    solar_declination_deg: Number
    solar_noon_elevation_deg: Number
    solar_noon_zenith_deg: Number
    daylight_hours: Number
    extraterrestrial_radiation_h0: Number
    has_valid_lag1: Annotated[Number, Field(ge=0, le=1)]
    lag1_daily_yield: Number
    lag2_daily_yield: Number
    lag7_daily_yield: Number
    rolling_mean_7d_yield: Number
    rolling_std_7d_yield: Number
    rolling_mean_14d_yield: Number
    rolling_mean_30d_yield: Number
    lag1_temp_mean: Number
    lag1_temp_max: Number
    lag1_temp_min: Number
    lag1_temp_range: Number
    lag1_rh_mean: Number

    @model_validator(mode="after")
    def calendar_indicators(self):
        for name in ("day_of_year", "month", "day_of_week", "is_weekend", "has_valid_lag1"):
            if not getattr(self, name).is_integer():
                raise ValueError(f"{name} must be an integer-valued number")
        if self.is_weekend != int(self.day_of_week >= 5):
            raise ValueError("is_weekend must agree with day_of_week (Monday=0)")
        # No year supplied: permit either leap/non-leap calendar; never transform inputs.
        starts = (1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335)
        lengths = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        m = int(self.month) - 1
        lo = starts[m]
        hi = min(366, starts[m] + lengths[m] - 1 + (1 if m >= 2 else 0))
        if not lo <= self.day_of_year <= hi:
            raise ValueError("month and day_of_year disagree in both leap and non-leap calendars")
        return self

class HistoricalRequest(Contract):
    scenario: Literal["historical_site_day"]
    features: HistoricalFeatures
    model_variant: ModelVariant = ModelVariant.PRIMARY_EXTRA_TREES

class ProspectiveRequest(Contract):
    scenario: Literal["prospective_roof"]
    roof_id: str = Field(min_length=1, max_length=128)

PredictionRequest = Annotated[HistoricalRequest | ProspectiveRequest, Field(discriminator="scenario")]

class BatchRequest(Contract):
    rows: list[HistoricalRequest] = Field(min_length=1, max_length=100, description="All-or-nothing validation; errors locate rows by zero-based index.")

class PredictionResult(Contract):
    predicted_specific_yield_kwh_per_kwp_day: Number
    prediction_status: Literal["PREDICTION_AVAILABLE", "NEGATIVE_PREDICTION_WARNING"]
    energy_basis: Literal["UNVERIFIED_ASSUMED_AC"] = "UNVERIFIED_ASSUMED_AC"
    model: dict
    request_id: str
    limitations: list[dict]

class BatchResult(Contract):
    results: list[PredictionResult]
    request_id: str

class Obstacle(Contract):
    obstacle_id: str = Field(min_length=1, max_length=128)
    x: NonNegative
    y: NonNegative
    width: Positive
    height: Positive
    buffer: NonNegative = 0
    description: str = Field(default="", max_length=512)

class RoofRequest(Contract):
    roof_id: str = Field(min_length=1, max_length=128)
    length: Annotated[Positive, Field(le=200, description="Metres; HTTP workload limit 200 m per side")]
    width: Annotated[Positive, Field(le=200)]
    perimeter_setback: NonNegative = 0.5
    panel_id: str = Field(min_length=1, max_length=128)
    orientation_override: Literal["portrait", "landscape", "both"] | None = None
    inter_panel_clearance: NonNegative = 0.02
    inter_row_clearance: NonNegative = 0.5
    azimuth_deg: Annotated[Number, Field(ge=0, le=360)] = 180
    tilt_deg: Annotated[Number, Field(ge=0, le=90)] = 0
    obstacles: list[Obstacle] = Field(default_factory=list, max_length=100)

class RoofResult(Contract):
    layout: dict
    approval_scope: str = "Geometric feasibility only; no structural or electrical approval."
    recommendation_status: str = "RECOMMENDATION_NOT_EVALUATED"
    electrical_status: str = "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS"
    request_id: str
