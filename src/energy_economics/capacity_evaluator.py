"""
SolarSelect — Phase 8: Capacity Support Evaluator
Evaluates candidate DC capacity (kWp) against the authoritative 22-site
Peer Cohort training capacity distribution.
Provides strict marginal univariate capacity support and capacity eligibility verdicts.
"""

import math
from typing import Optional, Union

from src.energy_economics.exceptions import CapacityEvaluationError
from src.energy_economics.types import (
    CapacitySupportStatus,
    CapacityEligibility,
    CapacitySupportResult,
    TrainingDistributionMetrics,
)


class CapacitySupportEvaluator:
    """
    Evaluates marginal training-capacity support for solar array candidates.
    Distinguishes dense core commercial cluster (21.39–100.00 kWp), sparse high-variance
    tail (100.00–539.80 kWp), and unsupported extrapolations (<21.39 or >539.80 kWp).
    """

    DEFAULT_DISTRIBUTION = TrainingDistributionMetrics()

    def __init__(
        self,
        distribution: Optional[TrainingDistributionMetrics] = DEFAULT_DISTRIBUTION,
    ) -> None:
        self.distribution = distribution

    def evaluate(
        self, installed_dc_capacity_kwp: Union[float, int]
    ) -> CapacitySupportResult:
        """
        Evaluates marginal training-capacity support for a given installed DC capacity.

        Args:
            installed_dc_capacity_kwp: System DC capacity in kilowatts-peak (kWp).

        Returns:
            CapacitySupportResult with capacity_support_status, capacity_eligibility,
            training distribution summary, and any applicable warning.

        Raises:
            CapacityEvaluationError: If capacity is null, non-numeric, NaN, infinite, or negative.
        """
        # Validate input numeric sanity
        if installed_dc_capacity_kwp is None:
            raise CapacityEvaluationError("Installed DC capacity cannot be None.")

        try:
            kwp = float(installed_dc_capacity_kwp)
        except (ValueError, TypeError) as e:
            raise CapacityEvaluationError(
                f"Installed DC capacity must be a numeric value, got '{installed_dc_capacity_kwp}'"
            ) from e

        if math.isnan(kwp) or math.isinf(kwp):
            raise CapacityEvaluationError(f"Installed DC capacity must be finite, got {kwp}.")

        if kwp < 0.0:
            raise CapacityEvaluationError(
                f"Installed DC capacity cannot be negative, got {kwp} kWp."
            )

        # Check distribution metadata availability
        if self.distribution is None:
            return CapacitySupportResult(
                status=CapacitySupportStatus.CAPACITY_DISTRIBUTION_UNAVAILABLE,
                candidate_kwp=kwp,
                capacity_eligibility=CapacityEligibility.CAPACITY_INELIGIBLE_UNAVAILABLE,
                training_distribution=None,
                warning="CAPACITY_DISTRIBUTION_METADATA_MISSING",
            )

        min_kwp = self.distribution.min_kwp
        core_max_kwp = self.distribution.core_band_kwp[1]
        max_kwp = self.distribution.max_kwp

        # 1. Dense Core band: [21.39, 100.00] kWp
        if min_kwp <= kwp <= core_max_kwp:
            return CapacitySupportResult(
                status=CapacitySupportStatus.SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION,
                candidate_kwp=kwp,
                capacity_eligibility=CapacityEligibility.CAPACITY_ELIGIBLE,
                training_distribution=self.distribution,
                warning=None,
            )

        # 2. Sparse Region: (100.00, 539.80] kWp
        elif core_max_kwp < kwp <= max_kwp:
            return CapacitySupportResult(
                status=CapacitySupportStatus.SPARSE_TRAINING_SUPPORT,
                candidate_kwp=kwp,
                capacity_eligibility=CapacityEligibility.CAPACITY_FLAGGED_SPARSE,
                training_distribution=self.distribution,
                warning="SPARSE_TRAINING_SUPPORT_WARNING",
            )

        # 3. Out of Range (Sub-minimum < 21.39 kWp or Super-maximum > 539.80 kWp)
        else:
            return CapacitySupportResult(
                status=CapacitySupportStatus.OUT_OF_TRAINING_RANGE,
                candidate_kwp=kwp,
                capacity_eligibility=CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE,
                training_distribution=self.distribution,
                warning="CAPACITY_OUT_OF_DISTRIBUTION_WARNING",
            )

