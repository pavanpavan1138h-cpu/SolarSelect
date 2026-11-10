"""
SolarSelect — Phase 7: Physical Constraint Validator
Validates candidate panel positions and layouts against hard physical constraints:
boundary containment, obstacle exclusion, inter-panel overlap, and minimum clearances.
Enforces zero tolerance relaxation on physical clearances (actual_gap >= required_gap).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from src.roof_fit.geometry import IntegerRectangle
from src.roof_fit.usable_area import ExpandedObstacle
from src.roof_fit.exceptions import (
    BoundaryContainmentError,
    ObstacleCollisionError,
    PanelOverlapError,
    ClearanceViolationError,
)


@dataclass(frozen=True)
class ConstraintViolation:
    """Detailed record of a physical or geometric constraint violation."""
    violation_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlacementValidationResult:
    """Aggregate result of validating a panel candidate or full layout."""
    is_valid: bool
    violations: List[ConstraintViolation] = field(default_factory=list)


class ConstraintValidator:
    """Enforces zero-tolerance geometric and physical layout invariants."""

    @classmethod
    def check_boundary_containment(
        cls, candidate: IntegerRectangle, usable_envelope: IntegerRectangle, raise_on_violation: bool = False
    ) -> Optional[ConstraintViolation]:
        """
        Verifies that candidate panel is completely inside the usable envelope.
        Returns None if valid, or ConstraintViolation if violated.
        """
        if not usable_envelope.contains(candidate):
            msg = (
                f"Candidate panel bounds ({candidate.x_min}, {candidate.y_min}, {candidate.x_max}, {candidate.y_max}) "
                f"exceed usable envelope ({usable_envelope.x_min}, {usable_envelope.y_min}, "
                f"{usable_envelope.x_max}, {usable_envelope.y_max})."
            )
            if raise_on_violation:
                raise BoundaryContainmentError(msg)
            return ConstraintViolation(
                violation_type="BOUNDARY_EXCLUSION",
                message=msg,
                details={
                    "candidate": candidate.to_tuple(),
                    "usable_envelope": usable_envelope.to_tuple(),
                },
            )
        return None

    @classmethod
    def check_obstacle_collision(
        cls,
        candidate: IntegerRectangle,
        obstacles: List[ExpandedObstacle],
        raise_on_violation: bool = False,
    ) -> List[ConstraintViolation]:
        """
        Verifies that candidate panel does not have positive-area overlap with any expanded obstacle.
        """
        violations: List[ConstraintViolation] = []
        for obs in obstacles:
            if candidate.has_positive_area_overlap(obs.expanded_rect):
                isect = candidate.intersection(obs.expanded_rect)
                msg = (
                    f"Candidate panel collides with expanded obstacle '{obs.obstacle_id}'. "
                    f"Intersection area: {isect.area if isect else 0} sq units."
                )
                if raise_on_violation:
                    raise ObstacleCollisionError(msg)
                violations.append(
                    ConstraintViolation(
                        violation_type="OBSTACLE_COLLISION",
                        message=msg,
                        details={
                            "obstacle_id": obs.obstacle_id,
                            "candidate": candidate.to_tuple(),
                            "expanded_obstacle": obs.expanded_rect.to_tuple(),
                            "intersection": isect.to_tuple() if isect else None,
                        },
                    )
                )
        return violations

    @classmethod
    def check_panel_overlap(
        cls,
        candidate: IntegerRectangle,
        placed_panels: List[IntegerRectangle],
        raise_on_violation: bool = False,
    ) -> List[ConstraintViolation]:
        """
        Verifies that candidate panel does not share positive area with already placed panels.
        """
        violations: List[ConstraintViolation] = []
        for idx, placed in enumerate(placed_panels):
            if candidate.has_positive_area_overlap(placed):
                isect = candidate.intersection(placed)
                msg = (
                    f"Candidate panel overlaps with placed panel index {idx}. "
                    f"Overlap area: {isect.area if isect else 0} sq units."
                )
                if raise_on_violation:
                    raise PanelOverlapError(msg)
                violations.append(
                    ConstraintViolation(
                        violation_type="PANEL_OVERLAP",
                        message=msg,
                        details={
                            "placed_index": idx,
                            "candidate": candidate.to_tuple(),
                            "placed": placed.to_tuple(),
                            "intersection": isect.to_tuple() if isect else None,
                        },
                    )
                )
        return violations

    @classmethod
    def check_inter_panel_gap(
        cls,
        panel_a: IntegerRectangle,
        panel_b: IntegerRectangle,
        min_gap_int: int,
        raise_on_violation: bool = False,
    ) -> Optional[ConstraintViolation]:
        """
        Verifies that the horizontal gap between two adjacent panels meets the hard minimum:
        actual_gap >= min_gap_int (strict, no negative tolerance).
        """
        gap = panel_a.horizontal_gap_to(panel_b)
        if gap < min_gap_int:
            msg = (
                f"Horizontal gap ({gap} units) is strictly less than required minimum "
                f"({min_gap_int} units). Deficit: {min_gap_int - gap} units."
            )
            if raise_on_violation:
                raise ClearanceViolationError(msg)
            return ConstraintViolation(
                violation_type="CLAMP_GAP_VIOLATION",
                message=msg,
                details={
                    "actual_gap_units": gap,
                    "required_gap_units": min_gap_int,
                    "deficit_units": min_gap_int - gap,
                },
            )
        return None

    @classmethod
    def check_inter_row_gap(
        cls,
        panel_lower: IntegerRectangle,
        panel_upper: IntegerRectangle,
        min_gap_int: int,
        raise_on_violation: bool = False,
    ) -> Optional[ConstraintViolation]:
        """
        Verifies that the vertical gap between two adjacent rows meets the hard minimum:
        actual_gap >= min_gap_int (strict, no negative tolerance).
        """
        gap = panel_lower.vertical_gap_to(panel_upper)
        if gap < min_gap_int:
            msg = (
                f"Vertical walkway gap ({gap} units) is strictly less than required minimum "
                f"({min_gap_int} units). Deficit: {min_gap_int - gap} units."
            )
            if raise_on_violation:
                raise ClearanceViolationError(msg)
            return ConstraintViolation(
                violation_type="ROW_GAP_VIOLATION",
                message=msg,
                details={
                    "actual_gap_units": gap,
                    "required_gap_units": min_gap_int,
                    "deficit_units": min_gap_int - gap,
                },
            )
        return None

    @classmethod
    def validate_candidate(
        cls,
        candidate: IntegerRectangle,
        usable_envelope: IntegerRectangle,
        obstacles: List[ExpandedObstacle],
        placed_panels: Optional[List[IntegerRectangle]] = None,
        raise_on_violation: bool = False,
    ) -> PlacementValidationResult:
        """
        Validates a single candidate panel against boundary, obstacles, and existing panels.
        """
        violations: List[ConstraintViolation] = []

        # 1. Boundary containment
        b_viol = cls.check_boundary_containment(candidate, usable_envelope, raise_on_violation=raise_on_violation)
        if b_viol:
            violations.append(b_viol)

        # 2. Obstacle collision
        obs_viols = cls.check_obstacle_collision(candidate, obstacles, raise_on_violation=raise_on_violation)
        violations.extend(obs_viols)

        # 3. Panel overlap
        if placed_panels:
            p_viols = cls.check_panel_overlap(candidate, placed_panels, raise_on_violation=raise_on_violation)
            violations.extend(p_viols)

        return PlacementValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
        )

    @classmethod
    def validate_layout(
        cls,
        placed_panels: List[IntegerRectangle],
        usable_envelope: IntegerRectangle,
        obstacles: List[ExpandedObstacle],
        raise_on_violation: bool = False,
    ) -> PlacementValidationResult:
        """
        Validates an entire generated panel array against containment, obstacle collisions,
        and pairwise mutual non-overlap.
        """
        violations: List[ConstraintViolation] = []

        # 1. Boundary containment for every panel
        for idx, panel in enumerate(placed_panels):
            b_viol = cls.check_boundary_containment(panel, usable_envelope, raise_on_violation=raise_on_violation)
            if b_viol:
                violations.append(b_viol)

        # 2. Obstacle collision for every panel
        for idx, panel in enumerate(placed_panels):
            obs_viols = cls.check_obstacle_collision(panel, obstacles, raise_on_violation=raise_on_violation)
            violations.extend(obs_viols)

        # 3. Pairwise non-overlap between all pairs
        n = len(placed_panels)
        for i in range(n):
            for j in range(i + 1, n):
                if placed_panels[i].has_positive_area_overlap(placed_panels[j]):
                    isect = placed_panels[i].intersection(placed_panels[j])
                    msg = (
                        f"Pairwise overlap between panel index {i} and {j}. "
                        f"Overlap area: {isect.area if isect else 0} sq units."
                    )
                    if raise_on_violation:
                        raise PanelOverlapError(msg)
                    violations.append(
                        ConstraintViolation(
                            violation_type="PANEL_OVERLAP",
                            message=msg,
                            details={
                                "panel_i": i,
                                "panel_j": j,
                                "rect_i": placed_panels[i].to_tuple(),
                                "rect_j": placed_panels[j].to_tuple(),
                                "intersection": isect.to_tuple() if isect else None,
                            },
                        )
                    )

        return PlacementValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
        )

