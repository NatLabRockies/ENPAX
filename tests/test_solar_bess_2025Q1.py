"""
Checks solar_bess_2025Q1 against PVSCM 2025 (UPV 2025Q1) for the default system.

Reference values come from the "PVSCM 2025 - UPV.xlsx" workbook released with
the Q1-2025 Solar Photovoltaic System Cost Benchmarks (DOI 10.7799/3009689),
System and O_M sheets. PV-only values are the published benchmark summary
(Table 2), which is rounded.
"""

from pathlib import Path

import pytest

from enpax.models.solar_bess_2025Q1 import SolarBESS2025Q1CostModel
from enpax.registry import REGISTRY
from enpax.runner import CentralRunner

CONFIGS = Path(__file__).resolve().parents[1] / "configs"

# System sheet, columns F (MSP) and H (MMP), $/kWdc
PVSCM_MSP = {
    "pv_module": 272.2601841477371,
    "three_phase_inverter": 32.15039154982662,
    "ess": 397.3443777439703,
    "sbos": 152.71562505281807,
    "ebos": 206.3779552238806,
    "fieldwork": 384.8062452122947,
    "officework": 70.27756559667415,
    "other": 197.69750522503767,
    "total": 1713.6298497522394,
}
PVSCM_MMP = {
    "pv_module": 291.2148514399248,
    "three_phase_inverter": 32.30636641037238,
    "ess": 436.87488541249223,
    "sbos": 154.75101318067195,
    "ebos": 230.59975746268657,
    "fieldwork": 384.8062452122947,
    "officework": 70.27756559667415,
    "other": 205.29590667185607,
    "total": 1806.126591386973,
}
PVSCM_OM = 33.27112276108396  # O_M sheet, $/kWdc-yr


# PV-only (IncludeESS = False), recalculated in the same workbook at 100 MWdc
PVSCM_PV_ONLY_MMP = 1115.2902750724597
PVSCM_PV_ONLY_OM = 19.899384490541244


def _by_category(breakdown):
    b = dict(breakdown)
    b["ess"] = b.pop("li_ion") + b.pop("bi_directional_inverter")
    b["total"] = b.pop("total_project_cost_per_kwdc")
    return b


def test_capex_matches_pvscm_mmp():
    got = _by_category(SolarBESS2025Q1CostModel().get_cost_breakdown())
    for key, value in PVSCM_MMP.items():
        assert got[key] == pytest.approx(value, rel=1e-9), key


def test_internal_msp_values_match_pvscm():
    # MSP values feed O&M (replacements, property tax, insurance) and developer profit.
    got = _by_category(SolarBESS2025Q1CostModel().get_cost_breakdown(_msp=True))
    for key, value in PVSCM_MSP.items():
        assert got[key] == pytest.approx(value, rel=1e-9), key


def test_om_matches_pvscm():
    om = SolarBESS2025Q1CostModel().get_om_cost_breakdown()
    assert om["total_om_per_kwdc_yr"] == pytest.approx(PVSCM_OM, rel=1e-9)


def test_pv_only_matches_pvscm():
    model = SolarBESS2025Q1CostModel(params={"IncludeESS": False})
    assert model.run_capex().total == pytest.approx(PVSCM_PV_ONLY_MMP, rel=1e-9)
    assert model.run_opex().annual_total == pytest.approx(PVSCM_PV_ONLY_OM, rel=1e-9)
    assert model.get_li_ion_cost_breakdown()["total_li_ion_cost_per_kwdc"] == 0
    assert "battery_capacity_mwdc" not in model.run_design().line_items


def test_run_capex_is_mmp():
    capex = SolarBESS2025Q1CostModel().run_capex()
    assert capex.total == pytest.approx(PVSCM_MMP["total"])
    assert capex.unit == "$/kWdc"


def test_exclude_indirect_lowers_cost():
    full = SolarBESS2025Q1CostModel().run_capex()
    direct = SolarBESS2025Q1CostModel(params={"IncludeIndirect": False}).run_capex()
    assert direct.total < full.total
    assert direct.line_items["officework"]["total"] == 0
    assert direct.line_items["other"]["total"] == 0


def test_out_of_range_system_size_warns():
    with pytest.warns(UserWarning):
        SolarBESS2025Q1CostModel(params={"SystemSize": 10_000})


def test_registered_and_runs_from_config():
    assert REGISTRY["solar_bess_2025Q1"] is SolarBESS2025Q1CostModel
    result = CentralRunner.from_yaml(CONFIGS / "solar_bess_2025Q1.yaml").run()
    tech = result.tech_results[0]
    assert tech.capex.total == pytest.approx(PVSCM_MMP["total"])
    assert tech.opex.annual_total == pytest.approx(PVSCM_OM)
    assert tech.design.line_items["battery_capacity_mwdc"] == pytest.approx(60)
