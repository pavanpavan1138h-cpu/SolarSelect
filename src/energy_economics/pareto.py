"""
SolarSelect — Phase 8: Stage 9A Pareto Ranking Engine
Implements:
- Multi-objective Pareto dominance evaluation (maximize annual energy E_1, minimize LCOE/cost).
- Deterministic non-dominated sorting layers (pareto_rank = 1, 2, ...).
- Strict eligibility gate enforcement (RECOMMENDATION_ELIGIBLE / RECOMMENDATION_FLAGGED).
- Missing objective handling (NOT_COMPARABLE_MISSING_OBJECTIVE without zero substitution).
- Capacity support safeguards (quarantined exploratory annex for out-of-range systems; sparse flags).
- Energy-only single objective fallback mode when cost objectives are unpopulated.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import math

from src.energy_economics.exceptions import RankingError
from src.energy_economics.types import (
    ParetoStatus,
    ParetoCandidateResult,
    ParetoRankingResult,
    OverallRecommendationEligibility,
    CapacityEligibility,
)


class Phase8ParetoEngine:
    """
    Engine for Phase 8 Stage 9A multi-objective Pareto ranking.
    Conforms strictly to Section 4.8 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage9a_pareto_ranking"

    DEFAULT_ENERGY_OBJECTIVE = "annual_energy"
    DEFAULT_COST_OBJECTIVE = "lcoe"

    SUPPORTED_COST_OBJECTIVES = {
        "lcoe": "minimize",
        "capex_net": "minimize",
        "capex_gross": "minimize",
        "lifecycle_cost_npv": "minimize",
    }

    def __init__(self) -> None:
        pass

    def evaluate_pareto_ranking(
        self,
        candidates: List[Dict[str, Any]],
        cost_objective: str = "lcoe",
        energy_only: bool = False,
        allow_exploratory_annex: bool = False,
    ) -> ParetoRankingResult:
        """
        Executes Pareto dominance evaluation and non-dominated sorting.

        Args:
            candidates: List of evaluated candidate dictionary records.
            cost_objective: Cost metric to minimize ('lcoe', 'capex_net', 'capex_gross', 'lifecycle_cost_npv').
            energy_only: If True, executes single-objective energy ordering without cost optimization.
            allow_exploratory_annex: If True, segregates out-of-range candidates into a quarantined annex.

        Returns:
            ParetoRankingResult containing frontier 1, all ranked frontiers, candidate statuses, and disclaimers.
        """
        active_cost_obj = cost_objective.lower().strip()
        if not energy_only and active_cost_obj not in self.SUPPORTED_COST_OBJECTIVES:
            raise RankingError(
                f"Unsupported cost_objective: '{cost_objective}'. "
                f"Must be one of {sorted(list(self.SUPPORTED_COST_OBJECTIVES.keys()))}."
            )

        cost_direction = self.SUPPORTED_COST_OBJECTIVES.get(active_cost_obj, "minimize")
        warnings: List[str] = []
        quarantined_annex: List[Dict[str, Any]] = []

        if energy_only:
            warnings.append(
                "ENERGY_ONLY: Pareto ranking executed in single-objective energy ordering mode. "
                "Economic cost optimization was not performed; highest energy does not imply lowest cost."
            )

        evaluated_candidates: Dict[str, ParetoCandidateResult] = {}
        eligible_for_ranking: List[Dict[str, Any]] = []

        # 1. Triage candidates by Eligibility and Capacity Support
        for cand in candidates:
            cfg_id = str(cand.get("configuration_id", f"candidate_{len(evaluated_candidates)}"))
            feas = cand.get("feasibility") or {}

            # Parse overall recommendation eligibility
            overall_elig = feas.get("overall_recommendation_eligibility")
            if isinstance(overall_elig, OverallRecommendationEligibility):
                overall_elig_val = overall_elig.value
            else:
                overall_elig_val = str(overall_elig) if overall_elig else "RECOMMENDATION_NOT_EVALUATED"

            # Parse capacity eligibility
            cap_elig = feas.get("capacity_eligibility")
            if isinstance(cap_elig, CapacityEligibility):
                cap_elig_val = cap_elig.value
            else:
                cap_elig_val = str(cap_elig) if cap_elig else "CAPACITY_INELIGIBLE_UNAVAILABLE"

            sparse_flag = (
                cap_elig_val == CapacityEligibility.CAPACITY_FLAGGED_SPARSE.value or
                overall_elig_val == OverallRecommendationEligibility.RECOMMENDATION_FLAGGED.value
            )

            # Extract objective values
            e1 = self._extract_energy_objective(cand)
            cost_val = self._extract_cost_objective(cand, active_cost_obj) if not energy_only else None

            # Check capacity out-of-range quarantine
            if cap_elig_val == CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE.value:
                if allow_exploratory_annex:
                    quarantined_annex.append({
                        "configuration_id": cfg_id,
                        "installed_dc_capacity_kwp": cand.get("installed_dc_capacity_kwp"),
                        "annual_energy_kwh": e1,
                        "cost_objective_value": cost_val,
                        "pareto_status": ParetoStatus.EXTRAPOLATED_CAPACITY_QUARANTINED.value,
                        "disclaimer": (
                            "QUARANTINED EXPLORATORY RECORD: Candidate capacity is out of the authoritative "
                            "training distribution range [21.39 - 539.80 kWp]. Unvalidated extrapolation; "
                            "must not be used as a production recommendation."
                        ),
                    })
                    evaluated_candidates[cfg_id] = ParetoCandidateResult(
                        configuration_id=cfg_id,
                        pareto_rank=None,
                        pareto_status=ParetoStatus.EXTRAPOLATED_CAPACITY_QUARANTINED.value,
                        is_non_dominated=False,
                        annual_energy_kwh=e1,
                        cost_objective_value=cost_val,
                        cost_objective_name=active_cost_obj,
                        sparse_support_flag=False,
                        exclusion_reason="Capacity is out of training range [21.39 - 539.80 kWp].",
                        warnings=["EXTRAPOLATED_CAPACITY_QUARANTINED"],
                    )
                    continue
                else:
                    evaluated_candidates[cfg_id] = ParetoCandidateResult(
                        configuration_id=cfg_id,
                        pareto_rank=None,
                        pareto_status=ParetoStatus.EXCLUDED_UNSUPPORTED_CAPACITY.value,
                        is_non_dominated=False,
                        annual_energy_kwh=e1,
                        cost_objective_value=cost_val,
                        cost_objective_name=active_cost_obj,
                        sparse_support_flag=False,
                        exclusion_reason="Excluded from primary Pareto ranking: capacity out of training range.",
                    )
                    continue

            # Check overall recommendation eligibility
            if overall_elig_val == OverallRecommendationEligibility.RECOMMENDATION_INELIGIBLE.value:
                evaluated_candidates[cfg_id] = ParetoCandidateResult(
                    configuration_id=cfg_id,
                    pareto_rank=None,
                    pareto_status=ParetoStatus.EXCLUDED_INELIGIBLE.value,
                    is_non_dominated=False,
                    annual_energy_kwh=e1,
                    cost_objective_value=cost_val,
                    cost_objective_name=active_cost_obj,
                    sparse_support_flag=sparse_flag,
                    exclusion_reason=f"Hard feasibility gate failure: first failed stage was {feas.get('first_failed_stage')}.",
                )
                continue

            if overall_elig_val == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value:
                evaluated_candidates[cfg_id] = ParetoCandidateResult(
                    configuration_id=cfg_id,
                    pareto_rank=None,
                    pareto_status=ParetoStatus.NOT_EVALUATED_UNRESOLVED_GATES.value,
                    is_non_dominated=False,
                    annual_energy_kwh=e1,
                    cost_objective_value=cost_val,
                    cost_objective_name=active_cost_obj,
                    sparse_support_flag=sparse_flag,
                    exclusion_reason="Mandatory feasibility or prediction gates remain unevaluated.",
                )
                continue

            # Candidate is eligible or flagged: verify required objectives
            if e1 is None:
                evaluated_candidates[cfg_id] = ParetoCandidateResult(
                    configuration_id=cfg_id,
                    pareto_rank=None,
                    pareto_status=ParetoStatus.NOT_COMPARABLE_MISSING_OBJECTIVE.value,
                    is_non_dominated=False,
                    annual_energy_kwh=None,
                    cost_objective_value=cost_val,
                    cost_objective_name=active_cost_obj,
                    sparse_support_flag=sparse_flag,
                    exclusion_reason="Missing annual energy generation objective (E_1 is None).",
                )
                continue

            if not energy_only and cost_val is None:
                evaluated_candidates[cfg_id] = ParetoCandidateResult(
                    configuration_id=cfg_id,
                    pareto_rank=None,
                    pareto_status=ParetoStatus.NOT_COMPARABLE_MISSING_OBJECTIVE.value,
                    is_non_dominated=False,
                    annual_energy_kwh=e1,
                    cost_objective_value=None,
                    cost_objective_name=active_cost_obj,
                    sparse_support_flag=sparse_flag,
                    exclusion_reason=f"Missing cost objective '{active_cost_obj}' (value is None).",
                )
                continue

            # Candidate is comparable and eligible
            eligible_for_ranking.append({
                "cfg_id": cfg_id,
                "e1": float(e1),
                "cost": float(cost_val) if cost_val is not None else 0.0,
                "sparse_flag": sparse_flag,
            })

        # 2. Execute Ranking
        fronts: List[List[str]] = []
        pareto_set: List[str] = []

        if energy_only:
            # Single objective descending sort by e1
            eligible_for_ranking.sort(key=lambda x: (-x["e1"], x["cfg_id"]))
            ranked_front = [c["cfg_id"] for c in eligible_for_ranking]
            if ranked_front:
                fronts = [ranked_front]
                pareto_set = [ranked_front[0]]  # Top energy candidate

            for rank_idx, item in enumerate(eligible_for_ranking, start=1):
                cid = item["cfg_id"]
                warns = []
                if item["sparse_flag"]:
                    warns.append("SPARSE_SUPPORT_FLAG: Candidate capacity lies in sparse training band [100 - 539.8 kWp].")
                evaluated_candidates[cid] = ParetoCandidateResult(
                    configuration_id=cid,
                    pareto_rank=rank_idx,
                    pareto_status=ParetoStatus.RANKED.value,
                    is_non_dominated=(rank_idx == 1),
                    annual_energy_kwh=item["e1"],
                    cost_objective_value=None,
                    cost_objective_name="none_energy_only",
                    sparse_support_flag=item["sparse_flag"],
                    warnings=warns,
                )

        else:
            # Non-dominated sorting
            # Compute dominance relationships
            dominates: Dict[str, List[str]] = {c["cfg_id"]: [] for c in eligible_for_ranking}
            dominated_by: Dict[str, List[str]] = {c["cfg_id"]: [] for c in eligible_for_ranking}

            n = len(eligible_for_ranking)
            for i in range(n):
                cand_a = eligible_for_ranking[i]
                id_a = cand_a["cfg_id"]
                for j in range(i + 1, n):
                    cand_b = eligible_for_ranking[j]
                    id_b = cand_b["cfg_id"]

                    a_dom_b = self._dominates(cand_a, cand_b)
                    b_dom_a = self._dominates(cand_b, cand_a)

                    if a_dom_b and not b_dom_a:
                        dominates[id_a].append(id_b)
                        dominated_by[id_b].append(id_a)
                    elif b_dom_a and not a_dom_b:
                        dominates[id_b].append(id_a)
                        dominated_by[id_a].append(id_b)

            # Peeling non-dominated frontiers
            remaining = set(c["cfg_id"] for c in eligible_for_ranking)
            current_rank = 1

            while remaining:
                current_front = [
                    cid for cid in remaining if len(set(dominated_by[cid]).intersection(remaining)) == 0
                ]
                if not current_front:
                    # In case of cycles (mathematically impossible with partial orders, but for absolute safety)
                    current_front = sorted(list(remaining))

                # Deterministic sorting within front by energy descending, then config_id
                cand_map = {c["cfg_id"]: c for c in eligible_for_ranking}
                current_front.sort(key=lambda x: (-cand_map[x]["e1"], cand_map[x]["cost"], x))

                fronts.append(current_front)
                if current_rank == 1:
                    pareto_set = list(current_front)

                for cid in current_front:
                    cand_data = cand_map[cid]
                    warns = []
                    if cand_data["sparse_flag"]:
                        warns.append("SPARSE_SUPPORT_FLAG: Candidate capacity lies in sparse training band [100 - 539.8 kWp].")

                    evaluated_candidates[cid] = ParetoCandidateResult(
                        configuration_id=cid,
                        pareto_rank=current_rank,
                        pareto_status=ParetoStatus.RANKED.value,
                        is_non_dominated=(current_rank == 1),
                        annual_energy_kwh=cand_data["e1"],
                        cost_objective_value=cand_data["cost"],
                        cost_objective_name=active_cost_obj,
                        sparse_support_flag=cand_data["sparse_flag"],
                        dominated_by=sorted(dominated_by[cid]),
                        dominates=sorted(dominates[cid]),
                        warnings=warns,
                    )
                    remaining.remove(cid)

                current_rank += 1

        return ParetoRankingResult(
            pareto_set=pareto_set,
            fronts=fronts,
            candidates=evaluated_candidates,
            cost_objective_name=active_cost_obj if not energy_only else "none_energy_only",
            cost_objective_direction=cost_direction,
            energy_only_mode=energy_only,
            quarantined_annex=quarantined_annex,
            warnings=warnings,
            metadata={
                "n_total_candidates": len(candidates),
                "n_eligible_ranked": len(eligible_for_ranking),
                "n_frontiers": len(fronts),
            },
        )

    def _dominates(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """
        Tests if candidate A Pareto-dominates candidate B.
        A dominates B iff E1(A) >= E1(B) and Cost(A) <= Cost(B), with at least one strict inequality.
        """
        e_a, c_a = a["e1"], a["cost"]
        e_b, c_b = b["e1"], b["cost"]

        # Maximise energy, minimise cost
        energy_better_or_equal = (e_a >= e_b)
        cost_better_or_equal = (c_a <= c_b)

        at_least_one_strict = (e_a > e_b) or (c_a < c_b)

        return energy_better_or_equal and cost_better_or_equal and at_least_one_strict

    def _extract_energy_objective(self, cand: Dict[str, Any]) -> Optional[float]:
        """Extracts annual energy generation E_1 in kWh/yr from candidate record."""
        # Check 'energy' subdict first
        eng = cand.get("energy")
        if isinstance(eng, dict):
            if eng.get("e_year1_kwh") is not None:
                return float(eng["e_year1_kwh"])
            if eng.get("annual_energy_kwh") is not None:
                return float(eng["annual_energy_kwh"])

        # Direct candidate attributes
        if cand.get("annual_energy_kwh") is not None:
            return float(cand["annual_energy_kwh"])
        if cand.get("e_year1_kwh") is not None:
            return float(cand["e_year1_kwh"])

        return None

    def _extract_cost_objective(self, cand: Dict[str, Any], cost_obj_name: str) -> Optional[float]:
        """Extracts selected cost objective value from candidate record."""
        fin = cand.get("financials")
        costs = cand.get("costs")

        if cost_obj_name == "lcoe":
            if isinstance(fin, dict) and fin.get("lcoe") is not None:
                return float(fin["lcoe"])
            if isinstance(fin, dict) and fin.get("lcoe_per_kwh") is not None:
                return float(fin["lcoe_per_kwh"])
            if cand.get("lcoe_per_kwh") is not None:
                return float(cand["lcoe_per_kwh"])
            if cand.get("lcoe") is not None:
                return float(cand["lcoe"])

        elif cost_obj_name == "capex_net":
            if isinstance(fin, dict) and fin.get("capex_net") is not None:
                return float(fin["capex_net"])
            if isinstance(costs, dict) and costs.get("c_net") is not None:
                return float(costs["c_net"])
            if cand.get("c_net") is not None:
                return float(cand["c_net"])

        elif cost_obj_name == "capex_gross":
            if isinstance(fin, dict) and fin.get("capex_gross") is not None:
                return float(fin["capex_gross"])
            if isinstance(costs, dict) and costs.get("c_gross") is not None:
                return float(costs["c_gross"])
            if cand.get("c_gross") is not None:
                return float(cand["c_gross"])

        elif cost_obj_name == "lifecycle_cost_npv":
            if isinstance(fin, dict) and fin.get("npv") is not None:
                return float(fin["npv"])
            if cand.get("npv") is not None:
                return float(cand["npv"])

        return None

