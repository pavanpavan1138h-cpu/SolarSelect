"""
SolarSelect — Phase 8: Stage 6 Degradation Modelling Engine
Implements:
- Explicit compounded degradation modeling: E_t = E_1 * (1 - d)^(t - 1) (original Section 4.4 formula).
- Explicit linear degradation modeling: E_t = E_1 * [1 - d * (t - 1)] (alternative modeling assumption).
- Physical positivity constraints (1 - d*(L-1) > 0) preventing non-positive energy generation.
- Transparent degradation-rate bound governance (proposed 0-5% bound requiring approval; configurable).
- Controlled negative degradation handling (allowed with EXTRAPOLATED_BEYOND_WARRANTY warning and source note).
- Constant-performance lifetime baseline comparison: E_life_baseline = E_1 * L.
- Configurable warranty validation tolerance (heuristic threshold without established standard).
- Catalogue datasheet warranty consistency checks and provenance qualification preservation.
- Strict separation of user-configured degradation assumptions from manufacturer warranty guarantees.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import math

from src.energy_economics.exceptions import (
    DegradationError,
    InvalidDegradationInputError,
)
from src.energy_economics.types import (
    DegradationModel,
    DegradationSource,
    YearlyDegradationRecord,
    DegradationResult,
    AnnualEnergyResult,
)
from src.energy_economics.catalogue import (
    PanelRecord,
    ReadOnlyPanelCatalogue,
)


class Phase8DegradationEngine:
    """
    Engine for Phase 8 Stage 6 lifetime degradation modeling.
    Conforms strictly to Section 4.4 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage6_degradation_modelling"
    ENERGY_BASIS = "UNVERIFIED"

    DEFAULT_MAX_DEGRADATION_RATE = 0.05  # 5.0% per year proposed bound
    DEGRADATION_BOUND_STATUS_PROPOSED = "PROPOSED_BOUND_REQUIRING_APPROVAL"
    DEGRADATION_BOUND_STATUS_CONFIGURED = "CONFIGURED_POLICY_OVERRIDE"

    DEFAULT_WARRANTY_TOLERANCE = 0.01  # 1.0% configurable heuristic tolerance
    WARRANTY_TOLERANCE_STATUS = "CONFIGURABLE_VALIDATION_TOLERANCE_NO_ESTABLISHED_STANDARD"

    MIN_LIFETIME_YEARS = 1
    MAX_LIFETIME_YEARS = 40

    DEGRADATION_MODEL_UNVERIFIED_WARNING = (
        "DEGRADATION_MODEL_TYPE_NOT_ESTABLISHED_BY_CATALOGUE: Catalogue annual_degradation_pct is a "
        "datasheet summary whose degradation model type (linear vs compounded) is not recorded in the catalogue. "
        "User-selected model applied."
    )

    WARRANTY_LIMITATION_NOTE = (
        "Manufacturer performance warranties represent guaranteed minimum power output thresholds, "
        "not empirical expected or measured field degradation rates. Warranties exclude initial light-induced "
        "degradation unless explicitly specified."
    )

    PROPOSED_BOUND_GOVERNANCE_NOTE = (
        "The 0–5%/yr degradation rate bound is a proposed specification bound requiring formal governance approval; "
        "it is not an independently certified empirical scientific limit. This policy is tracked separately "
        "from Decision D-5 (monthly coverage-adjusted annualization)."
    )

    def __init__(
        self,
        catalogue: Optional[ReadOnlyPanelCatalogue] = None,
        max_degradation_rate: Optional[float] = None,
        warranty_tolerance: Optional[float] = None,
        max_negative_degradation_rate: Optional[float] = None,
    ) -> None:
        self.catalogue = catalogue or ReadOnlyPanelCatalogue()
        if max_degradation_rate is not None:
            if not math.isfinite(max_degradation_rate) or max_degradation_rate <= 0:
                raise InvalidDegradationInputError(
                    f"max_degradation_rate must be a positive finite float, got {max_degradation_rate}."
                )
            self.max_degradation_rate = float(max_degradation_rate)
            self.degradation_bound_status = self.DEGRADATION_BOUND_STATUS_CONFIGURED
        else:
            self.max_degradation_rate = self.DEFAULT_MAX_DEGRADATION_RATE
            self.degradation_bound_status = self.DEGRADATION_BOUND_STATUS_PROPOSED

        if max_negative_degradation_rate is not None:
            if not math.isfinite(max_negative_degradation_rate) or max_negative_degradation_rate <= 0:
                raise InvalidDegradationInputError(
                    f"max_negative_degradation_rate must be a positive finite float, got {max_negative_degradation_rate}."
                )
            self.max_negative_degradation_rate = float(max_negative_degradation_rate)
        else:
            self.max_negative_degradation_rate = self.max_degradation_rate

        if warranty_tolerance is not None:
            if not math.isfinite(warranty_tolerance) or warranty_tolerance < 0:
                raise InvalidDegradationInputError(
                    f"warranty_tolerance must be a non-negative finite float, got {warranty_tolerance}."
                )
            self.warranty_tolerance = float(warranty_tolerance)
        else:
            self.warranty_tolerance = self.DEFAULT_WARRANTY_TOLERANCE

    def evaluate_degradation(
        self,
        annual_energy: Union[float, AnnualEnergyResult],
        degradation_model: Union[DegradationModel, str],
        degradation_rate: Optional[float] = None,
        lifetime_years: int = 25,
        start_year: Optional[int] = None,
        degradation_source: Union[DegradationSource, str] = DegradationSource.USER,
        degradation_source_note: Optional[str] = None,
        panel_id: Optional[str] = None,
        panel_record: Optional[PanelRecord] = None,
        evidence_status: Optional[str] = None,
        warranty_tolerance: Optional[float] = None,
    ) -> DegradationResult:
        """
        Executes lifetime degradation modeling for an initial annual energy input.

        Args:
            annual_energy: Initial annual energy (kWh/yr), either as float (E_1) or AnnualEnergyResult.
            degradation_model: Explicit DegradationModel (COMPOUNDED or LINEAR). No implicit default.
            degradation_rate: Annual degradation fraction d (e.g. 0.005 for 0.5%/yr). Required if not catalogue.
            lifetime_years: System operating duration L (1 <= L <= 40). Integer.
            start_year: Optional calendar year of operating year 1 (e.g. 2024).
            degradation_source: Source of degradation parameter (USER, ASSUMPTION, CATALOGUE).
            degradation_source_note: Contextual note explaining source or empirical basis.
            panel_id: Optional panel identifier for catalogue lookups.
            panel_record: Optional PanelRecord for catalogue lookups.
            evidence_status: Explicit evidence status string or inherited from AnnualEnergyResult.
            warranty_tolerance: Optional tolerance override for warranty consistency checking.

        Returns:
            DegradationResult containing yearly breakdowns, cumulative lifetime totals, baseline, and metadata.
        """
        warnings: List[str] = []
        limitations: List[str] = [
            "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
            self.WARRANTY_LIMITATION_NOTE,
            self.PROPOSED_BOUND_GOVERNANCE_NOTE,
        ]

        active_warranty_tolerance = (
            warranty_tolerance if warranty_tolerance is not None else self.warranty_tolerance
        )
        if not math.isfinite(active_warranty_tolerance) or active_warranty_tolerance < 0:
            raise InvalidDegradationInputError(
                f"warranty_tolerance must be a non-negative finite float, got {active_warranty_tolerance}."
            )

        # 1. Parse and extract initial annual energy (E_1)
        if isinstance(annual_energy, AnnualEnergyResult):
            if annual_energy.annual_energy_kwh is None:
                raise DegradationError(
                    "Cannot model degradation: AnnualEnergyResult has annual_energy_kwh=None "
                    f"(status: {annual_energy.evidence_status}). Complete annual reference is required."
                )
            e_1 = float(annual_energy.annual_energy_kwh)
            inherited_status = annual_energy.evidence_status
            warnings.extend(annual_energy.warnings)
            limitations.extend(annual_energy.limitations)
        else:
            try:
                e_1 = float(annual_energy)
            except (ValueError, TypeError) as e:
                raise InvalidDegradationInputError(f"annual_energy must be a valid float: {e}") from e
            inherited_status = evidence_status or "UNVALIDATED_REFERENCE_ONLY"

        if not math.isfinite(e_1) or e_1 <= 0:
            raise InvalidDegradationInputError(
                f"Initial annual energy E_1 must be a positive finite number, got {e_1}."
            )

        # 2. Validate degradation model (strictly required, no default)
        if degradation_model is None:
            raise InvalidDegradationInputError(
                "degradation_model must be explicitly specified ('compounded' or 'linear'). "
                "Implicit defaults are prohibited."
            )
        if isinstance(degradation_model, str):
            try:
                model_enum = DegradationModel(degradation_model.lower())
            except ValueError:
                raise InvalidDegradationInputError(
                    f"Unsupported degradation_model: '{degradation_model}'. "
                    f"Must be one of {[m.value for m in DegradationModel]}."
                )
        else:
            model_enum = degradation_model

        # Document model distinction
        if model_enum == DegradationModel.COMPOUNDED:
            model_status = "SPECIFIED_ORIGINAL_FORMULA"
            formula_label = "E_t = E_1 * (1 - d)^(t - 1)"
        else:  # LINEAR
            model_status = "ALTERNATIVE_MODELLING_ASSUMPTION"
            formula_label = "E_t = E_1 * [1 - d * (t - 1)]"
            warnings.append(
                "LINEAR_MODEL_ALTERNATIVE_ASSUMPTION: Linear degradation is an alternative modeling assumption; "
                "Mathematical Specification Section 4.4 specifies compounded degradation as the original formula."
            )

        # 3. Validate lifetime_years (L)
        if not isinstance(lifetime_years, int) or isinstance(lifetime_years, bool):
            raise InvalidDegradationInputError(
                f"lifetime_years must be an integer, got {type(lifetime_years).__name__}: {lifetime_years}"
            )
        if lifetime_years < self.MIN_LIFETIME_YEARS or lifetime_years > self.MAX_LIFETIME_YEARS:
            raise InvalidDegradationInputError(
                f"lifetime_years must be between {self.MIN_LIFETIME_YEARS} and {self.MAX_LIFETIME_YEARS}, "
                f"got {lifetime_years}."
            )

        # 4. Validate start_year
        if start_year is not None:
            if not isinstance(start_year, int) or isinstance(start_year, bool):
                raise InvalidDegradationInputError(
                    f"start_year must be an integer year (e.g. 2024), got {type(start_year).__name__}: {start_year}"
                )
            if start_year < 1970 or start_year > 2100:
                raise InvalidDegradationInputError(
                    f"start_year out of plausible range [1970, 2100]: {start_year}"
                )

        # 5. Parse degradation source
        if isinstance(degradation_source, str):
            try:
                source_enum = DegradationSource(degradation_source.lower())
            except ValueError:
                raise InvalidDegradationInputError(
                    f"Unsupported degradation_source: '{degradation_source}'. "
                    f"Must be one of {[s.value for s in DegradationSource]}."
                )
        else:
            source_enum = degradation_source

        # 6. Retrieve or validate degradation rate (d)
        catalogue_unverified = False
        target_panel_record: Optional[PanelRecord] = None
        warranty_checked = False
        warranty_warning: Optional[str] = None
        provenance_qual: Optional[str] = None

        if source_enum == DegradationSource.CATALOGUE:
            # Resolve panel record
            if panel_record is not None:
                target_panel_record = panel_record
            elif panel_id is not None:
                target_panel_record = self.catalogue.get_panel(panel_id)
            else:
                raise InvalidDegradationInputError(
                    "degradation_source is 'catalogue', but neither panel_id nor panel_record was provided."
                )

            if target_panel_record.annual_degradation_pct is None:
                raise InvalidDegradationInputError(
                    f"Panel '{target_panel_record.panel_id}' in catalogue has null annual_degradation_pct. "
                    "Cannot use catalogue degradation source."
                )

            d = target_panel_record.annual_degradation_pct / 100.0
            catalogue_unverified = True
            warnings.append(self.DEGRADATION_MODEL_UNVERIFIED_WARNING)
            provenance_qual = self.catalogue.PROVENANCE_QUALIFICATION

            # Warranty consistency check
            warranty_years = target_panel_record.performance_warranty_years
            warranty_end_pct = target_panel_record.end_of_warranty_power_pct

            if warranty_years is not None and warranty_end_pct is not None:
                warranty_checked = True
                lw = int(warranty_years)
                pw_fraction = warranty_end_pct / 100.0

                # Compute power ratio at warranty end year lw
                if model_enum == DegradationModel.LINEAR:
                    p_calc = 1.0 - d * (lw - 1)
                else:  # COMPOUNDED
                    p_calc = math.pow(1.0 - d, lw - 1)

                if abs(p_calc - pw_fraction) > active_warranty_tolerance:
                    warranty_warning = (
                        f"CATALOGUE_WARRANTY_DEGRADATION_MISMATCH: Calculated power at warranty end year {lw} "
                        f"({p_calc * 100:.2f}%) differs from catalogue end_of_warranty_power_pct "
                        f"({warranty_end_pct:.2f}%) by more than configurable validation tolerance "
                        f"({active_warranty_tolerance * 100:.1f}%). Warranty figures represent minimum performance guarantees "
                        "rather than expected degradation rates."
                    )
                    warnings.append(warranty_warning)

                if lifetime_years > lw:
                    warnings.append(
                        f"EXTRAPOLATED_BEYOND_WARRANTY: Lifetime duration L={lifetime_years} exceeds panel "
                        f"performance warranty period of {warranty_years} years."
                    )
        else:
            # User or assumption source
            if degradation_rate is None:
                raise InvalidDegradationInputError(
                    f"degradation_rate must be explicitly provided when degradation_source is '{source_enum.value}'."
                )
            try:
                d = float(degradation_rate)
            except (ValueError, TypeError) as e:
                raise InvalidDegradationInputError(f"degradation_rate must be a valid float: {e}") from e

        # Validate finite rate
        if not math.isfinite(d):
            raise InvalidDegradationInputError(f"degradation_rate must be finite, got {d}.")

        # Negative degradation policy
        if d < 0.0:
            if source_enum == DegradationSource.CATALOGUE:
                raise InvalidDegradationInputError("Catalogue degradation cannot be negative.")
            if not degradation_source_note:
                raise InvalidDegradationInputError(
                    "Negative degradation (generation growth over time) requires an explicit degradation_source_note "
                    "documenting the empirical basis or research assumption."
                )
            if d < -self.max_negative_degradation_rate:
                raise InvalidDegradationInputError(
                    f"Negative degradation rate d={d} exceeds maximum allowable negative rate bound "
                    f"(-{self.max_negative_degradation_rate}) [configurable policy bound]."
                )
            warnings.append(
                f"EXTRAPOLATED_BEYOND_WARRANTY: Negative degradation rate d={d:.4f} indicates power growth over time, "
                "which is outside manufacturer warranty specifications and represents an unvalidated modeling assumption."
            )
        elif d > self.max_degradation_rate:
            raise InvalidDegradationInputError(
                f"degradation_rate {d} ({d * 100:.2f}%/yr) exceeds maximum rate bound of "
                f"{self.max_degradation_rate} ({self.max_degradation_rate * 100:.1f}%/yr) "
                f"[{self.degradation_bound_status}]."
            )

        # 7. Physical Positivity Constraint for Linear Degradation
        if model_enum == DegradationModel.LINEAR:
            terminal_factor = 1.0 - d * (lifetime_years - 1)
            if terminal_factor <= 0:
                raise InvalidDegradationInputError(
                    f"Linear degradation violates physical positivity constraint: in year {lifetime_years}, "
                    f"generation factor is {terminal_factor:.4f} <= 0. Energy cannot become zero or negative."
                )

        # 8. Compute Yearly Energy and Cumulative Totals
        yearly_breakdown: List[YearlyDegradationRecord] = []
        running_cumulative = 0.0

        for t in range(1, lifetime_years + 1):
            cal_yr = (start_year + t - 1) if start_year is not None else None

            if model_enum == DegradationModel.COMPOUNDED:
                factor = math.pow(1.0 - d, t - 1)
            else:  # LINEAR
                factor = 1.0 - d * (t - 1)

            e_t = e_1 * factor
            running_cumulative += e_t

            yearly_breakdown.append(
                YearlyDegradationRecord(
                    operating_year=t,
                    calendar_year=cal_yr,
                    degradation_factor=factor,
                    annual_energy_kwh=e_t,
                    cumulative_energy_kwh=running_cumulative,
                )
            )

        # Closed-form analytical cumulative energy verification
        if model_enum == DegradationModel.COMPOUNDED:
            if d != 0.0:
                closed_form_cumulative = e_1 * (1.0 - math.pow(1.0 - d, lifetime_years)) / d
            else:
                closed_form_cumulative = e_1 * lifetime_years
        else:  # LINEAR
            closed_form_cumulative = e_1 * (lifetime_years - d * (lifetime_years * (lifetime_years - 1) / 2.0))

        assert abs(running_cumulative - closed_form_cumulative) < 1e-4, (
            f"Arithmetic discrepancy in cumulative degradation energy: {running_cumulative} vs {closed_form_cumulative}"
        )

        # Constant-performance baseline comparison (E_life_baseline = E_1 * L)
        baseline_cumulative = e_1 * lifetime_years
        lifetime_loss = baseline_cumulative - closed_form_cumulative
        loss_fraction = (lifetime_loss / baseline_cumulative) if baseline_cumulative > 0 else 0.0

        return DegradationResult(
            degradation_model=model_enum.value,
            degradation_rate=d,
            degradation_rate_pct=d * 100.0,
            degradation_source=source_enum.value,
            degradation_source_note=degradation_source_note,
            lifetime_years=lifetime_years,
            start_year=start_year,
            initial_annual_energy_kwh=e_1,
            cumulative_lifetime_energy_kwh=closed_form_cumulative,
            baseline_lifetime_energy_kwh=baseline_cumulative,
            lifetime_degradation_loss_kwh=lifetime_loss,
            lifetime_loss_fraction=loss_fraction,
            yearly_breakdown=yearly_breakdown,
            evidence_status=inherited_status,
            energy_basis=self.ENERGY_BASIS,
            catalogue_unverified_model_type=catalogue_unverified,
            panel_id=target_panel_record.panel_id if target_panel_record else None,
            performance_warranty_years=(
                target_panel_record.performance_warranty_years if target_panel_record else None
            ),
            end_of_warranty_power_pct=(
                target_panel_record.end_of_warranty_power_pct if target_panel_record else None
            ),
            warranty_consistency_checked=warranty_checked,
            warranty_consistency_warning=warranty_warning,
            provenance_qualification=provenance_qual,
            warnings=warnings,
            limitations=limitations,
            metadata={
                "model_status": model_status,
                "formula_yearly": formula_label,
                "degradation_bound_status": self.degradation_bound_status,
                "max_degradation_rate": self.max_degradation_rate,
                "warranty_tolerance": active_warranty_tolerance,
                "warranty_tolerance_status": self.WARRANTY_TOLERANCE_STATUS,
                "closed_form_cumulative_kwh": closed_form_cumulative,
                "discrete_sum_cumulative_kwh": running_cumulative,
            },
        )
