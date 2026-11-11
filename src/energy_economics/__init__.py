"""
SolarSelect — Phase 8: Energy, Economics and Recommendation Engine
Package initialization and public exports.
"""

from src.energy_economics.exceptions import (
    Phase8Error,
    Phase7IntegrationError,
    CatalogueIntegrationError,
    PanelNotFoundError,
    CapacityEvaluationError,
    FeasibilityEvaluationError,
    Phase5InferenceError,
    FeatureValidationError,
    HistoricalReplayError,
    EnergyEstimationError,
    ScenarioValidationError,
    AnnualizationError,
    DegradationError,
    InvalidDegradationInputError,
    FinancialError,
    CostStructureError,
    CurrencyMismatchError,
    InvalidFinancialInputError,
    ElectricalError,
    ElectricalConfigurationError,
    RankingError,
    RecommendationError,
)
from src.energy_economics.types import (
    CapacitySupportStatus,
    CapacityEligibility,
    OverallRecommendationEligibility,
    GeometricFeasibility,
    CatalogueValidity,
    PredictionAvailability,
    ElectricalCompatibility,
    EconomicFeasibility,
    TrainingDistributionMetrics,
    CapacitySupportResult,
    FeasibilityResult,
    ReplaySampleClassification,
    ModelVariant,
    HistoricalYearStatus,
    EnergyScenarioType,
    ScenarioEvaluationStatus,
    DailyEnergyEstimate,
    SiteEnergySummary,
    EnergyAggregationSummary,
    AnnualizationMethod,
    AnnualEvidenceStatus,
    AnnualEnergyResult,
    LifetimeEnergyBaseline,
    DegradationModel,
    DegradationSource,
    YearlyDegradationRecord,
    DegradationResult,
    CostCategory,
    LCOECapexBasis,
    RateBasis,
    PaybackStatus,
    CostItem,
    SystemCostResult,
    CashFlowYear,
    FinancialEvaluationResult,
    ModuleElectricalSpecs,
    InverterSpecs,
    StringDesign,
    ElectricalCheckResult,
    ElectricalCompatibilityResult,
    ParetoStatus,
    WeightedRankingStatus,
    RecommendationBasis,
    ParetoCandidateResult,
    ParetoRankingResult,
    WeightedCandidateResult,
    WeightedRankingResult,
    RecommendationExplanation,
    RecommendationResult,
)
from src.energy_economics.catalogue import (
    PanelRecord,
    ReadOnlyPanelCatalogue,
)
from src.energy_economics.capacity_evaluator import (
    CapacitySupportEvaluator,
)
from src.energy_economics.phase7_adapter import (
    Phase7Adapter,
)
from src.energy_economics.feasibility import (
    FeasibilityEvaluator,
)
from src.energy_economics.foundation import (
    Phase8FoundationEngine,
)
from src.energy_economics.inference import (
    Phase5PeerCohortPredictor,
)
from src.energy_economics.historical_replay import (
    UNISOLARHistoricalReplayEngine,
)
from src.energy_economics.energy_engine import (
    Phase8EnergyEstimationEngine,
)
from src.energy_economics.annualization import (
    Phase8AnnualizationEngine,
)
from src.energy_economics.degradation import (
    Phase8DegradationEngine,
)
from src.energy_economics.system_cost import (
    Phase8SystemCostEngine,
)
from src.energy_economics.financial import (
    Phase8FinancialEngine,
)
from src.energy_economics.electrical import (
    Phase8ElectricalEngine,
)
from src.energy_economics.pareto import (
    Phase8ParetoEngine,
)
from src.energy_economics.weighted_ranking import (
    Phase8WeightedRankingEngine,
)
from src.energy_economics.recommendation import (
    Phase8RecommendationEngine,
)
from src.energy_economics.engine import (
    EnergyEconomicsEngine,
)

__all__ = [
    # Exceptions
    "Phase8Error",
    "Phase7IntegrationError",
    "CatalogueIntegrationError",
    "PanelNotFoundError",
    "CapacityEvaluationError",
    "FeasibilityEvaluationError",
    "Phase5InferenceError",
    "FeatureValidationError",
    "HistoricalReplayError",
    "EnergyEstimationError",
    "ScenarioValidationError",
    "AnnualizationError",
    "DegradationError",
    "InvalidDegradationInputError",
    "FinancialError",
    "CostStructureError",
    "CurrencyMismatchError",
    "InvalidFinancialInputError",
    "ElectricalError",
    "ElectricalConfigurationError",
    "RankingError",
    "RecommendationError",
    # Enums & Dataclasses
    "CapacitySupportStatus",
    "CapacityEligibility",
    "OverallRecommendationEligibility",
    "GeometricFeasibility",
    "CatalogueValidity",
    "PredictionAvailability",
    "ElectricalCompatibility",
    "EconomicFeasibility",
    "TrainingDistributionMetrics",
    "CapacitySupportResult",
    "FeasibilityResult",
    "ReplaySampleClassification",
    "ModelVariant",
    "HistoricalYearStatus",
    "EnergyScenarioType",
    "ScenarioEvaluationStatus",
    "DailyEnergyEstimate",
    "SiteEnergySummary",
    "EnergyAggregationSummary",
    "AnnualizationMethod",
    "AnnualEvidenceStatus",
    "AnnualEnergyResult",
    "LifetimeEnergyBaseline",
    "DegradationModel",
    "DegradationSource",
    "YearlyDegradationRecord",
    "DegradationResult",
    "CostCategory",
    "LCOECapexBasis",
    "RateBasis",
    "PaybackStatus",
    "CostItem",
    "SystemCostResult",
    "CashFlowYear",
    "FinancialEvaluationResult",
    "ModuleElectricalSpecs",
    "InverterSpecs",
    "StringDesign",
    "ElectricalCheckResult",
    "ElectricalCompatibilityResult",
    "ParetoStatus",
    "WeightedRankingStatus",
    "RecommendationBasis",
    "ParetoCandidateResult",
    "ParetoRankingResult",
    "WeightedCandidateResult",
    "WeightedRankingResult",
    "RecommendationExplanation",
    "RecommendationResult",
    # Core Components
    "PanelRecord",
    "ReadOnlyPanelCatalogue",
    "CapacitySupportEvaluator",
    "Phase7Adapter",
    "FeasibilityEvaluator",
    "Phase8FoundationEngine",
    "Phase5PeerCohortPredictor",
    "UNISOLARHistoricalReplayEngine",
    "Phase8EnergyEstimationEngine",
    "Phase8AnnualizationEngine",
    "Phase8DegradationEngine",
    "Phase8SystemCostEngine",
    "Phase8FinancialEngine",
    "Phase8ElectricalEngine",
    "Phase8ParetoEngine",
    "Phase8WeightedRankingEngine",
    "Phase8RecommendationEngine",
    "EnergyEconomicsEngine",
]
