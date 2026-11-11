"""
SolarSelect — Phase 8: Stage 9B Weighted Ranking Engine
Implements:
- User-configurable multi-criteria weighted scoring: S = sum(w_k * z_k).
- Min-max linear normalisation for maximization and minimization criteria.
- Zero-discrimination detection when x_max == x_min (z = 1.0 for all candidates).
- Strict weight validation (w_k >= 0, sum(w_k) == 1.0 +/- 1e-9; no implicit defaults).
- Strict candidate exclusion on missing criteria (no zero-substitution, no per-candidate weight re-normalisation).
- Eligibility gate enforcement (RECOMMENDATION_ELIGIBLE / RECOMMENDATION_FLAGGED).
- Full reproducibility specification (normalisation bounds, weights, candidate set bounds).
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import math

from src.energy_economics.exceptions import RankingError
from src.energy_economics.types import (
    WeightedRankingStatus,
    WeightedCandidateResult,
    WeightedRankingResult,
    OverallRecommendationEligibility,
    CapacityEligibility,
)


class Phase8WeightedRankingEngine:
    """
    Engine for Phase 8 Stage 9B multi-criteria weighted scoring and ranking.
    Conforms strictly to Section 4.9 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage9b_weighted_ranking"

    DEFAULT_CRITERIA_DIRECTIONS = {
        "annual_energy": "maximize",
        "lcoe": "minimize",
        "capex_net": "minimize",
        "capex_gross": "minimize",
        "npv": "maximize",
    }

    REPRODUCIBILITY_NOTE = (
        "Weighted ranking scores depend strictly on the candidate set and its empirical min-max bounds. "
        "Scores and ranks cannot be directly compared across runs with different candidate pools or bounds."
    )

    def __init__(self) -> None:
        pass

    def evaluate_weighted_ranking(
        self,
        candidates: List[Dict[str, Any]],
        weights: Dict[str, float],
        criteria_directions: Optional[Dict[str, str]] = None,
    ) -> WeightedRankingResult:
        """
        Executes multi-criteria normalisation, scoring, and ranking.

        Args:
            candidates: List of evaluated candidate dictionary records.
            weights: User-supplied dictionary mapping criterion name to weight (must sum to 1.0).
            criteria_directions: Optional mapping of criterion name to 'maximize' or 'minimize'.

        Returns:
            WeightedRankingResult with ranked candidate order, normalisation bounds, and reproducibility data.
        """
        # 1. Validate weights
        if not weights:
            raise RankingError(
                "weights dictionary must be explicitly provided. Default weights are not defined under Decision D-5."
            )

        weight_sum = 0.0
        active_weights: Dict[str, float] = {}
        for criterion, w in weights.items():
            try:
                w_val = float(w)
            except (ValueError, TypeError) as e:
                raise RankingError(f"Weight for '{criterion}' must be a valid float: {e}") from e

            if not math.isfinite(w_val) or w_val < 0.0:
                raise RankingError(f"Weight for '{criterion}' must be a non-negative finite number, got {w_val}.")

            active_weights[criterion.strip().lower()] = w_val
            weight_sum += w_val

        if abs(weight_sum - 1.0) > 1e-9:
            raise RankingError(
                f"Weights must sum to exactly 1.0 (+/- 1e-9); sum is {weight_sum:.10f}."
            )

        # 2. Resolve criteria directions
        active_directions: Dict[str, str] = {}
        for criterion in active_weights.keys():
            if criteria_directions and criterion in criteria_directions:
                d = criteria_directions[criterion].strip().lower()
                if d not in ("maximize", "minimize"):
                    raise RankingError(f"Direction for '{criterion}' must be 'maximize' or 'minimize', got '{d}'.")
                active_directions[criterion] = d
            elif criterion in self.DEFAULT_CRITERIA_DIRECTIONS:
                active_directions[criterion] = self.DEFAULT_CRITERIA_DIRECTIONS[criterion]
            else:
                raise RankingError(
                    f"Unsupported criterion '{criterion}' without explicit direction. "
                    f"Supported default criteria: {sorted(list(self.DEFAULT_CRITERIA_DIRECTIONS.keys()))}."
                )

        # 3. Triage candidates by Eligibility & Criteria Availability
        evaluated_candidates: Dict[str, WeightedCandidateResult] = {}
        eligible_candidates: List[Dict[str, Any]] = []
        excluded_candidates: List[Dict[str, Any]] = []

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

            # Check capacity out-of-range
            if cap_elig_val == CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE.value:
                reason = "Capacity is out of training range [21.39 - 539.80 kWp]."
                excluded_candidates.append({"configuration_id": cfg_id, "reason": reason, "status": WeightedRankingStatus.EXCLUDED_UNSUPPORTED_CAPACITY.value})
                evaluated_candidates[cfg_id] = WeightedCandidateResult(
                    configuration_id=cfg_id,
                    weighted_rank=None,
                    weighted_score=None,
                    weighted_status=WeightedRankingStatus.EXCLUDED_UNSUPPORTED_CAPACITY.value,
                    raw_criteria_values={},
                    normalized_criteria_values={},
                    sparse_support_flag=False,
                    exclusion_reason=reason,
                )
                continue

            # Check overall recommendation eligibility
            if overall_elig_val == OverallRecommendationEligibility.RECOMMENDATION_INELIGIBLE.value:
                reason = f"Hard feasibility gate failure (first failed stage: {feas.get('first_failed_stage')})."
                excluded_candidates.append({"configuration_id": cfg_id, "reason": reason, "status": WeightedRankingStatus.EXCLUDED_INELIGIBLE.value})
                evaluated_candidates[cfg_id] = WeightedCandidateResult(
                    configuration_id=cfg_id,
                    weighted_rank=None,
                    weighted_score=None,
                    weighted_status=WeightedRankingStatus.EXCLUDED_INELIGIBLE.value,
                    raw_criteria_values={},
                    normalized_criteria_values={},
                    sparse_support_flag=sparse_flag,
                    exclusion_reason=reason,
                )
                continue

            if overall_elig_val == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value:
                reason = "Mandatory feasibility or prediction gates remain unevaluated."
                excluded_candidates.append({"configuration_id": cfg_id, "reason": reason, "status": WeightedRankingStatus.EXCLUDED_UNRESOLVED_GATES.value})
                evaluated_candidates[cfg_id] = WeightedCandidateResult(
                    configuration_id=cfg_id,
                    weighted_rank=None,
                    weighted_score=None,
                    weighted_status=WeightedRankingStatus.EXCLUDED_UNRESOLVED_GATES.value,
                    raw_criteria_values={},
                    normalized_criteria_values={},
                    sparse_support_flag=sparse_flag,
                    exclusion_reason=reason,
                )
                continue

            # Extract criteria values
            raw_vals: Dict[str, Optional[float]] = {}
            missing_criteria = []

            for crit in active_weights.keys():
                val = self._extract_criterion_value(cand, crit)
                raw_vals[crit] = val
                if val is None or not math.isfinite(val):
                    missing_criteria.append(crit)

            if missing_criteria:
                reason = f"Missing selected criteria: {missing_criteria}."
                excluded_candidates.append({"configuration_id": cfg_id, "reason": reason, "status": WeightedRankingStatus.EXCLUDED_MISSING_CRITERION.value})
                evaluated_candidates[cfg_id] = WeightedCandidateResult(
                    configuration_id=cfg_id,
                    weighted_rank=None,
                    weighted_score=None,
                    weighted_status=WeightedRankingStatus.EXCLUDED_MISSING_CRITERION.value,
                    raw_criteria_values=raw_vals,
                    normalized_criteria_values={},
                    sparse_support_flag=sparse_flag,
                    exclusion_reason=reason,
                )
                continue

            # Candidate is eligible and has all criteria
            eligible_candidates.append({
                "cfg_id": cfg_id,
                "raw_vals": raw_vals,
                "sparse_flag": sparse_flag,
            })

        # 4. Compute Normalisation Bounds (over eligible candidates)
        normalisation_bounds: Dict[str, Dict[str, float]] = {}
        non_discriminatory: List[str] = []
        warnings: List[str] = []

        if not eligible_candidates:
            warnings.append("No candidates were eligible for weighted ranking; all candidates were excluded.")
            return WeightedRankingResult(
                ranked_order=[],
                candidates=evaluated_candidates,
                weights=active_weights,
                criteria_directions=active_directions,
                normalisation_bounds={},
                non_discriminatory_criteria=[],
                excluded_candidates=excluded_candidates,
                warnings=warnings,
                metadata={"status": "NO_ELIGIBLE_CANDIDATES", "reproducibility_note": self.REPRODUCIBILITY_NOTE},
            )

        for crit in active_weights.keys():
            vals = [float(c["raw_vals"][crit]) for c in eligible_candidates]
            x_min = min(vals)
            x_max = max(vals)
            normalisation_bounds[crit] = {"min": x_min, "max": x_max}

            if math.isclose(x_min, x_max, rel_tol=1e-9):
                non_discriminatory.append(crit)
                warnings.append(
                    f"NON_DISCRIMINATORY_CRITERION: Criterion '{crit}' has identical min and max values "
                    f"({x_min:.4f}) across all eligible candidates; normalized to 1.0 (zero discriminatory power)."
                )

        # 5. Normalise and Compute Weighted Scores
        scored_candidates: List[Dict[str, Any]] = []

        for item in eligible_candidates:
            cid = item["cfg_id"]
            raws = item["raw_vals"]
            norm_vals: Dict[str, Optional[float]] = {}
            score = 0.0

            for crit, w in active_weights.items():
                x = raws[crit]
                x_min = normalisation_bounds[crit]["min"]
                x_max = normalisation_bounds[crit]["max"]
                direction = active_directions[crit]

                if crit in non_discriminatory:
                    z = 1.0
                else:
                    if direction == "maximize":
                        z = (x - x_min) / (x_max - x_min)
                    else:  # minimize
                        z = (x_max - x) / (x_max - x_min)

                norm_vals[crit] = round(z, 6)
                score += w * z

            scored_candidates.append({
                "cfg_id": cid,
                "score": score,
                "raw_vals": raws,
                "norm_vals": norm_vals,
                "sparse_flag": item["sparse_flag"],
            })

        # 6. Rank Candidates (Descending Score, deterministic tie-break by cfg_id)
        scored_candidates.sort(key=lambda c: (-c["score"], c["cfg_id"]))
        ranked_order = [c["cfg_id"] for c in scored_candidates]

        for rank_idx, sc in enumerate(scored_candidates, start=1):
            cid = sc["cfg_id"]
            warns = []
            if sc["sparse_flag"]:
                warns.append("SPARSE_SUPPORT_FLAG: Candidate capacity lies in sparse training band [100 - 539.8 kWp].")

            evaluated_candidates[cid] = WeightedCandidateResult(
                configuration_id=cid,
                weighted_rank=rank_idx,
                weighted_score=round(sc["score"], 6),
                weighted_status=WeightedRankingStatus.RANKED.value,
                raw_criteria_values=sc["raw_vals"],
                normalized_criteria_values=sc["norm_vals"],
                sparse_support_flag=sc["sparse_flag"],
                warnings=warns,
            )

        return WeightedRankingResult(
            ranked_order=ranked_order,
            candidates=evaluated_candidates,
            weights=active_weights,
            criteria_directions=active_directions,
            normalisation_bounds=normalisation_bounds,
            non_discriminatory_criteria=non_discriminatory,
            excluded_candidates=excluded_candidates,
            warnings=warnings,
            metadata={
                "n_candidates_evaluated": len(candidates),
                "n_eligible_ranked": len(scored_candidates),
                "reproducibility_note": self.REPRODUCIBILITY_NOTE,
            },
        )

    def _extract_criterion_value(self, cand: Dict[str, Any], criterion_name: str) -> Optional[float]:
        """Extracts numerical criterion value from candidate record."""
        eng = cand.get("energy") or {}
        fin = cand.get("financials") or {}
        costs = cand.get("costs") or {}

        crit = criterion_name.lower().strip()

        if crit in ("annual_energy", "energy"):
            if eng.get("annual_energy_kwh") is not None:
                return float(eng["annual_energy_kwh"])
            if eng.get("e_year1_kwh") is not None:
                return float(eng["e_year1_kwh"])
            if cand.get("annual_energy_kwh") is not None:
                return float(cand["annual_energy_kwh"])

        elif crit == "lcoe":
            if fin.get("lcoe_per_kwh") is not None:
                return float(fin["lcoe_per_kwh"])
            if fin.get("lcoe") is not None:
                return float(fin["lcoe"])
            if cand.get("lcoe_per_kwh") is not None:
                return float(cand["lcoe_per_kwh"])

        elif crit in ("capex_net", "c_net"):
            if fin.get("capex_net") is not None:
                return float(fin["capex_net"])
            if costs.get("c_net") is not None:
                return float(costs["c_net"])
            if cand.get("c_net") is not None:
                return float(cand["c_net"])

        elif crit in ("capex_gross", "c_gross"):
            if fin.get("capex_gross") is not None:
                return float(fin["capex_gross"])
            if costs.get("c_gross") is not None:
                return float(costs["c_gross"])
            if cand.get("c_gross") is not None:
                return float(cand["c_gross"])

        elif crit in ("npv", "lifecycle_cost_npv"):
            if fin.get("npv") is not None:
                return float(fin["npv"])
            if cand.get("npv") is not None:
                return float(cand["npv"])

        return None

