"""
SolarSelect — Phase 8: Stage 10 Recommendation & Explanation Engine
Implements:
- Authoritative recommendation selection across pareto, weighted, energy-only, and none bases.
- Rigorous eligibility gate enforcement (never recommends ineligible or unevaluated candidates).
- Structured transparent explanation generation (selection rationale, non-selected reasons).
- Explicit Pareto vs Weighted ranking alignment analysis (CONSENSUS vs DIVERGENT trade-off trade study).
- Scientific caveat generation preserving B-1, B-2, and unpopulated commercial/electrical boundaries.
- Strict compliance with Phase 8 Section 6 Output Schema Contract.
"""

from typing import Dict, Any, List, Optional, Tuple, Union

from src.energy_economics.exceptions import RecommendationError
from src.energy_economics.types import (
    RecommendationBasis,
    RecommendationExplanation,
    RecommendationResult,
    ParetoRankingResult,
    WeightedRankingResult,
    OverallRecommendationEligibility,
    CapacityEligibility,
)


class Phase8RecommendationEngine:
    """
    Engine for Phase 8 Stage 10 recommendation selection and transparent explanation synthesis.
    Conforms strictly to Section 4.7, 4.8, 4.9, and Section 6 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage10_recommendation_and_explanation"

    CAVEAT_B1_ENERGY_BASIS = (
        "Phase 5 model target (kWh/kWp/day) documentation states an AC kWh basis, "
        "but original raw telemetry cannot independently verify whether measurements reflect AC gross, "
        "AC net, or DC metering point. Retained as UNVERIFIED under Blocking Issue B-1."
    )

    CAVEAT_B2_PROSPECTIVE_ROOFS = (
        "Prospective candidate roofs lack physical historical telemetry and cannot generate lagged features "
        "without an authorized lag policy (Blocking Issue B-2: PREDICTION_PENDING_LAG_POLICY)."
    )

    CAVEAT_COMMERCIAL_PRICING = (
        "Phase 6 panel catalogue records contain null commercial pricing. Financial evaluations depend entirely "
        "on user-supplied cost quotations; system costs are unverified against market benchmarks."
    )

    CAVEAT_ELECTRICAL_COMPATIBILITY = (
        "Inverter specifications and engineered stringing layouts are not populated in repository catalogues. "
        "Real candidate compatibility remains NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS; installation approval "
        "requires licensed electrical engineering verification."
    )

    CAVEAT_FINANCIAL_RETURNS = (
        "Financial metrics (NPV, LCOE, Payback) represent conditional deterministic simulation scenarios, "
        "not guaranteed commercial yields, returns, or tariff continuity."
    )

    def __init__(self) -> None:
        pass

    def evaluate_recommendation(
        self,
        candidates: List[Dict[str, Any]],
        pareto_result: ParetoRankingResult,
        weighted_result: Optional[WeightedRankingResult] = None,
        basis: Union[RecommendationBasis, str] = RecommendationBasis.PARETO,
        preferred_tradeoff: Optional[str] = None,
        user_notes: Optional[str] = None,
    ) -> RecommendationResult:
        """
        Synthesizes ranking outcomes into an authoritative recommendation and explanation.

        Args:
            candidates: List of evaluated candidate dictionary records.
            pareto_result: Computed ParetoRankingResult from Phase8ParetoEngine.
            weighted_result: Optional computed WeightedRankingResult from Phase8WeightedRankingEngine.
            basis: RecommendationBasis ('pareto', 'weighted', 'energy_only', 'none').
            preferred_tradeoff: Optional preference for Pareto selection ('min_cost', 'max_energy', or config_id).
            user_notes: Optional designer or site context.

        Returns:
            RecommendationResult conforming strictly to Section 6 schema.
        """
        # 1. Parse recommendation basis
        if isinstance(basis, str):
            try:
                basis_enum = RecommendationBasis(basis.lower().strip())
            except ValueError:
                raise RecommendationError(
                    f"Unsupported recommendation basis: '{basis}'. "
                    f"Must be one of {[b.value for b in RecommendationBasis]}."
                )
        else:
            basis_enum = basis

        # Index candidates by configuration_id
        cand_map: Dict[str, Dict[str, Any]] = {}
        for c in candidates:
            cid = str(c.get("configuration_id", f"candidate_{len(cand_map)}"))
            cand_map[cid] = c

        # 2. Check Overall Eligibility across Candidate Pool
        eligible_candidates = [
            cid for cid, c in cand_map.items()
            if self._get_overall_eligibility(c) in (
                OverallRecommendationEligibility.RECOMMENDATION_ELIGIBLE.value,
                OverallRecommendationEligibility.RECOMMENDATION_FLAGGED.value,
            )
        ]

        has_unevaluated = any(
            self._get_overall_eligibility(c) == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value
            for c in cand_map.values()
        )

        recommended_cid: Optional[str] = None
        recommendation_status: str = OverallRecommendationEligibility.RECOMMENDATION_ELIGIBLE.value

        if not eligible_candidates:
            if has_unevaluated:
                recommendation_status = OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value
            else:
                recommendation_status = "NONE_ELIGIBLE"

            explanation = self._build_no_candidate_explanation(
                candidates=cand_map,
                pareto_result=pareto_result,
                weighted_result=weighted_result,
                has_unevaluated=has_unevaluated,
            )
            return RecommendationResult(
                configuration_id=None,
                basis=basis_enum.value,
                overall_recommendation_eligibility=recommendation_status,
                explanation=explanation,
                caveats=self._build_caveats(has_unevaluated=has_unevaluated),
                metadata={"status": "NO_ELIGIBLE_RECOMMENDATION"},
            )

        # 3. Select Winning Candidate based on Basis
        if basis_enum == RecommendationBasis.NONE:
            recommendation_status = "NONE_ELIGIBLE"
            explanation = RecommendationExplanation(
                summary="Recommendation basis set to 'none'; no automated selection performed.",
                selection_rationale="User explicitly designated recommendation basis as 'none'.",
                non_selected_rationales={},
                pareto_vs_weighted_alignment="N/A",
                alignment_status="NOT_APPLICABLE",
                tradeoff_analysis="No trade-off analysis performed.",
                caveats=self._build_caveats(),
            )
            return RecommendationResult(
                configuration_id=None,
                basis=RecommendationBasis.NONE.value,
                overall_recommendation_eligibility=recommendation_status,
                explanation=explanation,
                caveats=self._build_caveats(),
            )

        elif basis_enum == RecommendationBasis.PARETO:
            if not pareto_result.pareto_set:
                recommendation_status = "NONE_ELIGIBLE"
            else:
                front1 = pareto_result.pareto_set
                # Apply preferred tradeoff if supplied
                if preferred_tradeoff:
                    pref = preferred_tradeoff.strip().lower()
                    if pref in [cid.lower() for cid in front1]:
                        recommended_cid = next(cid for cid in front1 if cid.lower() == pref)
                    elif pref == "min_cost":
                        # Find candidate with minimum cost on front 1
                        costs = {
                            cid: pareto_result.candidates[cid].cost_objective_value
                            for cid in front1
                            if pareto_result.candidates[cid].cost_objective_value is not None
                        }
                        if costs:
                            recommended_cid = min(costs.keys(), key=lambda k: costs[k])
                        else:
                            recommended_cid = front1[0]
                    elif pref == "max_energy":
                        # Find candidate with maximum energy on front 1
                        energies = {
                            cid: pareto_result.candidates[cid].annual_energy_kwh
                            for cid in front1
                            if pareto_result.candidates[cid].annual_energy_kwh is not None
                        }
                        if energies:
                            recommended_cid = max(energies.keys(), key=lambda k: energies[k])
                        else:
                            recommended_cid = front1[0]
                    else:
                        recommended_cid = front1[0]
                else:
                    recommended_cid = front1[0]

        elif basis_enum == RecommendationBasis.WEIGHTED:
            if weighted_result is None or not weighted_result.ranked_order:
                raise RecommendationError(
                    "Recommendation basis is 'weighted', but valid weighted_result was not supplied."
                )
            recommended_cid = weighted_result.ranked_order[0]

        elif basis_enum == RecommendationBasis.ENERGY_ONLY:
            # Select leading candidate by energy
            if pareto_result.pareto_set:
                recommended_cid = pareto_result.pareto_set[0]
            else:
                recommendation_status = "NONE_ELIGIBLE"

        # Resolve status of recommended configuration
        if recommended_cid is not None:
            winning_cand = cand_map[recommended_cid]
            recommendation_status = self._get_overall_eligibility(winning_cand)

        # 4. Synthesize Explanations
        explanation = self._build_explanation(
            recommended_cid=recommended_cid,
            cand_map=cand_map,
            pareto_result=pareto_result,
            weighted_result=weighted_result,
            basis=basis_enum.value,
        )

        return RecommendationResult(
            configuration_id=recommended_cid,
            basis=basis_enum.value,
            overall_recommendation_eligibility=recommendation_status,
            explanation=explanation,
            caveats=self._build_caveats(),
            metadata={
                "basis_used": basis_enum.value,
                "n_eligible_candidates": len(eligible_candidates),
                "preferred_tradeoff": preferred_tradeoff,
            },
        )

    def _get_overall_eligibility(self, cand: Dict[str, Any]) -> str:
        """Helper to extract overall_recommendation_eligibility string."""
        feas = cand.get("feasibility") or {}
        elig = feas.get("overall_recommendation_eligibility")
        if isinstance(elig, OverallRecommendationEligibility):
            return elig.value
        return str(elig) if elig else "RECOMMENDATION_NOT_EVALUATED"

    def _build_caveats(self, has_unevaluated: bool = False) -> List[str]:
        """Constructs list of applicable scientific caveats."""
        c = [
            self.CAVEAT_B1_ENERGY_BASIS,
            self.CAVEAT_B2_PROSPECTIVE_ROOFS,
            self.CAVEAT_COMMERCIAL_PRICING,
            self.CAVEAT_ELECTRICAL_COMPATIBILITY,
            self.CAVEAT_FINANCIAL_RETURNS,
        ]
        if has_unevaluated:
            c.append(
                "MANDATORY GATES UNEVALUATED: One or more candidates have unevaluated feasibility, electrical, "
                "or prediction requirements. No candidate can be recommended without complete gate evaluation."
            )
        return c

    def _build_explanation(
        self,
        recommended_cid: Optional[str],
        cand_map: Dict[str, Dict[str, Any]],
        pareto_result: ParetoRankingResult,
        weighted_result: Optional[WeightedRankingResult],
        basis: str,
    ) -> RecommendationExplanation:
        """Formulates structured explanation covering selection, non-selection, alignment, and trade-offs."""
        if recommended_cid is None:
            return RecommendationExplanation(
                summary="No candidate configuration qualified for recommendation.",
                selection_rationale="Zero candidates passed all mandatory feasibility and eligibility gates.",
                non_selected_rationales={cid: "Ineligible or unevaluated." for cid in cand_map.keys()},
                pareto_vs_weighted_alignment="N/A",
                alignment_status="NOT_APPLICABLE",
                tradeoff_analysis="No trade-off analysis feasible.",
                caveats=self._build_caveats(),
            )

        win_cand = cand_map[recommended_cid]
        win_pareto = pareto_result.candidates.get(recommended_cid)
        win_weighted = weighted_result.candidates.get(recommended_cid) if weighted_result else None

        e1_val = win_pareto.annual_energy_kwh if win_pareto else None
        cost_val = win_pareto.cost_objective_value if win_pareto else None
        cost_name = pareto_result.cost_objective_name

        # A. Selection Rationale
        selection_parts = [
            f"Configuration '{recommended_cid}' was selected under the '{basis}' basis.",
            f"Feasibility: Passed all evaluated geometric and physical gates.",
            f"Annual Energy Generation (E_1): {e1_val:.2f} kWh/yr." if e1_val is not None else "Annual energy unpopulated.",
        ]
        if cost_val is not None:
            selection_parts.append(f"Cost Objective ({cost_name}): {cost_val:.4f}.")
        if win_pareto and win_pareto.pareto_rank is not None:
            selection_parts.append(f"Pareto Status: Non-dominated on Frontier {win_pareto.pareto_rank}.")
        if win_weighted and win_weighted.weighted_rank is not None:
            selection_parts.append(f"Weighted Score: {win_weighted.weighted_score:.4f} (Rank {win_weighted.weighted_rank}).")
        if win_pareto and win_pareto.sparse_support_flag:
            selection_parts.append("Warning: Candidate capacity lies in sparse training band [100 - 539.8 kWp].")

        selection_rationale = " ".join(selection_parts)

        # B. Non-Selected Rationales
        non_selected: Dict[str, str] = {}
        for cid, c in cand_map.items():
            if cid == recommended_cid:
                continue

            par_c = pareto_result.candidates.get(cid)
            wt_c = weighted_result.candidates.get(cid) if weighted_result else None
            feas = c.get("feasibility") or {}

            reasons = []
            if feas.get("overall_recommendation_eligibility") == OverallRecommendationEligibility.RECOMMENDATION_INELIGIBLE.value:
                reasons.append(f"Ineligible due to failure at {feas.get('first_failed_stage')} stage.")
            elif feas.get("overall_recommendation_eligibility") == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value:
                reasons.append("Excluded because mandatory feasibility or prediction gates remain unevaluated.")
            elif par_c and par_c.pareto_status == "NOT_COMPARABLE_MISSING_OBJECTIVE":
                reasons.append(f"Excluded from ranking: {par_c.exclusion_reason}")
            elif par_c and not par_c.is_non_dominated:
                reasons.append(f"Pareto-dominated on Frontier {par_c.pareto_rank} (dominated by {par_c.dominated_by}).")
            elif wt_c and wt_c.weighted_rank is not None:
                reasons.append(f"Ranked lower under weighted multi-criteria scoring (Rank {wt_c.weighted_rank}, Score {wt_c.weighted_score:.4f}).")
            else:
                reasons.append("Did not achieve non-dominated status or highest weighted score.")

            non_selected[cid] = " ".join(reasons)

        # C. Pareto vs Weighted Alignment
        pareto_leader = pareto_result.pareto_set[0] if pareto_result.pareto_set else None
        weighted_leader = weighted_result.ranked_order[0] if weighted_result and weighted_result.ranked_order else None

        if pareto_leader and weighted_leader:
            if pareto_leader == weighted_leader:
                alignment_status = "CONSENSUS"
                alignment_str = (
                    f"Consensus achieved: Both Pareto dominance (Frontier 1) and weighted multi-criteria ranking "
                    f"independently identify configuration '{pareto_leader}' as the top candidate."
                )
                tradeoff_str = (
                    f"Configuration '{pareto_leader}' represents an unambiguously superior trade-off "
                    "that maximizes energy while maintaining optimal cost efficiency under the specified weights."
                )
            else:
                alignment_status = "DIVERGENT"
                alignment_str = (
                    f"Method divergence: Pareto analysis identified a multi-candidate frontier containing '{pareto_leader}', "
                    f"while weighted multi-criteria ranking selected '{weighted_leader}'."
                )
                tradeoff_str = (
                    f"The Pareto frontier contains mutually non-dominated trade-offs. Configuration '{pareto_leader}' "
                    f"maximizes raw generation, whereas '{weighted_leader}' was prioritized by the user-supplied "
                    f"weight distribution ({weighted_result.weights if weighted_result else ''})."
                )
        else:
            alignment_status = "NOT_APPLICABLE"
            alignment_str = "Pareto vs weighted alignment could not be evaluated due to incomplete ranking results."
            tradeoff_str = "No trade-off divergence analysis possible."

        summary = f"Selected configuration '{recommended_cid}' under '{basis}' basis ({alignment_status})."

        return RecommendationExplanation(
            summary=summary,
            selection_rationale=selection_rationale,
            non_selected_rationales=non_selected,
            pareto_vs_weighted_alignment=alignment_str,
            alignment_status=alignment_status,
            tradeoff_analysis=tradeoff_str,
            caveats=self._build_caveats(),
        )

    def _build_no_candidate_explanation(
        self,
        candidates: Dict[str, Dict[str, Any]],
        pareto_result: ParetoRankingResult,
        weighted_result: Optional[WeightedRankingResult],
        has_unevaluated: bool,
    ) -> RecommendationExplanation:
        """Constructs explanation when zero candidates qualify for recommendation."""
        if has_unevaluated:
            sum_str = "No configuration can be recommended because mandatory feasibility and prediction gates remain unevaluated."
            sel_str = (
                "Under SolarSelect governance, unevaluated gates (including prospective lag feature policy B-2 "
                "and unpopulated inverter specifications) strictly evaluate to RECOMMENDATION_NOT_EVALUATED. "
                "Candidates cannot be recommended without complete empirical verification."
            )
        else:
            sum_str = "Zero candidate configurations satisfied the hard feasibility criteria."
            sel_str = "All evaluated candidates failed one or more mandatory feasibility gates (geometry, catalogue, capacity, or cost)."

        non_sel = {}
        for cid, c in candidates.items():
            feas = c.get("feasibility") or {}
            non_sel[cid] = (
                f"Overall status: {feas.get('overall_recommendation_eligibility')}; "
                f"first failed stage: {feas.get('first_failed_stage')}."
            )

        return RecommendationExplanation(
            summary=sum_str,
            selection_rationale=sel_str,
            non_selected_rationales=non_sel,
            pareto_vs_weighted_alignment="N/A",
            alignment_status="NOT_APPLICABLE",
            tradeoff_analysis="No candidates eligible for trade-off evaluation.",
            caveats=self._build_caveats(has_unevaluated=has_unevaluated),
        )

