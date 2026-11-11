"""
SolarSelect — Phase 8: Energy, Economics and Recommendation Engine
Exceptions module for Phase 8 Foundation and Integration Layer.
"""


class Phase8Error(Exception):
    """Base exception for all Phase 8 errors."""
    pass


class Phase7IntegrationError(Phase8Error):
    """Raised when Phase 7 output cannot be validated or ingested."""
    pass


class CatalogueIntegrationError(Phase8Error):
    """Raised when Phase 6 catalogue data cannot be loaded, parsed, or verified."""
    pass


class PanelNotFoundError(CatalogueIntegrationError):
    """Raised when a referenced panel_id does not exist in the catalogue."""
    pass


class CapacityEvaluationError(Phase8Error):
    """Raised when candidate capacity evaluation fails due to invalid input or distribution data."""
    pass


class FeasibilityEvaluationError(Phase8Error):
    """Raised when candidate feasibility evaluation encounters an unrecoverable failure."""
    pass


class Phase5InferenceError(Phase8Error):
    """Raised when Phase 5 model loading, validation, or inference fails."""
    pass


class FeatureValidationError(Phase5InferenceError):
    """Raised when input features fail schema, presence, or numerical validity checks."""
    pass


class HistoricalReplayError(Phase8Error):
    """Raised when historical replay dataset validation, ordering, or calculation fails."""
    pass


class EnergyEstimationError(Phase8Error):
    """Raised when Stage 3 energy estimation encounters invalid input, arithmetic failure, or non-finite values."""
    pass


class ScenarioValidationError(EnergyEstimationError):
    """Raised when scenario inputs violate scenario contracts or fail validation."""
    pass


class AnnualizationError(Phase8Error):
    """Raised when annualization evaluation violates temporal, coverage, or calculation constraints."""
    pass


class DegradationError(Phase8Error):
    """Raised when degradation modeling encounters invalid parameters or physics violations."""
    pass


class InvalidDegradationInputError(DegradationError, ValueError):
    """Raised when degradation rate, lifetime duration, or model parameters are out of valid bounds."""
    pass


class FinancialError(Phase8Error):
    """Base exception for Stage 7 financial evaluation errors."""
    pass


class CostStructureError(FinancialError):
    """Raised when system cost components or aggregation violates cost contracts."""
    pass


class CurrencyMismatchError(CostStructureError, ValueError):
    """Raised when cost items carry mismatched currencies without an authoritative conversion rate."""
    pass


class InvalidFinancialInputError(FinancialError, ValueError):
    """Raised when financial parameters, discount rates, or cash flow inputs are invalid."""
    pass


class ElectricalError(Phase8Error):
    """Base exception for Stage 8 electrical and inverter compatibility errors."""
    pass


class ElectricalConfigurationError(ElectricalError, ValueError):
    """Raised when string sizing, inverter inputs, or temperature parameters violate electrical contracts."""
    pass


class RankingError(Phase8Error):
    """Raised when Pareto or weighted ranking encounters invalid objectives, weights, or dimensions."""
    pass


class RecommendationError(Phase8Error):
    """Raised when recommendation formulation fails due to invalid candidate contracts or contradictory states."""
    pass





