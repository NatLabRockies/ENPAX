"""
solar_bess.py — Modeled Market Price Utility-Scale PV System Cost Model (PVSCM)

Based on:
    Modeled Market Price Utility-Scale PV System Cost Model (PVSCM), 2024 Q1
    U.S. Department of Energy (DOE)
    Lawrence Berkeley National Laboratory (LBNL)
    National Laboratory of the Rockies (NLR)
    Sandia National Laboratory (SNL)
    Ref: https://www.energy.gov/cmei/systems/solar-photovoltaic-system-cost-benchmarks

System scope:
    50–200 MWdc, single-axis tracking, c-Si modules, central inverter.
    Optional 2.4 kWh battery energy storage per kWdc of modules.
    Costs in 2023 USD (CPI-U = 304.7).

Representative system (default configuration):
    The default system is a 100 MWdc utility-scale PV plant. Each module has an
    area (with frame) of 2.57 m2 and a rated power of 530 W, corresponding to an
    efficiency of 20.6%. Bifacial modules are produced in Southeast Asia in a plant
    producing 1.5 GWdc/yr, using c-Si cells also from Southeast Asia. In 2024 Q1,
    these modules were not subject to import tariffs.

    ~189,000 modules are mounted on single-axis tracking structures assembled in
    the field, occupying 160 hectares. Torque tubes and fasteners are domestically
    produced; their producers receive 45X tax credits (~$4.60/m2), half of which
    is passed to the installer as reduced component pricing.

    DC cables connect to 19 utility-scale central inverters (4 MWac each) for a
    rated AC output of 76 MWac (ILR = 1.32). Inverters are made in Europe in a
    plant producing 250 units/yr and are not subject to import tariffs.

    When an ESS is included, it consists of 80 pad-mounted Li-ion battery cabinets
    (3 MWh each, 240 MWh total). Each cabinet includes a bidirectional inverter
    rated at 750 kWac (4-hour discharge), totaling 60 MWac AC-coupled with the PV
    inverter. The ESS is assembled in the US using domestic components except for
    battery cells imported from China (subject to 25% import tariff). The ESS
    producer receives a 45X tax credit of $10/kWh for battery modules; half is
    passed to the developer as reduced ESS pricing.

    O&M includes module cleaning, periodic inspection, component replacement, land
    lease, property tax, insurance, and management. Component replacement prices
    are based on the MSP of those components rather than MMP, as replacements occur
    well into the future.
"""

import warnings
from pathlib import Path

import pandas as pd
import yaml

from genstor.base_model import BaseCostModel
from genstor.outputs import CapexBreakdown, DesignSummary

# ---------------------------------------------------------------------------
# Valid system size range (MWdc)
# ---------------------------------------------------------------------------
_SYSTEM_SIZE_MIN_MWDC = 50
_SYSTEM_SIZE_MAX_MWDC = 200

DEFAULTS = {
    # -----------------------------------------------------------------------
    # 0. System parameters
    #    Representative 100 MWdc utility-scale plant with ILR = 1.32.
    #    StorageDuration = 2.4 kWh-cap/kWdc gives 240 MWh for a 100 MWdc plant.
    # -----------------------------------------------------------------------
    "SystemSize": 100_000,           # kWdc — rated DC capacity of PV array
    "ILR": 1.32,                     # kWdc/kWac — inverter loading ratio
    "StorageDuration": 2.4,          # kWh-cap/kWdc — storage per unit of solar
    "IncludeESS": True,              # toggle: include battery storage costs
    "GeneralDuty": 0.034,            # fraction — general import duty
    "Tariff201": 0.1425,             # fraction — Section 201 tariff
    "Tariff301": 0.25,               # fraction — Section 301 tariff
    "Tariff301high": 0.5,            # fraction — Section 301 high-rate tariff

    # -----------------------------------------------------------------------
    # 1. PV module parameters
    #    Bifacial c-Si module assembled in SE Asia using cells from SE Asia.
    #    Component costs and assembly labor are direct costs; others are indirect.
    #
    #    Default module: 530 W, 2.57 m2 (2.27 m × 1.13 m), efficiency = 20.6%.
    #    Plant capacity: 1.5 GWdc/yr. Not subject to import tariffs in 2024 Q1.
    # -----------------------------------------------------------------------
    "ModuleEfficiency": 0.206,       # kWdc/m2
    "ModuleHeight": 2.27,            # m
    "ModuleWidth": 1.13,             # m
    "ModuleWeight": 11.5,            # kg/m2
    "CellToModule": 0.98,            # kWdc module / kWdc cell
    "ModuleLabor": 0.109,            # hr/m2
    "ModuleElectricity": 5.79,       # kWh consumed/m2
    "ModuleDepreciation": 0.118,     # fraction/yr of capital invested
    "ModuleProfitMSP": 0.15,         # fraction — profit margin on MSP
    "ModuleMarketPrice": 336,        # $/kWdc — modeled market price
    "ModuleAnnualProduction": 1_500_000,  # kWdc/yr — plant annual output
    "ModuleLaborFixed": 700_000,     # $/yr — fixed labor cost at plant
    "Cost_Cells": 130.00,            # $/kWdc
    "Cost_Frame": 1.50,              # $/m of frame perimeter
    "Cost_Sheets": 7.70,             # $/m2
    "Cost_OtherMat": 6.30,           # $/module
    "Cost_Labor": 3.00,              # $/hr
    "Cost_Electricity": 0.06,        # $/kWh
    "Cost_Depreciation": 45.00,      # $/kWdc/yr
    "Cost_Maintenance": 1.80,        # $/kWdc
    "Cost_Shipping": 0.60,           # $/kg

    # -----------------------------------------------------------------------
    # 2. Three-phase central inverter parameters
    #    European 4 MWac utility-scale three-phase central inverter.
    #    Component costs and assembly labor are direct costs; others are indirect.
    #
    #    Default: 19 inverters × 4 MWac = 76 MWac. Made in Europe, 250 units/yr.
    #    Not subject to import tariffs.
    # -----------------------------------------------------------------------
    "InverterWeight": 0.935,         # kg/kWac
    "InverterLabor": 0.045,          # hr/kWac
    "InverterElectricity": 8.42,     # kWh consumed/kWac
    "InverterDepreciation": 0.118,   # fraction/yr of capital invested
    "InverterProfitMSP": 0.25,       # fraction — profit margin on MSP
    "InverterMarketPrice": 44,       # $/kWac — modeled market price
    "InverterAnnualProduction": 1_000_000,  # kWac/yr — plant annual output
    "InverterLaborFixed": 5_800_000, # $/yr — fixed labor cost at plant
    "Cost_Inv_PCBA": 14.00,          # $/kWac — PCB assemblies
    "Cost_Inv_ElecParts": 5.00,      # $/kWac — electrical parts
    "Cost_Inv_ClimateControl": 3.00, # $/kWac — climate control hardware
    "Cost_Inv_Enclosure": 4.00,      # $/kWac — enclosure
    "Cost_Inv_Labor": 39.00,         # $/hr — assembly labor rate
    "Cost_Inv_Electricity": 0.10,    # $/kWh
    "Cost_Inv_Depreciation": 10.00,  # $/kWac/yr
    "Cost_Inv_Maintenance": 0.40,    # $/kWac
    "Cost_Inv_Shipping": 1.50,       # $/kg

    # -----------------------------------------------------------------------
    # 3. ESS — energy storage system parameters
    #    Domestically assembled 3 MWh-cap, 1 MWac, AC-coupled pad-mounted
    #    battery cabinets. Component costs and on-site assembly labor are direct
    #    costs; other costs are indirect.
    #
    #    Default: 80 cabinets × 3 MWh = 240 MWh, 60 MWac bidirectional inverter.
    #    Battery cells imported from China, subject to 25% Section 301 tariff.
    #    45X credit = $10/kWh; 50% passed through to developer.
    # -----------------------------------------------------------------------
    "Battery45X": 10,                # $/kWh-cap — 45X tax credit for battery modules
    "45XPassthrough": 0.5,           # fraction — share of 45X credit passed to developer
    "BatteryDuration": 4,            # h — discharge duration
    "ESS_ILR": 1,                    # kWac ESS / kWdc battery
    "ESSWeight": 9.4,                # kg/kWh-cap
    "ESSLabor": 0.22,                # hr/kWh-cap — on-site assembly labor
    "ESSElectricity": 30.5,          # kWh consumed/kWh-cap
    "ESSDepreciation": 0.11,         # fraction/yr of capital invested
    "ESSProfitMSP": 0.25,            # fraction — profit margin on MSP
    "ESSMarketPrice": 228,           # $/kWh-cap — modeled market price
    "ESSAnnualProduction": 1_000_000,     # kWh-cap/yr — plant annual output
    "ESSLaborFixed": 2_500_000,      # $/yr — fixed labor cost at plant
    "Cost_ESS_LiIonCells": 75.00,    # $/kWh-cap
    "Cost_ESS_BatteryPacks": 25.00,  # $/kWh-cap
    "Cost_ESS_Enclosure": 20.00,     # $/kWh-cap
    "Cost_ESS_ACDC_Conv": 100.00,    # $/kWac — bidirectional AC/DC converter
    "Cost_ESS_Labor": 34.00,         # $/hr
    "Cost_ESS_Electricity": 0.08,    # $/kWh
    "Cost_ESS_Depreciation": 7.00,   # $/kWh-cap/yr
    "Cost_ESS_Maintenance": 0.28,    # $/kWh-cap
    "Cost_ESS_Shipping": 1.00,       # $/kg

    # -----------------------------------------------------------------------
    # 4. SBOS — structural balance of system
    #    Domestically assembled single-axis trackers installed in the field.
    #    Component costs are direct costs. ESS pad and shipping are indirect.
    #
    #    Torque tubes and fasteners receive 45X credits; 50% passed through.
    # -----------------------------------------------------------------------
    "Fastener45X": 2.28,             # $/m2 — 45X credit for fasteners
    "TorqueTube45X": 0.87,           # $/m2 — 45X credit for torque tubes
    "FastenerWeight": 0.2,           # kg/m2
    "TorqueTubeWeight": 4.8,         # kg/m2
    "SBOSshippingWeight": 10,        # kg/m2 — weight basis for SBOS shipping
    "PiersPerRow": 11,               # piers per tracker row
    "RowLength": 86.3,               # m — tracker row length
    "Cost_SBOS_TorqueTubes": 2.70,   # $/kg
    "Cost_SBOS_Piers": 100.00,       # $/pier
    "Cost_SBOS_Rails": 1.80,         # $/m of module rail
    "Cost_SBOS_Fasteners": 3.30,     # $/kg
    "Cost_SBOS_SlewDrive": 300.00,   # $/row
    "Cost_SBOS_Dampers": 6.40,       # $/pier
    "Cost_SBOS_Motor": 440.00,       # $/row
    "Cost_SBOS_Electronics": 110.00, # $/row
    "Cost_SBOS_Shipping": 0.40,      # $/kg
    "Cost_SBOS_ESSPad": 4.00,        # $/kWh-cap — ESS concrete pad cost

    # -----------------------------------------------------------------------
    # 5. EBOS — electrical balance of system
    #    Electrical system components for a large array connected to a
    #    transmission grid. All hardware costs are direct; shipping is indirect.
    # -----------------------------------------------------------------------
    "EBOSweight": 2,                 # kg/kWac — EBOS hardware weight
    "TransmissionFixed": 679_747,    # $ — fixed transmission interconnect cost
    "Cost_EBOS_Transformers": 40.00, # $/kWac
    "Cost_EBOS_Switches": 6.50,      # $/kWac
    "Cost_EBOS_Breakers": 15.00,     # $/kWac
    "Cost_EBOS_Conductors": 21.00,   # $/kWac
    "Cost_EBOS_Combiners": 9.60,     # $/kWac — combiner boxes
    "Cost_EBOS_Grounding": 9.50,     # $/kWac
    "Cost_EBOS_Substation": 33.00,   # $/kWac
    "Cost_EBOS_Transmission": 17.00, # $/kWac — variable transmission cost
    "Cost_EBOS_NetwUpgrade": 66.00,  # $/kWac — network upgrade cost
    "Cost_EBOS_Shipping": 1.20,      # $/kg

    # -----------------------------------------------------------------------
    # 6. Fieldwork
    #    Expenses directly related to labor performed at the installation site.
    #    Labor rates include burden. EBOS, SBOS, and ESS labor are direct costs;
    #    site prep, equipment rental, and inspection are indirect costs.
    # -----------------------------------------------------------------------
    "PVElectricalLabor": 0.25,       # hr/m2 — EBOS installation labor
    "PVConstructionLabor": 0.4,      # hr/m2 — SBOS installation labor
    "ESSInstallLabor": 2.15,         # hr/kWh-cap — ESS installation labor
    "LaborBurdenRate": 0.54,         # fraction — labor burden (benefits, taxes)
    "Cost_Field_EBOSLabor": 33.00,   # $/hr — EBOS field labor rate
    "Cost_Field_SBOSLabor": 24.00,   # $/hr — SBOS field labor rate
    "Cost_Field_ESSLabor": 27.50,    # $/hr — ESS field labor rate
    "Cost_Field_SitePrep": 8.00,     # $/m2 — site preparation cost
    "Cost_Field_EqpmtRental": 10.00, # $/m2 — equipment rental
    "Cost_Field_Inspection": 1.60,   # $/m2 — inspection cost

    # -----------------------------------------------------------------------
    # 7. Officework
    #    Expenses related to labor performed off-site.
    #    All costs on this sheet are indirect costs.
    # -----------------------------------------------------------------------
    "Office_EngineeringFixed": 50_000,   # $ — fixed engineering cost
    "Office_PermitsFixed": 200_000,      # $ — fixed permitting cost
    "Office_InterconnectFixed": 85_000,  # $ — fixed interconnection cost
    "Office_OutreachFixed": 200_000,     # $ — fixed community outreach cost
    "Cost_Office_Warehousing": 1.10,     # $/m2
    "Cost_Office_Logistics": 0.10,       # $/kg
    "Cost_Office_Engineering": 3.00,     # $/m2
    "Cost_Office_Permits": 0.00,         # $/kWac
    "Cost_Office_Interconnect": 35.00,   # $/kWac
    "Cost_Office_Outreach": 1.00,        # $/m2

    # -----------------------------------------------------------------------
    # 8. Other — developer-level costs
    #    Other costs related to the operation of the project developer.
    #    These costs are affected by the size of the developer and the system.
    # -----------------------------------------------------------------------
    "SalesTaxRate": 0.058,           # fraction — sales tax on hardware
    "ContingencyRate": 0.025,        # fraction — contingency on direct costs
    "OverheadRate": 0.01,            # fraction — overhead on direct costs
    "DeveloperProfit": 0.05,         # fraction — developer profit margin
    "AnnualInstallations": 200_000,  # kWdc/yr — developer annual install volume
    "ManagementFixed": 1_000_000,    # $/yr — fixed management cost

    # -----------------------------------------------------------------------
    # 9. O&M parameters
    #    O&M includes module cleaning, inspection, component replacement,
    #    land lease, property tax, insurance, and management.
    #    Replacement prices are based on MSP (not MMP) since replacements occur
    #    well into the future when current market prices may not apply.
    # -----------------------------------------------------------------------
    "PartsLossRate": 0.002,          # fraction/yr — annual parts loss/replacement
    "InverterLossRate": 0.09,        # fraction/yr — inverter replacement rate
    "ModuleLossRate": 0.001,         # fraction/yr — module replacement rate
    "ESSLossRate": 0.025,            # fraction/yr — ESS replacement rate
    "LandArea": 3000,                # m2/kWdc — land area per unit capacity
    "PropertyTaxRate": 0.002,        # fraction/yr of land value
    "InsuranceRate": 0.0025,         # fraction/yr of total capex
}


class SolarBESS2024Q1CostModel(BaseCostModel):
    """
    Cost model for a utility-scale solar PV system with optional battery storage.

    Based on the NREL Modeled Market Price Utility-Scale PV System Cost Model
    (PVSCM), 2024 Q1. Costs are in 2023 USD (CPI-U = 304.7).

    Recommended system size range: 50–200 MWdc. A UserWarning is raised if
    SystemSize is outside this range.

    Parameters
    ----------
    name : str
        Identifier for this technology instance.
    tech_type : str
        Technology type string (should be "solar_bess").
    params : dict, optional
        User-supplied overrides merged on top of DEFAULTS.
    user_config : dict, optional
        Alias for params; used when loading directly from a config file.
    """

    def __init__(self, name=None, tech_type=None, params=None, user_config=None):
        actual_config = params or user_config or {}

        if not isinstance(actual_config, dict):
            raise ValueError("params must be a dictionary.")

        self.name = name
        self.tech_type = tech_type
        self.config = {**DEFAULTS, **actual_config}

        cfg = self.config

        # Warn if system size is outside the validated range
        system_size_mwdc = cfg["SystemSize"] / 1000
        if not (_SYSTEM_SIZE_MIN_MWDC <= system_size_mwdc <= _SYSTEM_SIZE_MAX_MWDC):
            warnings.warn(
                f"SystemSize = {system_size_mwdc:.1f} MWdc is outside the recommended "
                f"range of {_SYSTEM_SIZE_MIN_MWDC}–{_SYSTEM_SIZE_MAX_MWDC} MWdc for "
                f"this model (PVSCM 2024 Q1). Results may not be representative.",
                UserWarning,
                stacklevel=2,
            )

        # Pre-computed factors used across multiple subsystems
        self.dur_ilr = cfg["BatteryDuration"] * cfg["ESS_ILR"]  # kWh-cap / kWdc battery
        self.system_cap_kwdc = cfg["SystemSize"]

    @classmethod
    def from_config_file(cls, file_name: str):
        """Load model parameters from a JSON or YAML config file.

        Searches the following locations in order:
          1. Same directory as this module
          2. configs/ subdirectory relative to this module
          3. ../../configs/ (project-root configs folder)
          4. The literal path provided as file_name
        """
        base_dir = Path(__file__).parent.absolute()
        search_paths = [
            base_dir / file_name,
            base_dir / "configs" / file_name,
            base_dir.parent.parent / "configs" / file_name,
        ]

        full_path = next((p for p in search_paths if p.exists()), Path(file_name))

        if not full_path.exists():
            tried = "\n".join(str(p) for p in search_paths)
            raise FileNotFoundError(f"Could not find '{file_name}'. Checked:\n{tried}")

        with open(full_path) as f:
            if full_path.suffix == ".json":
                import json
                data = json.load(f)
            elif full_path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                raise ValueError(
                    f"Unsupported format: {full_path.suffix}. Use .json or .yaml"
                )

        return cls(user_config=data)

    # ------------------------------------------------------------------
    # Subsystem cost breakdowns
    # Each method returns a dict of component costs plus a single
    # "total_*" key consumed by get_cost_breakdown().
    # ------------------------------------------------------------------

    def get_pv_module_cost_breakdown(self) -> dict:
        """
        PV module manufacturing cost breakdown.

        Bifacial c-Si module assembled in SE Asia using cells from SE Asia.
        Component costs and assembly labor are direct costs; other costs
        (depreciation, electricity, maintenance, shipping) are indirect.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        mods_per_kw = 1 / (cfg["ModuleWidth"] * cfg["ModuleHeight"] * cfg["ModuleEfficiency"])
        inv_eff = 1 / cfg["ModuleEfficiency"]

        cells = cfg["Cost_Cells"] * (1 / cfg["CellToModule"])
        frame = cfg["Cost_Frame"] * (2 * (cfg["ModuleWidth"] + cfg["ModuleHeight"])) * mods_per_kw
        sheets = cfg["Cost_Sheets"] * inv_eff
        other = cfg["Cost_OtherMat"] * mods_per_kw

        ann_prod = cfg.get("ModuleAnnualProduction", 1_500_000)
        labor = (cfg["ModuleLaborFixed"] / ann_prod) + (cfg["Cost_Labor"] * cfg["ModuleLabor"] * inv_eff)
        elec = cfg["Cost_Electricity"] * cfg["ModuleElectricity"] * inv_eff
        depr = cfg["Cost_Depreciation"] * cfg["ModuleDepreciation"]
        ship = cfg["Cost_Shipping"] * cfg["ModuleWeight"] * inv_eff

        mfg_sum = cells + frame + sheets + other + labor + elec + depr + cfg["Cost_Maintenance"] + ship
        profit = cfg["ModuleMarketPrice"] - mfg_sum

        res = {
            "cells": cells, "frame": frame, "sheets": sheets, "other_material": other,
            "labor": labor, "electricity": elec, "depreciation": depr,
            "maintenance": cfg["Cost_Maintenance"], "shipping": ship, "profit": profit,
        }
        res["total_pv_module_per_kwdc"] = sum(res.values())
        return res

    def get_three_phase_inverter_cost_breakdown(self) -> dict:
        """
        Three-phase central inverter manufacturing cost breakdown.

        European 4 MWac utility-scale three-phase central inverter.
        Component costs and assembly labor are direct costs; other costs
        (depreciation, electricity, maintenance, shipping) are indirect.

        Returns costs in $/kWdc (normalized by ILR).
        """
        cfg = self.config
        ilr = cfg["ILR"]
        ann_prod = cfg.get("InverterAnnualProduction", 1_000_000)

        labor = (cfg["InverterLaborFixed"] / ann_prod) + (cfg["Cost_Inv_Labor"] * cfg["InverterLabor"])
        elec = cfg["Cost_Inv_Electricity"] * cfg["InverterElectricity"]
        ship = cfg["Cost_Inv_Shipping"] * cfg["InverterWeight"]
        depr = cfg["Cost_Inv_Depreciation"] * cfg["InverterDepreciation"]

        mfg_sum = (cfg["Cost_Inv_PCBA"] + cfg["Cost_Inv_ElecParts"] +
                   cfg["Cost_Inv_ClimateControl"] + cfg["Cost_Inv_Enclosure"] +
                   labor + elec + ship + depr + cfg["Cost_Inv_Maintenance"])
        profit = cfg["InverterMarketPrice"] - mfg_sum

        res = {
            "pcb_assemblies":    cfg["Cost_Inv_PCBA"] / ilr,
            "electrical_parts":  cfg["Cost_Inv_ElecParts"] / ilr,
            "climate_control":   cfg["Cost_Inv_ClimateControl"] / ilr,
            "enclosure":         cfg["Cost_Inv_Enclosure"] / ilr,
            "labor":             labor / ilr,
            "electricity":       elec / ilr,
            "shipping":          ship / ilr,
            "depreciation":      depr / ilr,
            "maintenance":       cfg["Cost_Inv_Maintenance"] / ilr,
            "profit":            profit / ilr,
        }
        res["total_three_phase_inverter_per_kwdc"] = sum(res.values())
        return res

    def get_li_ion_cost_breakdown(self) -> dict:
        """
        Li-ion battery cabinet manufacturing cost breakdown.

        Domestically assembled 3 MWh-cap, 1 MWac, AC-coupled pad-mounted
        battery cabinets. Component costs and on-site assembly labor are
        direct costs; other costs are indirect.

        Scaled by StorageDuration (kWh-cap/kWdc) and zeroed when IncludeESS
        is False. Returns costs in $/kWdc.
        """
        cfg = self.config
        ess_mult = int(cfg["IncludeESS"])
        dur = cfg["StorageDuration"]
        ann_prod = cfg.get("ESSAnnualProduction", 1_000_000)

        cells = (cfg["Cost_ESS_LiIonCells"] * (1 + cfg["GeneralDuty"] + cfg["Tariff301"])) * dur * ess_mult
        labor = ((cfg["ESSLaborFixed"] / ann_prod) + (cfg["Cost_ESS_Labor"] * cfg["ESSLabor"])) * dur * ess_mult
        elec  = cfg["Cost_ESS_Electricity"] * cfg["ESSElectricity"] * dur * ess_mult
        depr  = cfg["Cost_ESS_Depreciation"] * cfg["ESSDepreciation"] * dur * ess_mult
        ship  = cfg["Cost_ESS_Shipping"] * cfg["ESSWeight"] * dur * ess_mult

        conv_val = (cfg["Cost_ESS_ACDC_Conv"] / self.dur_ilr) * dur
        p_base = (cells
                  + cfg["Cost_ESS_BatteryPacks"] * dur * ess_mult
                  + cfg["Cost_ESS_Enclosure"] * dur * ess_mult
                  + conv_val * ess_mult
                  + labor + elec + depr
                  + cfg["Cost_ESS_Maintenance"] * dur * ess_mult
                  - cfg["45XPassthrough"] * cfg["Battery45X"] * dur * ess_mult
                  + ship)

        profit = ((cfg["ESSMarketPrice"] * dur) - p_base) if ess_mult else 0.0

        res = {
            "li_ion_cells":       cells,
            "battery_packs":      cfg["Cost_ESS_BatteryPacks"] * dur * ess_mult,
            "enclosure":          cfg["Cost_ESS_Enclosure"] * dur * ess_mult,
            "labor":              labor,
            "electricity":        elec,
            "depreciation":       depr,
            "maintenance":        cfg["Cost_ESS_Maintenance"] * dur * ess_mult,
            "profit":             profit,
            "shipping":           ship,
            "passthrough_credit": -cfg["45XPassthrough"] * cfg["Battery45X"] * dur * ess_mult,
        }
        res["total_li_ion_cost_per_kwdc"] = sum(res.values())
        return res

    def get_bi_directional_inverter_cost_breakdown(self) -> dict:
        """
        Bidirectional AC/DC converter cost for the ESS cabinet.

        Zeroed when IncludeESS is False. Returns cost in $/kWdc.
        """
        ess_mult = int(self.config["IncludeESS"])
        val = (self.config["Cost_ESS_ACDC_Conv"] / self.dur_ilr) * self.config["StorageDuration"] * ess_mult
        return {"bi_directional_inverter": val, "total_bi_directional_inverter_per_kwdc": val}

    def get_sbos_cost_breakdown(self) -> dict:
        """
        Structural balance-of-system cost breakdown.

        Domestically assembled single-axis trackers installed in the field.
        Component costs (torque tubes, piers, rails, fasteners, drives,
        dampers, motors, electronics) are direct costs. ESS pad and shipping
        are indirect costs.

        Torque tube and fastener costs are net of 45X tax credit passthrough.
        Returns costs in $/kWdc.
        """
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]
        row_area = cfg["RowLength"] * cfg["ModuleHeight"]
        t301 = 1 + cfg["Tariff301"]
        ess_mult = int(cfg["IncludeESS"])

        tube_net = cfg["Cost_SBOS_TorqueTubes"] - cfg["45XPassthrough"] * cfg["TorqueTube45X"]
        tubes = tube_net * cfg["TorqueTubeWeight"] * inv_eff

        piers_per_m2 = cfg["PiersPerRow"] / row_area
        piers = cfg["Cost_SBOS_Piers"] * piers_per_m2 * inv_eff

        fasteners_net = cfg["Cost_SBOS_Fasteners"] - cfg["45XPassthrough"] * cfg["Fastener45X"]
        fasteners = fasteners_net * cfg["FastenerWeight"] * inv_eff

        row_unit_m2 = 1 / row_area
        res = {
            "torque_tubes":       tubes,
            "driven_piers":       piers,
            "module_rails":       cfg["Cost_SBOS_Rails"] * (1 / cfg["ModuleWidth"]) * inv_eff * t301,
            "fasteners":          fasteners,
            "slew_drive":         cfg["Cost_SBOS_SlewDrive"] * row_unit_m2 * inv_eff * t301,
            "dampers":            cfg["Cost_SBOS_Dampers"] * piers_per_m2 * inv_eff * t301,
            "motor":              cfg["Cost_SBOS_Motor"] * row_unit_m2 * inv_eff * t301,
            "control_electronics":cfg["Cost_SBOS_Electronics"] * row_unit_m2 * inv_eff * t301,
            "shipping":           cfg["Cost_SBOS_Shipping"] * cfg["SBOSshippingWeight"] * inv_eff,
            "ess_pad":            cfg["Cost_SBOS_ESSPad"] * cfg["StorageDuration"] * ess_mult,
        }
        res["total_sbos_per_kwdc"] = sum(res.values())
        return res

    def get_ebos_cost_breakdown(self) -> dict:
        """
        Electrical balance-of-system cost breakdown.

        Electrical system components for a large array connected to a
        transmission grid. All hardware costs are direct costs; shipping
        is an indirect cost.

        Returns costs in $/kWdc (normalized by ILR).
        """
        cfg = self.config
        ilr, t301 = cfg["ILR"], 1 + cfg["Tariff301"]
        trans_fix = cfg["TransmissionFixed"] / (cfg["SystemSize"] / ilr)

        res = {
            "transformers":   cfg["Cost_EBOS_Transformers"] / ilr,
            "switches":       cfg["Cost_EBOS_Switches"] / ilr * t301,
            "breakers":       cfg["Cost_EBOS_Breakers"] / ilr * t301,
            "conductors":     cfg["Cost_EBOS_Conductors"] / ilr,
            "combiner_boxes": cfg["Cost_EBOS_Combiners"] / ilr * t301,
            "grounding":      cfg["Cost_EBOS_Grounding"] / ilr,
            "substation":     cfg["Cost_EBOS_Substation"] / ilr * t301,
            "transmission":   (trans_fix + cfg["Cost_EBOS_Transmission"]) / ilr,
            "network_upgrade":cfg["Cost_EBOS_NetwUpgrade"] / ilr,
            "shipping":       cfg["Cost_EBOS_Shipping"] * cfg["EBOSweight"] / ilr,
        }
        res["total_ebos_per_kwdc"] = sum(res.values())
        return res

    def get_fieldwork_cost_breakdown(self) -> dict:
        """
        On-site fieldwork cost breakdown.

        Expenses directly related to labor performed at the installation site.
        Labor rates include burden. EBOS, SBOS, and ESS labor are direct costs;
        site prep, equipment rental, and inspection are indirect costs.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]
        burden = 1 + cfg["LaborBurdenRate"]
        ess_mult = int(cfg["IncludeESS"])

        res = {
            "ebos_labor":       cfg["Cost_Field_EBOSLabor"] * cfg["PVElectricalLabor"] * burden * inv_eff,
            "sbos_labor":       cfg["Cost_Field_SBOSLabor"] * cfg["PVConstructionLabor"] * burden * inv_eff,
            "ess_labor":        cfg["Cost_Field_ESSLabor"] * cfg["ESSInstallLabor"] * cfg["StorageDuration"] * burden * ess_mult,
            "site_prep":        cfg["Cost_Field_SitePrep"] * inv_eff,
            "equipment_rental": cfg["Cost_Field_EqpmtRental"] * inv_eff,
            "inspection":       cfg["Cost_Field_Inspection"] * inv_eff,
        }
        res["total_fieldwork_per_kwdc"] = sum(res.values())
        return res

    def get_officework_cost_breakdown(self) -> dict:
        """
        Off-site officework cost breakdown.

        Expenses related to labor performed off-site (engineering, permitting,
        interconnection, outreach, logistics, warehousing).
        All costs are indirect costs.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]
        ilr = cfg["ILR"]
        sys_size = cfg["SystemSize"]

        res = {
            "warehousing": cfg["Cost_Office_Warehousing"] * inv_eff,
            "logistics":   cfg["Cost_Office_Logistics"] * cfg["ModuleWeight"] * inv_eff,
            "engineering": (cfg["Office_EngineeringFixed"] / sys_size) + cfg["Cost_Office_Engineering"] * inv_eff,
            "permits":     (cfg["Office_PermitsFixed"] / sys_size) + cfg["Cost_Office_Permits"] / ilr,
            "interconnect":(cfg["Office_InterconnectFixed"] / sys_size) + cfg["Cost_Office_Interconnect"] / ilr,
            "outreach":    (cfg["Office_OutreachFixed"] / sys_size) + cfg["Cost_Office_Outreach"] * inv_eff,
        }
        res["total_officework_per_kwdc"] = sum(res.values())
        return res

    def get_other_cost_breakdown(self) -> dict:
        """
        Developer-level cost breakdown (sales tax, contingency, management,
        developer profit).

        Other costs related to the operation of the project developer.
        These costs are affected by the size of the developer as well as the
        size of the system.

        Sales tax applies to hardware costs only. Contingency and management
        apply to all direct costs. Developer profit applies to the subtotal
        of all costs including tax, contingency, and management.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        hw = (self.get_pv_module_cost_breakdown()["total_pv_module_per_kwdc"]
              + self.get_three_phase_inverter_cost_breakdown()["total_three_phase_inverter_per_kwdc"]
              + self.get_li_ion_cost_breakdown()["total_li_ion_cost_per_kwdc"]
              + self.get_bi_directional_inverter_cost_breakdown()["total_bi_directional_inverter_per_kwdc"]
              + self.get_sbos_cost_breakdown()["total_sbos_per_kwdc"]
              + self.get_ebos_cost_breakdown()["total_ebos_per_kwdc"])

        direct = hw + (self.get_fieldwork_cost_breakdown()["total_fieldwork_per_kwdc"]
                       + self.get_officework_cost_breakdown()["total_officework_per_kwdc"])

        tax  = cfg["SalesTaxRate"] * hw
        cont = cfg["ContingencyRate"] * direct
        mgt  = (cfg["ManagementFixed"] / cfg["AnnualInstallations"]) + cfg["OverheadRate"] * direct

        subtotal = direct + tax + cont + mgt
        profit = cfg.get("DeveloperProfit", 0.05) * subtotal

        res = {"sales_tax": tax, "contingency": cont, "management": mgt, "developer_profit": profit}
        res["total_other_per_kwdc"] = sum(res.values())
        return res

    # ------------------------------------------------------------------
    # Dynamic attribute resolution
    # Allows calling calculate_<subsystem>_per_kwh() to get the scalar
    # total for any subsystem without writing explicit wrapper methods.
    # ------------------------------------------------------------------

    def __getattr__(self, name):
        if name.startswith("calculate_") and name.endswith("_per_kwh"):
            target = "get_" + name[10:-8] + "_breakdown"
            if hasattr(self, target):
                breakdown = getattr(self, target)()
                return lambda: breakdown[next(k for k in breakdown if k.startswith("total_"))]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_cost_breakdown(self, higher_resolution: bool = False) -> dict:
        """
        Aggregate all subsystem breakdowns into a single cost dictionary.

        Parameters
        ----------
        higher_resolution : bool
            If True, each subsystem entry contains {"total": ..., "components": {...}}.
            If False, each subsystem entry is the scalar total only.

        Returns
        -------
        dict
            Keys are subsystem names plus "total_project_cost_per_kwh".
            Values are in $/kWdc.
        """
        subsystems = {
            "pv_module":              self.get_pv_module_cost_breakdown,
            "three_phase_inverter":   self.get_three_phase_inverter_cost_breakdown,
            "li_ion":                 self.get_li_ion_cost_breakdown,
            "bi_directional_inverter":self.get_bi_directional_inverter_cost_breakdown,
            "sbos":                   self.get_sbos_cost_breakdown,
            "ebos":                   self.get_ebos_cost_breakdown,
            "fieldwork":              self.get_fieldwork_cost_breakdown,
            "officework":             self.get_officework_cost_breakdown,
            "other":                  self.get_other_cost_breakdown,
        }
        output, total = {}, 0.0
        for name, func in subsystems.items():
            sub = func()
            val = sub[next(k for k in sub if k.startswith("total_"))]
            total += val
            output[name] = (
                {"total": val, "components": {k: v for k, v in sub.items() if not k.startswith("total_")}}
                if higher_resolution else val
            )
        output["total_project_cost_per_kwh"] = total
        return output

    # ------------------------------------------------------------------
    # BaseCostModel interface
    # ------------------------------------------------------------------

    def run_capex(self) -> CapexBreakdown:
        """Return a CapexBreakdown with total cost in $/kWdc and full line items."""
        breakdown = self.get_cost_breakdown(higher_resolution=True)
        total = breakdown.pop("total_project_cost_per_kwh")
        return CapexBreakdown(total=total, unit="$/kWdc", line_items=breakdown)

    def run_design(self) -> DesignSummary:
        """
        Return key design parameters for this solar+BESS configuration.

        Always includes solar capacity and inverter capacity.
        Battery parameters are included only when IncludeESS is True.
        """
        cfg = self.config
        ilr = cfg["ILR"]
        sys_kwdc = cfg["SystemSize"]

        line_items = {
            "solar_capacity_mwdc":          sys_kwdc / 1000,
            "solar_inverter_capacity_mwac": (sys_kwdc / ilr) / 1000,
        }

        if cfg["IncludeESS"]:
            batt_dur = cfg["BatteryDuration"]
            stor_dur = cfg["StorageDuration"]
            battery_capacity_mwdc = (sys_kwdc * stor_dur / batt_dur) / 1000
            line_items.update({
                "battery_capacity_mwdc":          battery_capacity_mwdc,
                "storage_duration_h":             batt_dur,
                "battery_inverter_capacity_mwac": battery_capacity_mwdc / cfg["ESS_ILR"],
            })

        return DesignSummary(line_items=line_items)

    # run_opex() — planned, not yet implemented
    # Will surface O&M parameters already present in DEFAULTS:
    #   parts_replacement, inverter_replacement, module_replacement,
    #   ess_replacement, land_property_tax, insurance.
    # Replacement costs use MSP rather than MMP.