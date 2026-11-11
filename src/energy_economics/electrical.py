"""
SolarSelect — Phase 8: Stage 8 Electrical Compatibility Engine
Implements:
- Module-level electrical specification extraction (Voc, Isc, Vmp, Imp, coefficients).
- Inverter nameplate constraint verification (max DC voltage, MPPT window, max current).
- Temperature-corrected string voltage calculations (cold Voc, hot/cold Vmp).
- Multi-string current and reverse-current series fuse protection checks.
- DC/AC ratio and power limit validation.
- Strict NOT_EVALUATED handling when inverter or string specifications are unpopulated.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import math

from src.energy_economics.exceptions import (
    ElectricalError,
    ElectricalConfigurationError,
)
from src.energy_economics.types import (
    ElectricalCompatibility,
    ModuleElectricalSpecs,
    InverterSpecs,
    StringDesign,
    ElectricalCheckResult,
    ElectricalCompatibilityResult,
)
from src.energy_economics.catalogue import PanelRecord


class Phase8ElectricalEngine:
    """
    Engine for Phase 8 Stage 8 electrical and inverter compatibility evaluation.
    Conforms strictly to Section 4.7 of the Phase 8 Mathematical Specification.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage8_electrical_evaluation"

    MISSING_INVERTER_QUALIFICATION = (
        "Phase 8 repository currently contains module catalogue records but lacks a dedicated "
        "authoritative inverter catalogue and pre-engineered stringing designs. "
        "Real installations remain NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS until explicit designer "
        "inverter specifications and string layouts are supplied."
    )

    def __init__(self) -> None:
        pass

    def evaluate_compatibility(
        self,
        module_specs: Union[ModuleElectricalSpecs, PanelRecord],
        inverter_specs: Optional[InverterSpecs] = None,
        string_design: Optional[StringDesign] = None,
        total_panel_count: Optional[int] = None,
    ) -> ElectricalCompatibilityResult:
        """
        Evaluates electrical compatibility between panels, inverter, and string design.

        Args:
            module_specs: ModuleElectricalSpecs or catalogue PanelRecord.
            inverter_specs: Inverter electrical specifications.
            string_design: String layout and design temperature specifications.
            total_panel_count: Total candidate roof panels (from Phase 7).

        Returns:
            ElectricalCompatibilityResult with detailed per-check verdicts.
        """
        # 1. Parse module specs
        if isinstance(module_specs, PanelRecord):
            mod = self._extract_specs_from_panel_record(module_specs)
        elif isinstance(module_specs, ModuleElectricalSpecs):
            mod = module_specs
        else:
            raise ElectricalConfigurationError(
                f"Unsupported module_specs type: {type(module_specs).__name__}. "
                "Must be ModuleElectricalSpecs or PanelRecord."
            )

        # 2. Check if inverter and string design are supplied
        if inverter_specs is None or string_design is None:
            missing_specs = []
            if inverter_specs is None:
                missing_specs.append("inverter_specifications")
            if string_design is None:
                missing_specs.append("string_design_layout")

            return ElectricalCompatibilityResult(
                overall_status=ElectricalCompatibility.NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS.value,
                checks=[],
                dc_ac_ratio=None,
                warnings=[self.MISSING_INVERTER_QUALIFICATION],
                missing_specifications=missing_specs,
                metadata={"status": "INSUFFICIENT_INPUTS"},
            )

        # 3. Perform Electrical Checks
        checks: List[ElectricalCheckResult] = []
        warnings: List[str] = []
        missing_specs: List[str] = []

        # Check 1: Panel Count Consistency
        total_modules_in_design = string_design.modules_per_string * string_design.n_strings
        if total_panel_count is not None:
            if total_modules_in_design != total_panel_count:
                checks.append(
                    ElectricalCheckResult(
                        check_name="panel_count_consistency",
                        status="FAIL",
                        calculated_value=float(total_modules_in_design),
                        threshold_value=float(total_panel_count),
                        unit="panels",
                        details=(
                            f"String layout covers {total_modules_in_design} panels "
                            f"({string_design.n_strings} strings of {string_design.modules_per_string}), "
                            f"which does not match candidate roof count of {total_panel_count} panels."
                        ),
                    )
                )
            else:
                checks.append(
                    ElectricalCheckResult(
                        check_name="panel_count_consistency",
                        status="PASS",
                        calculated_value=float(total_modules_in_design),
                        threshold_value=float(total_panel_count),
                        unit="panels",
                        details=f"String layout perfectly matches roof panel count ({total_panel_count} panels).",
                    )
                )

        # Check 2: Max String Open-Circuit Voltage (Cold Temperature)
        # Formula: V_oc_cold = n_s * V_oc * [1 + (beta_Voc / 100) * (T_min - 25)]
        # Must be <= min(V_dc_max_inverter, V_sys_max_module)
        beta_voc = mod.voc_temp_coefficient_pct_per_c / 100.0  # fraction / °C
        delta_t_cold = string_design.min_design_temperature_c - 25.0
        voc_cold_per_mod = mod.voc_v * (1.0 + beta_voc * delta_t_cold)
        voc_cold_string = string_design.modules_per_string * voc_cold_per_mod

        v_limit = min(inverter_specs.max_dc_input_voltage_v, mod.max_system_voltage_v)

        if voc_cold_string <= v_limit:
            checks.append(
                ElectricalCheckResult(
                    check_name="max_string_voltage_cold",
                    status="PASS",
                    calculated_value=round(voc_cold_string, 2),
                    threshold_value=round(v_limit, 2),
                    unit="V",
                    details=(
                        f"String cold Voc is {voc_cold_string:.2f} V at {string_design.min_design_temperature_c}°C, "
                        f"which is below maximum limit of {v_limit:.2f} V."
                    ),
                )
            )
        else:
            checks.append(
                ElectricalCheckResult(
                    check_name="max_string_voltage_cold",
                    status="FAIL",
                    calculated_value=round(voc_cold_string, 2),
                    threshold_value=round(v_limit, 2),
                    unit="V",
                    details=(
                        f"String cold Voc {voc_cold_string:.2f} V exceeds voltage limit {v_limit:.2f} V "
                        f"at design minimum temperature {string_design.min_design_temperature_c}°C."
                    ),
                )
            )

        # Check 3: MPPT Upper Voltage Window (Cold)
        # Needs Vmp temperature coefficient. If missing -> NOT_EVALUATED
        if mod.vmp_temp_coefficient_pct_per_c is None:
            checks.append(
                ElectricalCheckResult(
                    check_name="mppt_upper_voltage_cold",
                    status="NOT_EVALUATED",
                    calculated_value=None,
                    threshold_value=inverter_specs.mppt_max_voltage_v,
                    unit="V",
                    details=(
                        "Vmp temperature coefficient is not available in catalogue. "
                        "Upper MPPT voltage check cannot be evaluated."
                    ),
                    missing_inputs=["vmp_temp_coefficient_pct_per_c"],
                )
            )
            missing_specs.append("vmp_temp_coefficient_pct_per_c")
        else:
            gamma_vmp = mod.vmp_temp_coefficient_pct_per_c / 100.0
            vmp_cold_per_mod = mod.vmp_v * (1.0 + gamma_vmp * delta_t_cold)
            vmp_cold_string = string_design.modules_per_string * vmp_cold_per_mod
            if vmp_cold_string <= inverter_specs.mppt_max_voltage_v:
                checks.append(
                    ElectricalCheckResult(
                        check_name="mppt_upper_voltage_cold",
                        status="PASS",
                        calculated_value=round(vmp_cold_string, 2),
                        threshold_value=inverter_specs.mppt_max_voltage_v,
                        unit="V",
                        details=(
                            f"Cold string Vmp {vmp_cold_string:.2f} V is within MPPT upper bound "
                            f"of {inverter_specs.mppt_max_voltage_v:.2f} V."
                        ),
                    )
                )
            else:
                checks.append(
                    ElectricalCheckResult(
                        check_name="mppt_upper_voltage_cold",
                        status="FAIL",
                        calculated_value=round(vmp_cold_string, 2),
                        threshold_value=inverter_specs.mppt_max_voltage_v,
                        unit="V",
                        details=(
                            f"Cold string Vmp {vmp_cold_string:.2f} V exceeds MPPT upper limit "
                            f"of {inverter_specs.mppt_max_voltage_v:.2f} V."
                        ),
                    )
                )

        # Check 4: MPPT Lower Voltage Window (Hot Cell Temperature)
        # Needs gamma_vmp and max_cell_temperature_c
        if mod.vmp_temp_coefficient_pct_per_c is None or string_design.max_cell_temperature_c is None:
            missing = []
            if mod.vmp_temp_coefficient_pct_per_c is None:
                missing.append("vmp_temp_coefficient_pct_per_c")
            if string_design.max_cell_temperature_c is None:
                missing.append("max_cell_temperature_c")
            checks.append(
                ElectricalCheckResult(
                    check_name="mppt_lower_voltage_hot",
                    status="NOT_EVALUATED",
                    calculated_value=None,
                    threshold_value=inverter_specs.mppt_min_voltage_v,
                    unit="V",
                    details=f"Missing inputs: {', '.join(missing)}. Lower MPPT check cannot be evaluated.",
                    missing_inputs=missing,
                )
            )
            missing_specs.extend(missing)
        else:
            gamma_vmp = mod.vmp_temp_coefficient_pct_per_c / 100.0
            delta_t_hot = string_design.max_cell_temperature_c - 25.0
            vmp_hot_per_mod = mod.vmp_v * (1.0 + gamma_vmp * delta_t_hot)
            vmp_hot_string = string_design.modules_per_string * vmp_hot_per_mod
            if vmp_hot_string >= inverter_specs.mppt_min_voltage_v:
                checks.append(
                    ElectricalCheckResult(
                        check_name="mppt_lower_voltage_hot",
                        status="PASS",
                        calculated_value=round(vmp_hot_string, 2),
                        threshold_value=inverter_specs.mppt_min_voltage_v,
                        unit="V",
                        details=(
                            f"Hot string Vmp {vmp_hot_string:.2f} V is above MPPT lower bound "
                            f"of {inverter_specs.mppt_min_voltage_v:.2f} V."
                        ),
                    )
                )
            else:
                checks.append(
                    ElectricalCheckResult(
                        check_name="mppt_lower_voltage_hot",
                        status="FAIL",
                        calculated_value=round(vmp_hot_string, 2),
                        threshold_value=inverter_specs.mppt_min_voltage_v,
                        unit="V",
                        details=(
                            f"Hot string Vmp {vmp_hot_string:.2f} V falls below MPPT minimum "
                            f"of {inverter_specs.mppt_min_voltage_v:.2f} V."
                        ),
                    )
                )

        # Check 5: Input Current per MPPT
        # Formula: n_par * I_mp <= I_max_mppt
        total_imp_mppt = string_design.parallel_strings_per_mppt * mod.imp_a
        if total_imp_mppt <= inverter_specs.max_input_current_per_mppt_a:
            checks.append(
                ElectricalCheckResult(
                    check_name="mppt_input_current",
                    status="PASS",
                    calculated_value=round(total_imp_mppt, 2),
                    threshold_value=inverter_specs.max_input_current_per_mppt_a,
                    unit="A",
                    details=(
                        f"MPPT input current {total_imp_mppt:.2f} A ({string_design.parallel_strings_per_mppt} strings) "
                        f"is within rating {inverter_specs.max_input_current_per_mppt_a:.2f} A."
                    ),
                )
            )
        else:
            checks.append(
                ElectricalCheckResult(
                    check_name="mppt_input_current",
                    status="FAIL",
                    calculated_value=round(total_imp_mppt, 2),
                    threshold_value=inverter_specs.max_input_current_per_mppt_a,
                    unit="A",
                    details=(
                        f"MPPT input current {total_imp_mppt:.2f} A exceeds inverter rating "
                        f"of {inverter_specs.max_input_current_per_mppt_a:.2f} A."
                    ),
                )
            )

        # Check 6: Short-Circuit Current per MPPT (Hot Temperature)
        alpha_isc = mod.isc_temp_coefficient_pct_per_c / 100.0
        delta_t_max = string_design.max_design_temperature_c - 25.0
        isc_hot_per_string = mod.isc_a * (1.0 + alpha_isc * delta_t_max)
        total_isc_mppt = string_design.parallel_strings_per_mppt * isc_hot_per_string

        if total_isc_mppt <= inverter_specs.max_short_circuit_current_per_mppt_a:
            checks.append(
                ElectricalCheckResult(
                    check_name="mppt_short_circuit_current",
                    status="PASS",
                    calculated_value=round(total_isc_mppt, 2),
                    threshold_value=inverter_specs.max_short_circuit_current_per_mppt_a,
                    unit="A",
                    details=(
                        f"MPPT Isc {total_isc_mppt:.2f} A is below inverter rating "
                        f"of {inverter_specs.max_short_circuit_current_per_mppt_a:.2f} A (evaluated with alpha_Isc without generic unstated multipliers)."
                    ),
                )
            )
        else:
            checks.append(
                ElectricalCheckResult(
                    check_name="mppt_short_circuit_current",
                    status="FAIL",
                    calculated_value=round(total_isc_mppt, 2),
                    threshold_value=inverter_specs.max_short_circuit_current_per_mppt_a,
                    unit="A",
                    details=(
                        f"MPPT Isc {total_isc_mppt:.2f} A exceeds inverter limit "
                        f"of {inverter_specs.max_short_circuit_current_per_mppt_a:.2f} A."
                    ),
                )
            )

        # Check 7: Series Fuse Protection
        # In a multi-string combiner (n_par >= 2), reverse current could be (n_par - 1) * Isc.
        if string_design.parallel_strings_per_mppt > 1:
            potential_fault_current = (string_design.parallel_strings_per_mppt - 1) * mod.isc_a
            if potential_fault_current <= mod.max_series_fuse_rating_a:
                checks.append(
                    ElectricalCheckResult(
                        check_name="series_fuse_rating",
                        status="PASS",
                        calculated_value=round(potential_fault_current, 2),
                        threshold_value=mod.max_series_fuse_rating_a,
                        unit="A",
                        details=(
                            f"Reverse fault current {potential_fault_current:.2f} A does not exceed "
                            f"module series fuse rating of {mod.max_series_fuse_rating_a:.2f} A."
                        ),
                    )
                )
            else:
                checks.append(
                    ElectricalCheckResult(
                        check_name="series_fuse_rating",
                        status="FAIL",
                        calculated_value=round(potential_fault_current, 2),
                        threshold_value=mod.max_series_fuse_rating_a,
                        unit="A",
                        details=(
                            f"Reverse fault current {potential_fault_current:.2f} A exceeds "
                            f"module fuse rating of {mod.max_series_fuse_rating_a:.2f} A. Individual string fuses required."
                        ),
                    )
                )
        else:
            checks.append(
                ElectricalCheckResult(
                    check_name="series_fuse_rating",
                    status="PASS",
                    calculated_value=round(mod.isc_a, 2),
                    threshold_value=mod.max_series_fuse_rating_a,
                    unit="A",
                    details="Single string per MPPT; reverse current cannot exceed module fuse rating.",
                )
            )

        # Check 8: DC Input Power & DC/AC Ratio
        active_panels = total_panel_count if total_panel_count is not None else total_modules_in_design
        p_stc_w = mod.rated_power_wp or (mod.vmp_v * mod.imp_a)
        total_dc_kw = (active_panels * p_stc_w) / 1000.0
        dc_ac_ratio = total_dc_kw / inverter_specs.rated_ac_power_kw if inverter_specs.rated_ac_power_kw > 0 else 1.0

        if total_dc_kw <= inverter_specs.max_dc_input_power_kw:
            details_str = (
                f"Total DC capacity {total_dc_kw:.2f} kWp is within inverter maximum DC power "
                f"of {inverter_specs.max_dc_input_power_kw:.2f} kW (DC/AC ratio: {dc_ac_ratio:.2f})."
            )
            if dc_ac_ratio > 1.35:
                warnings.append(
                    f"High DC/AC ratio ({dc_ac_ratio:.2f}) may cause significant inverter power clipping in high irradiance."
                )
            checks.append(
                ElectricalCheckResult(
                    check_name="dc_input_power_capacity",
                    status="PASS",
                    calculated_value=round(total_dc_kw, 2),
                    threshold_value=inverter_specs.max_dc_input_power_kw,
                    unit="kW",
                    details=details_str,
                )
            )
        else:
            checks.append(
                ElectricalCheckResult(
                    check_name="dc_input_power_capacity",
                    status="FAIL",
                    calculated_value=round(total_dc_kw, 2),
                    threshold_value=inverter_specs.max_dc_input_power_kw,
                    unit="kW",
                    details=(
                        f"Total DC capacity {total_dc_kw:.2f} kWp exceeds maximum inverter DC limit "
                        f"of {inverter_specs.max_dc_input_power_kw:.2f} kW."
                    ),
                )
            )

        # 4. Determine Overall Status
        has_fail = any(c.status == "FAIL" for c in checks)
        has_not_evaluated = any(c.status == "NOT_EVALUATED" for c in checks)

        if has_fail:
            overall_status = ElectricalCompatibility.INCOMPATIBLE.value
        elif has_not_evaluated:
            overall_status = ElectricalCompatibility.NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS.value
        else:
            overall_status = ElectricalCompatibility.COMPATIBLE.value

        return ElectricalCompatibilityResult(
            overall_status=overall_status,
            checks=checks,
            dc_ac_ratio=round(dc_ac_ratio, 2) if total_panel_count is not None else None,
            warnings=warnings,
            missing_specifications=sorted(list(set(missing_specs))),
            metadata={
                "inverter_model": inverter_specs.inverter_model,
                "total_modules_in_design": total_modules_in_design,
            },
        )

    def _extract_specs_from_panel_record(self, record: PanelRecord) -> ModuleElectricalSpecs:
        """Extracts required electrical parameters from a PanelRecord, verifying completeness."""
        missing = []
        if record.voc_v is None:
            missing.append("voc_v")
        if record.isc_a is None:
            missing.append("isc_a")
        if record.vmp_v is None:
            missing.append("vmp_v")
        if record.imp_a is None:
            missing.append("imp_a")
        if record.max_system_voltage_v is None:
            missing.append("max_system_voltage_v")
        if record.max_series_fuse_rating_a is None:
            missing.append("max_series_fuse_rating_a")
        if record.voc_temp_coefficient_pct_per_c is None:
            missing.append("voc_temp_coefficient_pct_per_c")
        if record.isc_temp_coefficient_pct_per_c is None:
            missing.append("isc_temp_coefficient_pct_per_c")

        if missing:
            raise ElectricalConfigurationError(
                f"Panel '{record.panel_id}' missing essential electrical parameters: {missing}."
            )

        return ModuleElectricalSpecs(
            voc_v=float(record.voc_v),
            isc_a=float(record.isc_a),
            vmp_v=float(record.vmp_v),
            imp_a=float(record.imp_a),
            max_system_voltage_v=float(record.max_system_voltage_v),
            max_series_fuse_rating_a=float(record.max_series_fuse_rating_a),
            voc_temp_coefficient_pct_per_c=float(record.voc_temp_coefficient_pct_per_c),
            isc_temp_coefficient_pct_per_c=float(record.isc_temp_coefficient_pct_per_c),
            vmp_temp_coefficient_pct_per_c=None,  # Not present in Phase 6 catalogue
            rated_power_wp=record.rated_power_wp,
        )

