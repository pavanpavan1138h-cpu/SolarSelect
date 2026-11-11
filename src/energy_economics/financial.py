"""
SolarSelect — Phase 8: Stage 7 Financial Evaluation Engine
Implements:
- Lifecycle cash-flow ledger accounting (initial outlay, operating costs, replacements, residual).
- Explicit CAPEX basis tracking: net CAPEX for NPV and payback; explicit net vs gross basis for LCOE.
- Discounted cash flow (DCF) and Net Present Value (NPV) calculation.
- Simple payback and discounted payback with exact fractional-year linear interpolation.
- Levelized Cost of Energy (LCOE) with explicit cost basis and revenue exclusion.
- Strict rejection of missing discount rates, mismatched rate bases, and fabricated commercial prices.
- Preservation of energy evidence status and UNVERIFIED energy basis (B-1).
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import math

from src.energy_economics.exceptions import (
    FinancialError,
    InvalidFinancialInputError,
)
from src.energy_economics.types import (
    RateBasis,
    LCOECapexBasis,
    PaybackStatus,
    CostItem,
    SystemCostResult,
    CashFlowYear,
    FinancialEvaluationResult,
    AnnualEnergyResult,
    DegradationResult,
)


class Phase8FinancialEngine:
    """
    Engine for Phase 8 Stage 7 financial evaluation and lifecycle economics.
    Conforms strictly to Section 4.6 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage7_financial_evaluation"
    ENERGY_BASIS = "UNVERIFIED"

    def __init__(self) -> None:
        pass

    def evaluate_financials(
        self,
        system_cost: SystemCostResult,
        annual_energy: Union[float, AnnualEnergyResult, DegradationResult, List[float]],
        lifetime_years: int,
        discount_rate: float,
        rate_basis: Union[RateBasis, str],
        lcoe_capex_basis: Union[LCOECapexBasis, str],
        self_consumption_ratio: Optional[float] = None,
        purchase_tariff: Optional[float] = None,
        export_tariff: Optional[float] = None,
        tariff_escalation_rate: float = 0.0,
        export_escalation_rate: float = 0.0,
        recurring_incentives: Optional[Dict[int, float]] = None,
        start_year: Optional[int] = None,
    ) -> FinancialEvaluationResult:
        """
        Executes lifecycle cash-flow formulation, NPV, payback, and LCOE evaluations.

        Args:
            system_cost: SystemCostResult from Phase8SystemCostEngine.
            annual_energy: Energy profile (float, AnnualEnergyResult, DegradationResult, or List[float]).
            lifetime_years: Operating lifetime duration L (1 <= L <= 40).
            discount_rate: Annual discount rate r (r >= 0, required, no default).
            rate_basis: RateBasis (REAL or NOMINAL, required, no default).
            lcoe_capex_basis: LCOECapexBasis (NET or GROSS, required, no default).
            self_consumption_ratio: Fraction sigma of generated energy consumed on-site (0.0 to 1.0).
            purchase_tariff: Grid purchase price per kWh displaced by self-consumption (p_1^buy).
            export_tariff: Feed-in tariff price per exported kWh (p_1^exp).
            tariff_escalation_rate: Annual escalation rate e_p for grid purchase tariff.
            export_escalation_rate: Annual escalation rate e_x for export feed-in tariff.
            recurring_incentives: Optional mapping of year t to recurring incentive payment (Inc_t).
            start_year: Optional calendar year of operating year 1.

        Returns:
            FinancialEvaluationResult containing complete cash-flow ledger, NPV, payback, and LCOE.
        """
        warnings: List[str] = list(system_cost.warnings)
        limitations: List[str] = [
            "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
            "Financial calculations assume static regulatory frameworks and non-stochastic weather regimes.",
        ]

        # 1. Validate discount_rate (strictly required, no default)
        if discount_rate is None:
            raise InvalidFinancialInputError(
                "discount_rate must be explicitly provided (r >= 0). Implicit default rates are prohibited."
            )
        try:
            r = float(discount_rate)
        except (ValueError, TypeError) as e:
            raise InvalidFinancialInputError(f"discount_rate must be a valid float: {e}") from e

        if not math.isfinite(r) or r < 0.0:
            raise InvalidFinancialInputError(
                f"discount_rate must be non-negative and finite, got {r}."
            )

        # 2. Validate rate_basis (strictly required, no default)
        if rate_basis is None:
            raise InvalidFinancialInputError(
                "rate_basis must be explicitly provided ('real' or 'nominal'). Implicit defaults are prohibited."
            )
        if isinstance(rate_basis, str):
            try:
                rate_basis_enum = RateBasis(rate_basis.lower())
            except ValueError:
                raise InvalidFinancialInputError(
                    f"Unsupported rate_basis: '{rate_basis}'. Must be one of {[b.value for b in RateBasis]}."
                )
        else:
            rate_basis_enum = rate_basis

        # Validate rate_basis consistency with system_cost
        if system_cost.rate_basis and system_cost.rate_basis != rate_basis_enum.value:
            raise InvalidFinancialInputError(
                f"Rate basis mismatch: system_cost uses '{system_cost.rate_basis}', but financial evaluation "
                f"requested '{rate_basis_enum.value}'. Rates must be consistently real or nominal."
            )

        # 3. Validate lcoe_capex_basis (strictly required, no default)
        if lcoe_capex_basis is None:
            raise InvalidFinancialInputError(
                "lcoe_capex_basis must be explicitly specified ('net' or 'gross'). Implicit defaults are prohibited."
            )
        if isinstance(lcoe_capex_basis, str):
            try:
                lcoe_basis_enum = LCOECapexBasis(lcoe_capex_basis.lower())
            except ValueError:
                raise InvalidFinancialInputError(
                    f"Unsupported lcoe_capex_basis: '{lcoe_capex_basis}'. Must be 'net' or 'gross'."
                )
        else:
            lcoe_basis_enum = lcoe_capex_basis

        # 4. Validate lifetime_years (L)
        if not isinstance(lifetime_years, int) or isinstance(lifetime_years, bool):
            raise InvalidFinancialInputError(
                f"lifetime_years must be an integer, got {type(lifetime_years).__name__}: {lifetime_years}"
            )
        if lifetime_years < 1 or lifetime_years > 40:
            raise InvalidFinancialInputError(
                f"lifetime_years must be between 1 and 40, got {lifetime_years}."
            )

        # 5. Validate self_consumption_ratio if supplied
        if self_consumption_ratio is not None:
            if not math.isfinite(self_consumption_ratio) or self_consumption_ratio < 0.0 or self_consumption_ratio > 1.0:
                raise InvalidFinancialInputError(
                    f"self_consumption_ratio must be between 0.0 and 1.0, got {self_consumption_ratio}."
                )

        # 6. Extract yearly energy sequence E_t (t=1..L)
        yearly_energy_kwh: List[float] = []
        inherited_evidence_status = "UNVALIDATED_REFERENCE_ONLY"

        if isinstance(annual_energy, DegradationResult):
            yearly_energy_kwh = [yr.annual_energy_kwh for yr in annual_energy.yearly_breakdown[:lifetime_years]]
            inherited_evidence_status = annual_energy.evidence_status
            warnings.extend(annual_energy.warnings)
            limitations.extend(annual_energy.limitations)
        elif isinstance(annual_energy, AnnualEnergyResult):
            if annual_energy.annual_energy_kwh is None:
                # Incomplete or blocked energy input
                return self._create_missing_financial_result(
                    system_cost=system_cost,
                    rate_basis=rate_basis_enum.value,
                    discount_rate=r,
                    lifetime_years=lifetime_years,
                    lcoe_basis=lcoe_basis_enum.value,
                    evidence_status=annual_energy.evidence_status,
                    reason=f"Annual energy is unavailable ({annual_energy.evidence_status}). Financial metrics null.",
                )
            e_base = float(annual_energy.annual_energy_kwh)
            yearly_energy_kwh = [e_base] * lifetime_years
            inherited_evidence_status = annual_energy.evidence_status
            warnings.extend(annual_energy.warnings)
            limitations.extend(annual_energy.limitations)
            limitations.append(
                "Energy sequence uses unadjusted constant-performance baseline (Stage 5); physical degradation "
                "was not modeled for this financial evaluation."
            )
        elif isinstance(annual_energy, list):
            if len(annual_energy) < lifetime_years:
                raise InvalidFinancialInputError(
                    f"annual_energy list has {len(annual_energy)} entries, but lifetime_years is {lifetime_years}."
                )
            yearly_energy_kwh = [float(e) for e in annual_energy[:lifetime_years]]
        else:
            try:
                e_val = float(annual_energy)
                if not math.isfinite(e_val) or e_val <= 0:
                    raise InvalidFinancialInputError(f"annual_energy must be strictly positive, got {e_val}.")
                yearly_energy_kwh = [e_val] * lifetime_years
            except (ValueError, TypeError) as e:
                raise InvalidFinancialInputError(f"annual_energy could not be parsed: {e}") from e

        # 7. Check if system_cost is populated
        if system_cost.c_net is None or system_cost.c_gross is None:
            return self._create_missing_financial_result(
                system_cost=system_cost,
                rate_basis=rate_basis_enum.value,
                discount_rate=r,
                lifetime_years=lifetime_years,
                lcoe_basis=lcoe_basis_enum.value,
                evidence_status=inherited_evidence_status,
                reason="Commercial system costs are unpopulated. Financial metrics null.",
            )

        c_gross = float(system_cost.c_gross)
        s_upfront = float(system_cost.s_upfront)
        c_net = float(system_cost.c_net)

        # 8. Compute Cash Flows
        cash_flows: List[CashFlowYear] = []
        cum_cf = -c_net
        cum_dcf = -c_net
        total_discounted_cash_flows = -c_net  # CF_0 included in NPV

        nominal_opex_sum = 0.0
        discounted_opex_sum = 0.0

        tariffs_supplied = (
            self_consumption_ratio is not None and
            purchase_tariff is not None and
            export_tariff is not None
        )

        lcoe_cost_numerator = c_net if lcoe_basis_enum == LCOECapexBasis.NET else c_gross
        lcoe_energy_denominator = 0.0

        for t in range(1, lifetime_years + 1):
            cal_yr = (start_year + t - 1) if start_year is not None else None
            e_t = yearly_energy_kwh[t - 1]

            # Energy revenues / savings
            savings_t = None
            export_rev_t = None
            sc_kwh = None
            ex_kwh = None
            p_buy_t = None
            p_exp_t = None

            if tariffs_supplied:
                sc_ratio = float(self_consumption_ratio)
                sc_kwh = e_t * sc_ratio
                ex_kwh = e_t * (1.0 - sc_ratio)
                p_buy_t = float(purchase_tariff) * math.pow(1.0 + tariff_escalation_rate, t - 1)
                p_exp_t = float(export_tariff) * math.pow(1.0 + export_escalation_rate, t - 1)
                savings_t = sc_kwh * p_buy_t
                export_rev_t = ex_kwh * p_exp_t
                rev_total_t = savings_t + export_rev_t
            else:
                rev_total_t = 0.0

            # Operating costs and replacements
            base_opex_t = float(system_cost.annual_base_opex) * math.pow(1.0 + system_cost.opex_escalation_rate, t - 1)
            replacement_t = float(system_cost.replacement_schedule.get(t, 0.0))
            residual_t = float(system_cost.residual_value) if t == lifetime_years else 0.0
            inc_t = float(recurring_incentives.get(t, 0.0)) if recurring_incentives else 0.0

            net_cf_t = rev_total_t + inc_t - base_opex_t - replacement_t + residual_t
            df_t = math.pow(1.0 + r, -t)
            dcf_t = net_cf_t * df_t

            cum_cf += net_cf_t
            cum_dcf += dcf_t
            total_discounted_cash_flows += dcf_t

            nominal_opex_sum += (base_opex_t + replacement_t)
            discounted_opex_sum += (base_opex_t + replacement_t) * df_t

            # LCOE accumulation
            # Cost stream includes base opex and replacements, less residual value at year L
            cost_t = base_opex_t + replacement_t - (residual_t if t == lifetime_years else 0.0)
            lcoe_cost_numerator += cost_t * df_t
            lcoe_energy_denominator += e_t * df_t

            cash_flows.append(
                CashFlowYear(
                    operating_year=t,
                    calendar_year=cal_yr,
                    generated_energy_kwh=e_t,
                    self_consumed_energy_kwh=sc_kwh,
                    exported_energy_kwh=ex_kwh,
                    purchase_tariff=p_buy_t,
                    export_tariff=p_exp_t,
                    savings_amount=savings_t,
                    export_revenue=export_rev_t,
                    recurring_incentives=inc_t,
                    base_opex=base_opex_t,
                    replacement_cost=replacement_t,
                    residual_value=residual_t,
                    net_cash_flow=net_cf_t,
                    discount_factor=df_t,
                    discounted_cash_flow=dcf_t,
                    cumulative_cash_flow=cum_cf,
                    cumulative_discounted_cash_flow=cum_dcf,
                )
            )

        # 9. Payback Calculations
        simple_payback_yrs = None
        simple_payback_int = None
        simple_status = PaybackStatus.ACHIEVED.value

        disc_payback_yrs = None
        disc_payback_int = None
        disc_status = PaybackStatus.ACHIEVED.value

        if not tariffs_supplied:
            simple_status = PaybackStatus.NOT_EVALUATED_MISSING_TARIFFS.value
            disc_status = PaybackStatus.NOT_EVALUATED_MISSING_TARIFFS.value
            warnings.append(
                "Energy revenue and tariff inputs were not provided. Payback periods cannot be evaluated."
            )
        elif c_net <= 0.0:
            simple_status = PaybackStatus.NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX.value
            disc_status = PaybackStatus.NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX.value
        else:
            # Simple Payback: find smallest T where cum_cf >= 0
            found_simple = False
            for idx, yr in enumerate(cash_flows):
                if yr.cumulative_cash_flow >= 0.0:
                    found_simple = True
                    simple_payback_int = yr.operating_year
                    # Fractional year interpolation: (T - 1) + (-CumCF_{T-1}) / CF_T
                    if idx == 0:
                        prev_cum = -c_net
                    else:
                        prev_cum = cash_flows[idx - 1].cumulative_cash_flow

                    cf_curr = yr.net_cash_flow
                    if cf_curr > 0:
                        fractional = (yr.operating_year - 1) + (-prev_cum) / cf_curr
                        simple_payback_yrs = max(0.0, min(float(lifetime_years), float(fractional)))
                    else:
                        simple_payback_yrs = float(yr.operating_year)
                    break

            if not found_simple:
                simple_status = PaybackStatus.NOT_ACHIEVED_WITHIN_LIFETIME.value

            # Discounted Payback: find smallest T where cum_dcf >= 0
            found_disc = False
            for idx, yr in enumerate(cash_flows):
                if yr.cumulative_discounted_cash_flow >= 0.0:
                    found_disc = True
                    disc_payback_int = yr.operating_year
                    if idx == 0:
                        prev_cum_d = -c_net
                    else:
                        prev_cum_d = cash_flows[idx - 1].cumulative_discounted_cash_flow

                    dcf_curr = yr.discounted_cash_flow
                    if dcf_curr > 0:
                        fractional_d = (yr.operating_year - 1) + (-prev_cum_d) / dcf_curr
                        disc_payback_yrs = max(0.0, min(float(lifetime_years), float(fractional_d)))
                    else:
                        disc_payback_yrs = float(yr.operating_year)
                    break

            if not found_disc:
                disc_status = PaybackStatus.NOT_ACHIEVED_WITHIN_LIFETIME.value

        # 10. LCOE Calculation
        if lcoe_energy_denominator > 0:
            lcoe_val = lcoe_cost_numerator / lcoe_energy_denominator
        else:
            lcoe_val = None

        return FinancialEvaluationResult(
            currency=system_cost.currency,
            rate_basis=rate_basis_enum.value,
            discount_rate=r,
            lifetime_years=lifetime_years,
            financial_capex_basis="net",
            lcoe_capex_basis=lcoe_basis_enum.value,
            c_gross=c_gross,
            s_upfront=s_upfront,
            c_net=c_net,
            npv=total_discounted_cash_flows if tariffs_supplied else None,
            simple_payback_years=simple_payback_yrs,
            simple_payback_integer_year=simple_payback_int,
            simple_payback_status=simple_status,
            discounted_payback_years=disc_payback_yrs,
            discounted_payback_integer_year=disc_payback_int,
            discounted_payback_status=disc_status,
            lcoe_per_kwh=lcoe_val,
            annual_base_opex=system_cost.annual_base_opex,
            lifetime_nominal_opex=nominal_opex_sum,
            lifetime_discounted_opex=discounted_opex_sum,
            cash_flows=cash_flows,
            evidence_status=inherited_evidence_status,
            energy_basis=self.ENERGY_BASIS,
            warnings=warnings,
            limitations=limitations,
            metadata={
                "lcoe_cost_numerator": lcoe_cost_numerator,
                "lcoe_energy_denominator": lcoe_energy_denominator,
                "tariffs_supplied": tariffs_supplied,
            },
        )

    def _create_missing_financial_result(
        self,
        system_cost: SystemCostResult,
        rate_basis: str,
        discount_rate: float,
        lifetime_years: int,
        lcoe_basis: str,
        evidence_status: str,
        reason: str,
    ) -> FinancialEvaluationResult:
        """Helper returning null financial evaluation with explicit reasons."""
        return FinancialEvaluationResult(
            currency=system_cost.currency,
            rate_basis=rate_basis,
            discount_rate=discount_rate,
            lifetime_years=lifetime_years,
            financial_capex_basis="net",
            lcoe_capex_basis=lcoe_basis,
            c_gross=system_cost.c_gross,
            s_upfront=system_cost.s_upfront,
            c_net=system_cost.c_net,
            npv=None,
            simple_payback_years=None,
            simple_payback_integer_year=None,
            simple_payback_status=PaybackStatus.NOT_EVALUATED_MISSING_TARIFFS.value,
            discounted_payback_years=None,
            discounted_payback_integer_year=None,
            discounted_payback_status=PaybackStatus.NOT_EVALUATED_MISSING_TARIFFS.value,
            lcoe_per_kwh=None,
            annual_base_opex=system_cost.annual_base_opex,
            lifetime_nominal_opex=0.0,
            lifetime_discounted_opex=0.0,
            cash_flows=[],
            evidence_status=evidence_status,
            energy_basis=self.ENERGY_BASIS,
            warnings=[reason] + list(system_cost.warnings),
            limitations=["Financial metrics unavailable due to missing upstream inputs."],
            metadata={"status": "MISSING_INPUTS", "reason": reason},
        )

