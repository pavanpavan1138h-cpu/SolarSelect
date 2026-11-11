"""
SolarSelect — Phase 8: Stage 7 System Cost Engine
Implements:
- Itemized CAPEX component aggregation (panels, inverter, mounting, BOS, labour, permits, taxes).
- Upfront capital incentives and subsidies isolation (S_up >= 0).
- Explicit derivation of gross CAPEX (C_gross) and net CAPEX (C_net = C_gross - S_up).
- Itemized recurring OPEX, replacements schedule, and residual value aggregation.
- Strict currency mismatch rejection and validation contracts.
- Missing commercial pricing preservation without synthetic estimation.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import math

from src.energy_economics.exceptions import (
    CostStructureError,
    CurrencyMismatchError,
    InvalidFinancialInputError,
)
from src.energy_economics.types import (
    CostCategory,
    CostItem,
    SystemCostResult,
    RateBasis,
)


class Phase8SystemCostEngine:
    """
    Engine for Phase 8 Stage 7 system cost accounting and aggregation.
    Conforms strictly to Section 4.5 and 4.6 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage7_system_cost"

    CAPEX_SUBCATEGORIES = {
        "panels", "inverter", "mounting", "bos", "labour", "permits",
        "interconnection", "taxes", "subsidies", "other_capex"
    }

    OPEX_SUBCATEGORIES = {
        "maintenance", "cleaning", "insurance", "monitoring",
        "replacement", "residual", "decommissioning", "other_opex"
    }

    def __init__(self) -> None:
        pass

    def evaluate_system_cost(
        self,
        cost_items: Optional[List[CostItem]] = None,
        rate_basis: Union[RateBasis, str] = RateBasis.REAL,
        opex_escalation_rate: float = 0.0,
        residual_value: float = 0.0,
    ) -> SystemCostResult:
        """
        Aggregates itemized cost items into structured CAPEX and OPEX schedules.

        Args:
            cost_items: List of CostItem records carrying explicit currency, source, quantity, and amounts.
            rate_basis: RateBasis (REAL or NOMINAL) accounting convention.
            opex_escalation_rate: Annual recurring OPEX escalation rate e_o (fraction/yr).
            residual_value: Optional residual value V_L at end of system life (default 0.0).

        Returns:
            SystemCostResult containing gross CAPEX, net CAPEX, upfront subsidies, and OPEX schedules.
        """
        # Validate rate basis
        if isinstance(rate_basis, str):
            try:
                rate_basis_enum = RateBasis(rate_basis.lower())
            except ValueError:
                raise InvalidFinancialInputError(
                    f"Unsupported rate_basis: '{rate_basis}'. Must be one of {[r.value for r in RateBasis]}."
                )
        else:
            rate_basis_enum = rate_basis

        # Validate opex escalation rate
        if not math.isfinite(opex_escalation_rate) or opex_escalation_rate < -0.2 or opex_escalation_rate > 0.3:
            raise InvalidFinancialInputError(
                f"opex_escalation_rate must be a finite rate between -0.2 and 0.3, got {opex_escalation_rate}."
            )

        # Validate residual value
        if not math.isfinite(residual_value) or residual_value < 0.0:
            raise InvalidFinancialInputError(
                f"residual_value must be non-negative and finite, got {residual_value}."
            )

        # Handle empty or missing cost items
        if not cost_items:
            return SystemCostResult(
                c_gross=None,
                s_upfront=0.0,
                c_net=None,
                currency="UNSPECIFIED",
                rate_basis=rate_basis_enum.value,
                capex_items=[],
                opex_items=[],
                annual_base_opex=0.0,
                opex_escalation_rate=opex_escalation_rate,
                replacement_schedule={},
                residual_value=residual_value,
                warnings=[
                    "No commercial cost items provided. Commercial pricing is not populated in Phase 6 catalogue. "
                    "System cost remains unavailable without user-supplied quotations."
                ],
                missing_inputs=["CAPEX items (panels, inverter, BOS, labour, permits)", "OPEX items"],
            )

        # Validate currency consistency
        currencies = {item.currency.strip().upper() for item in cost_items if item.currency}
        if len(currencies) > 1:
            raise CurrencyMismatchError(
                f"Mismatched currencies found in cost items: {sorted(list(currencies))}. "
                "All cost items must share a single currency or be explicitly converted prior to ingestion."
            )
        if not currencies:
            raise InvalidFinancialInputError("Cost items must specify an ISO 4217 currency code.")

        active_currency = next(iter(currencies))

        # Categorize items
        capex_items: List[CostItem] = []
        opex_items: List[CostItem] = []
        gross_capex_sum = 0.0
        upfront_subsidies_sum = 0.0
        annual_recurring_opex = 0.0
        replacement_schedule: Dict[int, float] = {}
        warnings: List[str] = []
        missing_inputs: List[str] = []

        has_panel_cost = False
        has_inverter_cost = False

        for item in cost_items:
            # Validate amounts and quantities
            if not math.isfinite(item.amount) or item.amount < 0.0:
                raise InvalidFinancialInputError(
                    f"Cost item '{item.name}' amount must be non-negative and finite, got {item.amount}."
                )
            if not math.isfinite(item.quantity) or item.quantity <= 0.0:
                raise InvalidFinancialInputError(
                    f"Cost item '{item.name}' quantity must be strictly positive, got {item.quantity}."
                )

            total_item_cost = float(item.amount * item.quantity)
            subcat = item.subcategory.strip().lower()
            cat = item.category.strip().upper()

            if cat == CostCategory.CAPEX.value:
                capex_items.append(item)
                if subcat == "subsidies":
                    upfront_subsidies_sum += total_item_cost
                else:
                    gross_capex_sum += total_item_cost
                    if subcat == "panels":
                        has_panel_cost = True
                    elif subcat == "inverter":
                        has_inverter_cost = True

            elif cat == CostCategory.OPEX.value:
                opex_items.append(item)
                if subcat == "replacement":
                    if item.replacement_year is None or item.replacement_year < 1:
                        raise InvalidFinancialInputError(
                            f"Replacement item '{item.name}' must specify a positive replacement_year."
                        )
                    yr = int(item.replacement_year)
                    replacement_schedule[yr] = replacement_schedule.get(yr, 0.0) + total_item_cost
                elif subcat == "residual":
                    residual_value = max(residual_value, total_item_cost)
                else:
                    annual_recurring_opex += total_item_cost
            else:
                raise InvalidFinancialInputError(
                    f"Unknown cost category '{item.category}' for item '{item.name}'. Must be CAPEX or OPEX."
                )

        # Enforce subsidy bound: S_up <= C_gross
        if upfront_subsidies_sum > gross_capex_sum:
            raise InvalidFinancialInputError(
                f"Upfront incentives/subsidies ({upfront_subsidies_sum:.2f} {active_currency}) cannot exceed "
                f"gross CAPEX ({gross_capex_sum:.2f} {active_currency})."
            )

        c_net = gross_capex_sum - upfront_subsidies_sum

        if not has_panel_cost:
            missing_inputs.append("panels_commercial_price")
            warnings.append(
                "Panel commercial cost was not supplied. Phase 6 catalogue contains null pricing. "
                "Gross CAPEX may be incomplete."
            )

        return SystemCostResult(
            c_gross=gross_capex_sum,
            s_upfront=upfront_subsidies_sum,
            c_net=c_net,
            currency=active_currency,
            rate_basis=rate_basis_enum.value,
            capex_items=capex_items,
            opex_items=opex_items,
            annual_base_opex=annual_recurring_opex,
            opex_escalation_rate=opex_escalation_rate,
            replacement_schedule=replacement_schedule,
            residual_value=residual_value,
            warnings=warnings,
            missing_inputs=missing_inputs,
        )

