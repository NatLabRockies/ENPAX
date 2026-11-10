"""
solar_bess_2025Q1.py — PV System Cost Model (PVSCM), utility-scale PV + ESS, 2025 Q1

Dollar year: 2024 USD (CPI-U = 313.7). All costs and outputs are in 2024 dollars.

Based on:
    Q1-2025 Solar Photovoltaic System Cost Benchmarks — PVSCM 2025, UPV 2025Q1
    U.S. Department of Energy (DOE)
    Lawrence Berkeley National Laboratory (LBNL)
    National Laboratory of the Rockies (NLR)
    Sandia National Laboratories (SNL)
    Data: https://data.nlr.gov/submissions/304 (DOI: 10.7799/3009689)
    Ref:  https://www.energy.gov/cmei/systems/solar-photovoltaic-system-cost-benchmarks

System scope:
    50–200 MWdc, single-axis tracking, c-Si modules, central inverter.
    Optional 2.4 kWh battery energy storage per kWdc of modules.
    Costs in 2024 USD (CPI-U = 313.7).

Representative system (default configuration):
    The default system is a 100 MWdc utility-scale PV plant. Each module has a
    rated power of 600 W (2.49 m x 1.10 m), corresponding to an efficiency of
    21.9%. Bifacial modules are manufactured in the United States in a plant
    producing 1.5 GWdc/yr, using c-Si cells from Southeast Asia. The module
    producer receives a 45X credit of $70/kWdc ($68.88 in 2024 USD). In 2025 Q1
    the cells were subject to AD/CVD duties but not the Section 201 tariff.

    ~167,000 modules are mounted on single-axis trackers assembled in the field,
    occupying ~155 hectares. Most tracker components are produced domestically.

    DC cables connect to 19 utility-scale central inverters (4 MWac each) for a
    rated AC output of ~76 MWac (ILR = 1.34). Inverters are made in Europe in a
    plant producing 250 units/yr and are not subject to import tariffs.

    When an ESS is included, it consists of 60 pad-mounted Li-ion battery cabinets
    (4 MWh each, 240 MWh total), each with a 1 MWac bidirectional inverter
    (4-hour discharge), totaling 60 MWac AC-coupled with the PV inverter. The ESS
    is assembled in the US from components imported from China (25% Section 301
    tariff). The ESS producer receives a 45X credit of $10/kWh for battery
    modules ($9.84 in 2024 USD).

    O&M includes module cleaning, inspection, repairs, component replacement,
    land lease, property tax, insurance, and management. Replacement components,
    property tax, and insurance are priced at MSP, not MMP.

Pricing basis (MMP):
    PVSCM 2025 reports every cost two ways. MSP (Minimum Sustainable Price) is
    the undistorted long-run price. MMP (Modeled Market Price) adds temporary
    market distortions: import tariffs and duties raise it, 45X subsidies lower
    it, and manufacturer profit is set to match observed market prices.

    CAPEX is always reported at MMP, consistent with ``solar_bess_2024Q1``.
    MSP is used only where the spreadsheet ties a value to MSP:
      - O&M replacement components, property tax, and insurance.
      - Developer profit (the "Other" category). PVSCM 2025 gives this element
        no MMP value, so its MMP column uses the MSP-based profit.

Changes relative to solar_bess_2024Q1:
    The class, method names, subsystem breakdowns, and output structure match
    the 2024 Q1 model. PVSCM 2025 restructured its inputs, so some cost elements
    and their units changed:
      - Every cost element is now "fixed cost + cost per intrinsic unit" (e.g.
        SBOS hardware in $/m2 of modules instead of $/kg, $/pier, or $/row).
        Physical intermediates that no longer drive the cost (labor hours,
        electricity use, pier spacing, row length, labor burden) are removed.
      - New cost elements: module front/back glass, encapsulant, junction box,
        facilities and business overhead, manufacturing yield loss; inverter
        switching/filtering/other parts; ESS charge control and temperature
        control; EBOS system monitor; EBOS pad; fieldwork site management; O&M
        repair labor and EBOS replacement.
      - Manufacturer profit at MMP is an explicit input (``*ProfitMMP``) rather
        than being backed out of a component market price.
      - New toggle: ``IncludeIndirect`` (exclude indirect costs, as in PVSCM).
"""

import warnings
from pathlib import Path

import yaml

from enpax.base_model import BaseCostModel
from enpax.outputs import CapexBreakdown, OpexBreakdown, DesignSummary

# ---------------------------------------------------------------------------
# Valid system size range (MWdc)
# ---------------------------------------------------------------------------
_SYSTEM_SIZE_MIN_MWDC = 50
_SYSTEM_SIZE_MAX_MWDC = 200

DEFAULTS = {
    # -----------------------------------------------------------------------
    # 0. System parameters
    #    Representative 100 MWdc utility-scale plant with ILR = 1.34.
    #    StorageDuration = 2.4 kWh-cap/kWdc gives 240 MWh for a 100 MWdc plant.
    # -----------------------------------------------------------------------
    "SystemSize": 100_000,           # kWdc — rated DC capacity of PV array
    "ILR": 1.34,                     # kWdc/kWac — inverter loading ratio
    "StorageDuration": 2.4,          # kWh-cap/kWdc — storage per unit of solar
    "IncludeESS": True,              # toggle: include battery storage costs
    "IncludeIndirect": True,         # toggle: include indirect costs (PVSCM "I" flag)
    "GeneralDuty": 0.034,            # fraction — general import duty (ESS cells)
    "Tariff301": 0.25,               # fraction — Section 301 tariff (applied at MMP only)

    # -----------------------------------------------------------------------
    # 1. PV module parameters
    #    600 W bifacial c-Si module assembled in the USA from imported
    #    components. Fixed costs are per year for a 1.5 GWdc/yr factory.
    #
    #    Default module: 600 W, 2.49 m x 1.10 m, efficiency = 21.9%.
    #    Cells from SE Asia (AD/CVD duties, no Section 201 tariff).
    # -----------------------------------------------------------------------
    "ModuleEfficiency": 0.219,       # kWdc/m2
    "ModuleHeight": 2.49,            # m
    "ModuleWidth": 1.10,             # m
    "ModuleWeight": 12.56,           # kg/m2
    "CellToModule": 0.98,            # kWdc module / kWdc cell
    "ModuleYieldLoss": 0.01,         # fraction — modules produced but scrapped
    "ModuleDepreciation": 0.118,     # fraction/yr of capital invested
    "ModuleProfitMSP": 0.25,         # fraction/yr profit on capital invested (MSP)
    "ModuleProfitMMP": 89.89,        # $/kWdc — profit adjusted to observed market price (MMP)
    "ModuleAnnualProduction": 1_500_000,  # kWdc/yr — plant annual output
    "ModuleOverheadFixed": 24_450_000,    # $/yr — fixed business overhead (R&D, SG&A)
    "Cost_Cells": 85.33,             # $/kWdc cells (MSP)
    "Cost_Cells_MMP": 102.90,        # $/kWdc cells (MMP) — includes AD/CVD duties
    "Cost_Frame": 1.953,             # $/m of frame perimeter — Section 301 at MMP
    "Cost_FrontGlass": 4.802,        # $/m2 — 2 mm AR-coated glass
    "Cost_BackGlass": 3.513,         # $/m2 — 2 mm back glass
    "Cost_Encapsulant": 2.705,       # $/m2 — two layers POE — Section 301 at MMP
    "Cost_JunctionBox": 2.982,       # $/module — Section 301 at MMP
    "Cost_OtherMat": 5.482,          # $/module — ribbons, edge seals, pottants — Section 301 at MMP
    "Cost_Labor": 5.088,             # $/m2 — direct manufacturing labor
    "Cost_FacilitiesOverhead": 0.615,     # $/m2 — utilities and maintenance (indirect)
    "Cost_BusinessOverhead": 2.184,  # $/kWdc — warranty and insurance (indirect)
    "Cost_Depreciation": 75.71,      # $/(kWdc/yr) — facility capex per annual capacity
    "Cost_Shipping": 0.164,          # $/kg — domestic shipping incl. packaging
    "Module45X": 68.88,              # $/kWdc — 45X credit for domestic modules (MMP only)

    # -----------------------------------------------------------------------
    # 2. Three-phase central inverter parameters
    #    European 4 MWac utility-scale central inverter, 250 units/yr.
    #    Not subject to import tariffs in 2025 Q1.
    # -----------------------------------------------------------------------
    "InverterWeight": 0.935,         # kg/kWac
    "InverterYieldLoss": 0.01,       # fraction — inverters produced but scrapped
    "InverterDepreciation": 0.118,   # fraction/yr of capital invested
    "InverterProfitMSP": 0.25,       # fraction/yr profit on capital invested (MSP)
    "InverterProfitMMP": 4.458,      # $/kWac — profit adjusted to observed market price (MMP)
    "InverterAnnualProduction": 1_000_000,  # kWac/yr — plant annual output
    "InverterOverheadFixed": 4_336_000,     # $/yr — fixed business overhead (R&D, SG&A)
    "Cost_Inv_PCBA": 11.48,          # $/kWac — PCB assemblies
    "Cost_Inv_Switching": 2.974,     # $/kWac — IGBTs and main power switch
    "Cost_Inv_Filtering": 2.958,     # $/kWac — DC capacitors, inductors, sine-wave filters
    "Cost_Inv_OtherParts": 1.274,    # $/kWac — controls, sensors, buswork, cables
    "Cost_Inv_ClimateControl": 4.174,     # $/kWac — liquid cooling with chillers
    "Cost_Inv_Enclosure": 3.959,     # $/kWac — steel cabinet
    "Cost_Inv_Labor": 1.846,         # $/kWac — direct manufacturing labor
    "Cost_Inv_FacilitiesOverhead": 0.292, # $/kWac — utilities and maintenance (indirect)
    "Cost_Inv_BusinessOverhead": 2.184,   # $/kWac — warranty and insurance (indirect)
    "Cost_Inv_Depreciation": 8.059,  # $/(kWac/yr) — facility capex per annual capacity
    "Cost_Inv_Shipping": 2.282,      # $/kg

    # -----------------------------------------------------------------------
    # 3. ESS — energy storage system parameters
    #    Domestically assembled 4 MWh-cap, 1 MWac, AC-coupled pad-mounted
    #    battery cabinets with components imported from China.
    #
    #    Default: 60 cabinets x 4 MWh = 240 MWh, 60 MWac bidirectional inverter.
    #    LFP cells subject to 25% Section 301 tariff + 3.4% general duty (MMP).
    #    45X credit for battery modules applied in full at MMP.
    # -----------------------------------------------------------------------
    "Battery45X": 9.84,              # $/kWh-cap — 45X credit for battery modules (2024 USD)
    "45XPassthrough": 1.0,           # fraction — share of 45X credits reflected in MMP
    "BatteryDuration": 4,            # h — discharge duration (kWh-cap / kWac ESS)
    "ESS_ILR": 1,                    # kWac ESS / kWdc battery
    "ESSWeight": 9.4,                # kg/kWh-cap
    "CellToPack": 0.98,              # kWh-cap / kWh-cells
    "ESSYieldLoss": 0.01,            # fraction — ESS produced but scrapped
    "ESSDepreciation": 0.11,         # fraction/yr of capital invested
    "ESSProfitMSP": 0.25,            # fraction/yr profit on capital invested (MSP)
    "ESSProfitMMP": 7.321,           # $/kWh-cap — profit adjusted to observed market price (MMP)
    "ESSAnnualProduction": 1_000_000,     # kWh-cap/yr — plant annual output
    "ESSOverheadFixed": 5_442_000,   # $/yr — fixed business overhead (R&D, SG&A)
    "Cost_ESS_LiIonCells": 61.16,    # $/kWh-cells — LFP cells from China
    "Cost_ESS_BatteryPacks": 15.80,  # $/kWh-cap — module packaging — Section 301 at MMP
    "Cost_ESS_ACDC_Conv": 76.48,     # $/kWac — bidirectional AC/DC converter — Section 301 at MMP
    "Cost_ESS_ChargeControl": 25.16, # $/kWac — battery management system — Section 301 at MMP
    "Cost_ESS_TempControl": 6.442,   # $/kWh-cap — thermal management — Section 301 at MMP
    "Cost_ESS_Enclosure": 18.80,     # $/kWh-cap — container, racks, fire suppression
    "Cost_ESS_Labor": 8.379,         # $/kWh-cap — direct manufacturing labor
    "Cost_ESS_FacilitiesOverhead": 1.261, # $/kWh-cap — utilities and maintenance (indirect)
    "Cost_ESS_BusinessOverhead": 1.84,    # $/kWh-cap — warranty and insurance (indirect)
    "Cost_ESS_Depreciation": 7.014,  # $/(kWh-cap/yr) — facility capex per annual capacity
    "Cost_ESS_Shipping": 0.719,      # $/kg

    # -----------------------------------------------------------------------
    # 4. SBOS — structural balance of system
    #    Single-axis trackers installed in the field. Major components and
    #    structural steel are domestically sourced. Costs in $/m2 of modules.
    # -----------------------------------------------------------------------
    "SBOSshippingWeight": 10,        # kg/m2 — weight basis for SBOS shipping
    "EBOSPadCapacity": 50,           # kWac / m2 pad
    "ESSPadCapacity": 50,            # kWh-cap / m2 pad
    "Cost_SBOS_TorqueTubes": 7.44,   # $/m2 — galvanized steel torque tubes
    "Cost_SBOS_Piers": 5.684,        # $/m2 — galvanized I or C steel beams
    "Cost_SBOS_Rails": 2.319,        # $/m2 — module rails
    "Cost_SBOS_Fasteners": 1.066,    # $/m2 — structural fasteners
    "Cost_SBOS_OtherFasteners": 0.364,    # $/m2 — non-structural fasteners — Section 301 at MMP
    "Cost_SBOS_SlewDrive": 3.625,    # $/m2 — drive system
    "Cost_SBOS_Motor": 3.275,        # $/m2 — actuators (brushless DC motor)
    "Cost_SBOS_Electronics": 1.834,  # $/m2 — controllers (inclinometer, backup battery, comms)
    "Cost_SBOS_Dampers": 1.419,      # $/m2 — Section 301 at MMP
    "Cost_SBOS_EBOSPad": 346.4,      # $/m2 pad — concrete pad for inverter/transformer/switchgear
    "Cost_SBOS_ESSPad": 284.1,       # $/m2 pad — concrete pad for ESS containers
    "Cost_SBOS_Shipping": 0.23,      # $/kg

    # -----------------------------------------------------------------------
    # 5. EBOS — electrical balance of system
    #    Electrical components to connect a large PV array to a transmission
    #    grid. Some major components domestic, remainder from China.
    # -----------------------------------------------------------------------
    "EBOSweight": 2,                 # kg/kWac — EBOS hardware weight
    "MonitorFixed": 131_000,         # $ — fixed system monitor cost
    "TransmissionFixed": 1_883_000,  # $ — fixed transmission line cost (2.4 mi)
    "Cost_EBOS_Transformers": 51.08, # $/kWac
    "Cost_EBOS_Switches": 4.689,     # $/kWac — Section 301 at MMP
    "Cost_EBOS_Breakers": 12.03,     # $/kWac — Section 301 at MMP
    "Cost_EBOS_Conductors": 30.01,   # $/kWdc — DC & AC cables — Section 301 at MMP
    "Cost_EBOS_Combiners": 5.461,    # $/kWdc — 1500 V combiner boxes — Section 301 at MMP
    "Cost_EBOS_Grounding": 6.708,    # $/kWdc — Section 301 at MMP
    "Cost_EBOS_Substation": 56.59,   # $/kWac — Section 301 at MMP
    "Cost_EBOS_Monitor": 0.0,        # $/kWac — variable system monitor cost
    "Cost_EBOS_Transmission": 15.14, # $/kWac — variable transmission cost
    "Cost_EBOS_NetwUpgrade": 51.26,  # $/kWac — network upgrade cost
    "Cost_EBOS_Shipping": 1.125,     # $/kg

    # -----------------------------------------------------------------------
    # 6. Fieldwork
    #    Expenses directly related to labor performed at the installation site.
    #    All labor costs include burden.
    # -----------------------------------------------------------------------
    "Field_SiteManagementFixed": 1_654_000,  # $ — fixed on-site management cost
    "Cost_Field_SBOSLabor": 9.477,   # $/m2 — site prep, piers, trackers, modules
    "Cost_Field_EBOSLabor": 52.86,   # $/kWac — inverters, trenching, cabling, SCADA
    "Cost_Field_ESSLabor": 68.33,    # $/kWh-cap — construction and electrical labor
    "Cost_Field_SiteManagement": 6.915,   # $/m2 (indirect)
    "Cost_Field_SitePrep": 6.838,    # $/m2 — grading, fencing, roads, buildings (indirect)
    "Cost_Field_EqpmtRental": 11.48, # $/m2 — equipment rental (indirect)
    "Cost_Field_Inspection": 1.387,  # $/m2 — permit-compliance inspection (indirect)

    # -----------------------------------------------------------------------
    # 7. Officework
    #    Expenses related to labor performed off-site.
    #    All costs in this category are indirect costs.
    # -----------------------------------------------------------------------
    "Office_LogisticsFixed": 131_200,     # $ — fixed inventory management cost
    "Office_EngineeringFixed": 478_600,   # $ — fixed engineering cost
    "Office_PermitsFixed": 411_400,       # $ — fixed permit application fee
    "Office_InterconnectFixed": 0,        # $ — fixed interconnection cost
    "Office_OutreachFixed": 32_800,       # $ — fixed land/community outreach cost
    "Cost_Office_Warehousing": 1.043,     # $/m2
    "Cost_Office_Logistics": 0.0984,      # $/m2
    "Cost_Office_Engineering": 1.823,     # $/m2
    "Cost_Office_Permits": 0.211,         # $/kWac
    "Cost_Office_Interconnect": 58.39,    # $/kWac
    "Cost_Office_Outreach": 3.309,        # $/kWac

    # -----------------------------------------------------------------------
    # 8. Other — developer-level costs
    #    Costs related to the operation of the project developer and EPC.
    #    All costs in this category are indirect costs.
    # -----------------------------------------------------------------------
    "SalesTaxRate": 0.058,           # fraction — sales tax on hardware
    "ContingencyRate": 0.0215,       # fraction — contingency on direct costs
    "OverheadRate": 0.01,            # fraction — overhead on direct costs
    "DeveloperProfit": 0.05,         # fraction — developer profit margin
    "AnnualInstallations": 200_000,  # kWdc/yr — developer annual install volume
    "ManagementFixed": 1_363_000,    # $/yr — fixed EPC & developer salaries

    # -----------------------------------------------------------------------
    # 9. O&M parameters
    #    Annualized cost to operate and maintain the system over a 20-year
    #    lifetime. Replacements, property tax, and insurance are priced at MSP.
    # -----------------------------------------------------------------------
    "ModuleLossRate": 0.002,         # fraction/yr — module replacement rate
    "InverterLossRate": 0.09,        # fraction/yr — inverter replacement rate
    "ESSLossRate": 0.025,            # fraction/yr — ESS replacement rate
    "SBOSLossRate": 0.002,           # fraction/yr — SBOS replacement rate
    "EBOSLossRate": 0.002,           # fraction/yr — EBOS replacement rate
    "LandArea": 3000,                # m2 modules/ha land
    "PropertyTaxRate": 0.002,        # fraction/yr of system MSP
    "InsuranceRate": 0.0025,         # fraction/yr of system MSP
    "OM_NonESSRepairFixed": 59_240,  # $/yr — labor to repair non-ESS components
    "OM_ESSRepairFixed": 49_590,     # $/yr — labor to repair ESS components
    "Cost_Cleaning": 0.551,          # $/m2-yr — cleaning, vegetation and pest control
    "Cost_Inspection": 0.649,        # $/m2-yr — inspection of modules and panels
    "Cost_Land_Lease": 2002,         # $/ha-yr — land lease rate
    "Cost_OM_Management": 185_500,   # $/yr — asset management, security, administration
}


class SolarBESS2025Q1CostModel(BaseCostModel):
    """
    Cost model for a utility-scale solar PV system with optional battery storage.

    Based on the PV System Cost Model (PVSCM) 2025, UPV 2025Q1 benchmark.
    Costs are in 2024 USD (CPI-U = 313.7).

    Recommended system size range: 50–200 MWdc. A UserWarning is raised if
    SystemSize is outside this range.

    Parameters
    ----------
    name : str
        Identifier for this technology instance.
    tech_type : str
        Technology type string (should be "solar_bess_2025Q1").
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
                f"this model (PVSCM 2025 Q1). Results may not be representative.",
                UserWarning,
                stacklevel=2,
            )

        # Pre-computed factors used across multiple subsystems
        self.dur_ilr = cfg["BatteryDuration"] * cfg["ESS_ILR"]  # kWh-cap / kWac ESS
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
    # Helpers
    # ------------------------------------------------------------------

    def _incl(self, flags: str = "") -> int:
        """
        PVSCM ``includerow`` flag: 0 if the cost element is ESS-related ("E")
        and IncludeESS is False, or indirect ("I") and IncludeIndirect is False.
        """
        cfg = self.config
        if "E" in flags and not cfg["IncludeESS"]:
            return 0
        if "I" in flags and not cfg["IncludeIndirect"]:
            return 0
        return 1

    # ------------------------------------------------------------------
    # Subsystem cost breakdowns
    # Each method returns a dict of component costs plus a single
    # "total_*" key consumed by get_cost_breakdown(). Costs are at MMP.
    # ``_msp=True`` is internal: it returns MSP values, used only for the
    # O&M and developer-profit terms that PVSCM ties to MSP.
    # ------------------------------------------------------------------

    def get_pv_module_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        PV module manufacturing cost breakdown.

        600 W bifacial c-Si module assembled in the USA from imported
        components. Material costs are grossed up by manufacturing yield loss.
        At MMP: cells carry AD/CVD duties, Chinese-sourced materials carry the
        Section 301 tariff, profit matches the observed market price, and the
        45X module credit is subtracted.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        mmp = not _msp
        t301 = 1 + cfg["Tariff301"] if mmp else 1
        inv_eff = 1 / cfg["ModuleEfficiency"]                                   # m2/kWdc
        mods_per_kw = inv_eff / (cfg["ModuleWidth"] * cfg["ModuleHeight"])      # modules/kWdc
        perimeter = 2 * (cfg["ModuleWidth"] + cfg["ModuleHeight"])              # m/module
        yl = 1 / (1 - cfg["ModuleYieldLoss"])
        ind = self._incl("I")

        cell_price = cfg["Cost_Cells_MMP"] if (mmp and cfg["Cost_Cells_MMP"]) else cfg["Cost_Cells"]

        res = {
            "cells":               cell_price / cfg["CellToModule"] * yl,
            "frame":               cfg["Cost_Frame"] * t301 * perimeter * mods_per_kw * yl,
            "front_glass":         cfg["Cost_FrontGlass"] * inv_eff * yl,
            "back_glass":          cfg["Cost_BackGlass"] * inv_eff * yl,
            "encapsulant":         cfg["Cost_Encapsulant"] * t301 * inv_eff * yl,
            "junction_box":        cfg["Cost_JunctionBox"] * t301 * mods_per_kw * yl,
            "other_material":      cfg["Cost_OtherMat"] * t301 * mods_per_kw * yl,
            "labor":               cfg["Cost_Labor"] * inv_eff,
            "facilities_overhead": cfg["Cost_FacilitiesOverhead"] * inv_eff * ind,
            "business_overhead":   (cfg["ModuleOverheadFixed"] / cfg["ModuleAnnualProduction"]
                                    + cfg["Cost_BusinessOverhead"]) * ind,
        }
        # MSP profit = (facility capex + 1/4 of annual cost elements) x profit rate
        msp_profit = ((cfg["Cost_Depreciation"] + sum(res.values()) / 4)
                      * cfg["ModuleProfitMSP"] * ind) if not mmp else 0.0

        res["depreciation"] = cfg["Cost_Depreciation"] * cfg["ModuleDepreciation"] * ind
        res["profit"] = cfg["ModuleProfitMMP"] * ind if mmp else msp_profit
        res["shipping"] = cfg["Cost_Shipping"] * cfg["ModuleWeight"] * inv_eff * ind
        res["passthrough_credit"] = (-cfg["45XPassthrough"] * cfg["Module45X"] * ind) if mmp else 0.0

        res["total_pv_module_per_kwdc"] = sum(res.values())
        return res

    def get_three_phase_inverter_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Three-phase central inverter manufacturing cost breakdown.

        European 4 MWac utility-scale central inverter. Parts are grossed up
        by manufacturing yield loss. Not subject to import tariffs in 2025 Q1;
        at MMP, profit matches the observed market price.

        Returns costs in $/kWdc (normalized by ILR).
        """
        cfg = self.config
        mmp = not _msp
        ilr = cfg["ILR"]
        yl = 1 / (1 - cfg["InverterYieldLoss"])
        ind = self._incl("I")

        per_kwac = {
            "pcb_assemblies":      cfg["Cost_Inv_PCBA"] * yl,
            "switching":           cfg["Cost_Inv_Switching"] * yl,
            "filtering":           cfg["Cost_Inv_Filtering"] * yl,
            "other_parts":         cfg["Cost_Inv_OtherParts"] * yl,
            "climate_control":     cfg["Cost_Inv_ClimateControl"] * yl,
            "enclosure":           cfg["Cost_Inv_Enclosure"] * yl,
            "labor":               cfg["Cost_Inv_Labor"],
            "facilities_overhead": cfg["Cost_Inv_FacilitiesOverhead"] * ind,
            "business_overhead":   (cfg["InverterOverheadFixed"] / cfg["InverterAnnualProduction"]
                                    + cfg["Cost_Inv_BusinessOverhead"]) * ind,
        }
        msp_profit = ((cfg["Cost_Inv_Depreciation"] + sum(per_kwac.values()) / 4)
                      * cfg["InverterProfitMSP"] * ind) if not mmp else 0.0

        per_kwac["depreciation"] = cfg["Cost_Inv_Depreciation"] * cfg["InverterDepreciation"] * ind
        per_kwac["profit"] = cfg["InverterProfitMMP"] * ind if mmp else msp_profit
        per_kwac["shipping"] = cfg["Cost_Inv_Shipping"] * cfg["InverterWeight"] * ind

        res = {k: v / ilr for k, v in per_kwac.items()}
        res["total_three_phase_inverter_per_kwdc"] = sum(res.values())
        return res

    def _ess_cost_per_kwh(self, _msp: bool = False) -> dict:
        """
        Full ESS cabinet cost per kWh-cap, including the AC/DC converter.

        Shared by get_li_ion_cost_breakdown() and
        get_bi_directional_inverter_cost_breakdown(). Manufacturer profit is
        computed on the whole cabinet, converter included, as in PVSCM.
        """
        cfg = self.config
        mmp = not _msp
        t301 = 1 + cfg["Tariff301"] if mmp else 1
        cell_duty = 1 + cfg["GeneralDuty"] + cfg["Tariff301"] if mmp else 1
        yl = 1 / (1 - cfg["ESSYieldLoss"])
        ind = self._incl("I")

        res = {
            "li_ion_cells":        cfg["Cost_ESS_LiIonCells"] * cell_duty / cfg["CellToPack"] * yl,
            "battery_packs":       cfg["Cost_ESS_BatteryPacks"] * t301 * yl,
            "bi_directional_inverter": cfg["Cost_ESS_ACDC_Conv"] * t301 / self.dur_ilr * yl,
            "charge_control":      cfg["Cost_ESS_ChargeControl"] * t301 / self.dur_ilr * yl,
            "temperature_control": cfg["Cost_ESS_TempControl"] * t301 * yl,
            "enclosure":           cfg["Cost_ESS_Enclosure"] * yl,
            "labor":               cfg["Cost_ESS_Labor"],
            "facilities_overhead": cfg["Cost_ESS_FacilitiesOverhead"] * ind,
            "business_overhead":   (cfg["ESSOverheadFixed"] / cfg["ESSAnnualProduction"]
                                    + cfg["Cost_ESS_BusinessOverhead"]) * ind,
        }
        msp_profit = ((cfg["Cost_ESS_Depreciation"] + sum(res.values()) / 4)
                      * cfg["ESSProfitMSP"] * ind) if not mmp else 0.0

        res["depreciation"] = cfg["Cost_ESS_Depreciation"] * cfg["ESSDepreciation"] * ind
        res["profit"] = cfg["ESSProfitMMP"] * ind if mmp else msp_profit
        res["shipping"] = cfg["Cost_ESS_Shipping"] * cfg["ESSWeight"] * ind
        res["passthrough_credit"] = (-cfg["45XPassthrough"] * cfg["Battery45X"] * ind) if mmp else 0.0
        return res

    def get_li_ion_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Li-ion battery cabinet cost breakdown, excluding the bidirectional
        AC/DC converter (reported separately).

        Domestically assembled 4 MWh-cap, 1 MWac pad-mounted cabinets with
        components imported from China. At MMP: cells carry the Section 301
        tariff plus general duty, other imported parts carry Section 301,
        profit matches the observed market price, and the 45X battery-module
        credit is subtracted.

        Scaled by StorageDuration (kWh-cap/kWdc) and zeroed when IncludeESS
        is False. Returns costs in $/kWdc.
        """
        scale = self.config["StorageDuration"] * self._incl("E")
        per_kwh = self._ess_cost_per_kwh(_msp)
        per_kwh.pop("bi_directional_inverter")

        res = {k: v * scale for k, v in per_kwh.items()}
        res["total_li_ion_cost_per_kwdc"] = sum(res.values())
        return res

    def get_bi_directional_inverter_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Bidirectional AC/DC converter cost for the ESS cabinet.

        Zeroed when IncludeESS is False. Returns cost in $/kWdc.
        """
        scale = self.config["StorageDuration"] * self._incl("E")
        val = self._ess_cost_per_kwh(_msp)["bi_directional_inverter"] * scale
        return {"bi_directional_inverter": val, "total_bi_directional_inverter_per_kwdc": val}

    def get_sbos_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Structural balance-of-system cost breakdown.

        Single-axis trackers installed in the field. Tracker hardware is
        priced per m2 of modules; Chinese-sourced non-structural fasteners and
        dampers carry the Section 301 tariff at MMP. Concrete pads for the
        EBOS equipment and ESS containers and shipping are indirect costs.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        mmp = not _msp
        t301 = 1 + cfg["Tariff301"] if mmp else 1
        eff = cfg["ModuleEfficiency"]
        inv_eff = 1 / eff

        ebos_pad_m2 = eff / (cfg["ILR"] * cfg["EBOSPadCapacity"])               # m2 pad / m2 modules
        ess_pad_m2 = cfg["StorageDuration"] * eff / cfg["ESSPadCapacity"]       # m2 pad / m2 modules

        per_m2 = {
            "torque_tubes":        cfg["Cost_SBOS_TorqueTubes"],
            "driven_piers":        cfg["Cost_SBOS_Piers"],
            "module_rails":        cfg["Cost_SBOS_Rails"],
            "fasteners":           cfg["Cost_SBOS_Fasteners"],
            "other_fasteners":     cfg["Cost_SBOS_OtherFasteners"] * t301,
            "slew_drive":          cfg["Cost_SBOS_SlewDrive"],
            "motor":               cfg["Cost_SBOS_Motor"],
            "control_electronics": cfg["Cost_SBOS_Electronics"],
            "dampers":             cfg["Cost_SBOS_Dampers"] * t301,
            "ebos_pad":            cfg["Cost_SBOS_EBOSPad"] * ebos_pad_m2 * self._incl("I"),
            "ess_pad":             cfg["Cost_SBOS_ESSPad"] * ess_pad_m2 * self._incl("EI"),
            "shipping":            cfg["Cost_SBOS_Shipping"] * cfg["SBOSshippingWeight"] * self._incl("I"),
        }

        res = {k: v * inv_eff for k, v in per_m2.items()}
        res["total_sbos_per_kwdc"] = sum(res.values())
        return res

    def get_ebos_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Electrical balance-of-system cost breakdown.

        Electrical system components for a large array connected to a
        transmission grid. Chinese-sourced components carry the Section 301
        tariff at MMP. System monitor and transmission include fixed costs
        spread over system capacity. Shipping is an indirect cost.

        Returns costs in $/kWdc (normalized by ILR).
        """
        cfg = self.config
        mmp = not _msp
        t301 = 1 + cfg["Tariff301"] if mmp else 1
        ilr = cfg["ILR"]
        sys_kwac = cfg["SystemSize"] / ilr

        per_kwac = {
            "transformers":    cfg["Cost_EBOS_Transformers"],
            "switches":        cfg["Cost_EBOS_Switches"] * t301,
            "breakers":        cfg["Cost_EBOS_Breakers"] * t301,
            "conductors":      cfg["Cost_EBOS_Conductors"] * t301 * ilr,
            "combiner_boxes":  cfg["Cost_EBOS_Combiners"] * t301 * ilr,
            "grounding":       cfg["Cost_EBOS_Grounding"] * t301 * ilr,
            "substation":      cfg["Cost_EBOS_Substation"] * t301,
            "system_monitor":  cfg["MonitorFixed"] / sys_kwac + cfg["Cost_EBOS_Monitor"],
            "transmission":    cfg["TransmissionFixed"] / sys_kwac + cfg["Cost_EBOS_Transmission"],
            "network_upgrade": cfg["Cost_EBOS_NetwUpgrade"],
            "shipping":        cfg["Cost_EBOS_Shipping"] * cfg["EBOSweight"] * self._incl("I"),
        }

        res = {k: v / ilr for k, v in per_kwac.items()}
        res["total_ebos_per_kwdc"] = sum(res.values())
        return res

    def get_fieldwork_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        On-site fieldwork cost breakdown.

        Expenses directly related to labor performed at the installation site.
        Labor rates include burden. SBOS, EBOS, and ESS labor are direct costs;
        site management, site prep, equipment rental, and inspection are
        indirect costs. Fieldwork has no market distortions (MSP = MMP).

        Returns costs in $/kWdc.
        """
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]
        ind = self._incl("I")

        res = {
            "sbos_labor":       cfg["Cost_Field_SBOSLabor"] * inv_eff,
            "ebos_labor":       cfg["Cost_Field_EBOSLabor"] / cfg["ILR"],
            "ess_labor":        cfg["Cost_Field_ESSLabor"] * cfg["StorageDuration"] * self._incl("E"),
            "site_management":  (cfg["Field_SiteManagementFixed"] / cfg["SystemSize"]
                                 + cfg["Cost_Field_SiteManagement"] * inv_eff) * ind,
            "site_prep":        cfg["Cost_Field_SitePrep"] * inv_eff * ind,
            "equipment_rental": cfg["Cost_Field_EqpmtRental"] * inv_eff * ind,
            "inspection":       cfg["Cost_Field_Inspection"] * inv_eff * ind,
        }
        res["total_fieldwork_per_kwdc"] = sum(res.values())
        return res

    def get_officework_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Off-site officework cost breakdown.

        Expenses related to labor performed off-site (warehousing, logistics,
        engineering, permitting, interconnection, outreach). All costs are
        indirect costs. Officework has no market distortions (MSP = MMP).

        Returns costs in $/kWdc.
        """
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]
        ilr = cfg["ILR"]
        sys_size = cfg["SystemSize"]
        ind = self._incl("I")

        res = {
            "warehousing":  cfg["Cost_Office_Warehousing"] * inv_eff,
            "logistics":    (cfg["Office_LogisticsFixed"] / sys_size) + cfg["Cost_Office_Logistics"] * inv_eff,
            "engineering":  (cfg["Office_EngineeringFixed"] / sys_size) + cfg["Cost_Office_Engineering"] * inv_eff,
            "permits":      (cfg["Office_PermitsFixed"] / sys_size) + cfg["Cost_Office_Permits"] / ilr,
            "interconnect": (cfg["Office_InterconnectFixed"] / sys_size) + cfg["Cost_Office_Interconnect"] / ilr,
            "outreach":     (cfg["Office_OutreachFixed"] / sys_size) + cfg["Cost_Office_Outreach"] / ilr,
        }
        res = {k: v * ind for k, v in res.items()}
        res["total_officework_per_kwdc"] = sum(res.values())
        return res

    def _direct_and_hardware(self, _msp: bool) -> tuple:
        """Return (hardware, hardware + fieldwork + officework) in $/kWdc."""
        hw = (self.get_pv_module_cost_breakdown(_msp)["total_pv_module_per_kwdc"]
              + self.get_three_phase_inverter_cost_breakdown(_msp)["total_three_phase_inverter_per_kwdc"]
              + self.get_li_ion_cost_breakdown(_msp)["total_li_ion_cost_per_kwdc"]
              + self.get_bi_directional_inverter_cost_breakdown(_msp)["total_bi_directional_inverter_per_kwdc"]
              + self.get_sbos_cost_breakdown(_msp)["total_sbos_per_kwdc"]
              + self.get_ebos_cost_breakdown(_msp)["total_ebos_per_kwdc"])
        direct = hw + (self.get_fieldwork_cost_breakdown(_msp)["total_fieldwork_per_kwdc"]
                       + self.get_officework_cost_breakdown(_msp)["total_officework_per_kwdc"])
        return hw, direct

    def get_other_cost_breakdown(self, _msp: bool = False) -> dict:
        """
        Developer-level cost breakdown (sales tax, contingency, management,
        developer profit).

        Costs related to the operation of the project developer and EPC
        contractor. Sales tax applies to hardware costs only. Contingency and
        management apply to hardware + fieldwork + officework. Developer
        profit applies to that subtotal plus tax, contingency, and management.

        Sales tax, contingency, and management are at MMP. Developer profit
        is computed on the MSP subtotal, because PVSCM 2025 gives this element
        no MMP value. All costs are indirect costs.

        Returns costs in $/kWdc.
        """
        cfg = self.config
        ind = self._incl("I")

        def _pre_profit(msp):
            hw, direct = self._direct_and_hardware(msp)
            tax = cfg["SalesTaxRate"] * hw
            cont = cfg["ContingencyRate"] * direct
            mgt = (cfg["ManagementFixed"] / cfg["AnnualInstallations"]) + cfg["OverheadRate"] * direct
            return direct, tax, cont, mgt

        direct, tax, cont, mgt = _pre_profit(_msp)
        msp_terms = (direct, tax, cont, mgt) if _msp else _pre_profit(True)
        profit = cfg["DeveloperProfit"] * sum(msp_terms)

        res = {"sales_tax": tax, "contingency": cont, "management": mgt, "developer_profit": profit}
        res = {k: v * ind for k, v in res.items()}
        res["total_other_per_kwdc"] = sum(res.values())
        return res

    def get_om_cost_breakdown(self) -> dict:
        """
        Annual O&M cost breakdown.

        Covers recurring costs of operating and maintaining the plant over a
        20-year life: cleaning, inspection, repair labor, component
        replacements (modules, inverters, ESS, SBOS, EBOS), land lease,
        property tax, insurance, and management.

        Replacement components, property tax, and insurance are priced at MSP,
        as in PVSCM 2025: replacements happen well into the future, when
        today's market distortions are not expected to apply. ESS terms are
        zeroed when IncludeESS is False.

        Returns costs in $/kWdc-yr.
        """
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]  # m2/kWdc
        sys_size = cfg["SystemSize"]
        ind = self._incl("I")
        ess = self._incl("E")

        msp = self.get_cost_breakdown(_msp=True)
        new_ess = msp["li_ion"] + msp["bi_directional_inverter"]
        system_msp = msp["total_project_cost_per_kwdc"]

        res = {
            "cleaning":        cfg["Cost_Cleaning"] * inv_eff,
            "inspection":      cfg["Cost_Inspection"] * inv_eff,
            "non_ess_repair":  cfg["OM_NonESSRepairFixed"] / sys_size,
            "ess_repair":      cfg["OM_ESSRepairFixed"] / sys_size * ess,
            "new_modules":     msp["pv_module"] * cfg["ModuleLossRate"],
            "new_inverters":   msp["three_phase_inverter"] * cfg["InverterLossRate"],
            "new_ess":         new_ess * cfg["ESSLossRate"] * ess,
            "new_sbos":        msp["sbos"] * cfg["SBOSLossRate"],
            "new_ebos":        msp["ebos"] * cfg["EBOSLossRate"],
            # Cost_Land_Lease [$/ha-yr] / LandArea [m2 modules / ha land] x m2/kWdc
            "land_lease":      cfg["Cost_Land_Lease"] / cfg["LandArea"] * inv_eff * ind,
            "property_tax":    system_msp * cfg["PropertyTaxRate"] * ind,
            "insurance":       system_msp * cfg["InsuranceRate"] * ind,
            "management":      cfg["Cost_OM_Management"] / sys_size * ind,
        }
        res["total_om_per_kwdc_yr"] = sum(res.values())
        return res

    # ------------------------------------------------------------------
    # Dynamic attribute resolution
    # Allows calling calculate_<subsystem>_per_kwdc() to get the scalar
    # total for any subsystem without writing explicit wrapper methods.
    # ------------------------------------------------------------------

    def __getattr__(self, name):
        if name.startswith("calculate_") and name.endswith("_per_kwdc"):
            target = "get_" + name[10:-len("_per_kwdc")] + "_breakdown"
            if hasattr(self, target):
                breakdown = getattr(self, target)()
                return lambda: breakdown[next(k for k in breakdown if k.startswith("total_"))]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_cost_breakdown(self, higher_resolution: bool = False, _msp: bool = False) -> dict:
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
            Keys are subsystem names plus "total_project_cost_per_kwdc".
            Values are in $/kWdc at MMP.
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
            sub = func(_msp)
            val = sub[next(k for k in sub if k.startswith("total_"))]
            total += val
            output[name] = (
                {"total": val, "components": {k: v for k, v in sub.items() if not k.startswith("total_")}}
                if higher_resolution else val
            )
        output["total_project_cost_per_kwdc"] = total
        return output

    # ------------------------------------------------------------------
    # BaseCostModel interface
    # ------------------------------------------------------------------

    def run_capex(self) -> CapexBreakdown:
        """Return a CapexBreakdown with total cost in $/kWdc and full line items."""
        breakdown = self.get_cost_breakdown(higher_resolution=True)
        total = breakdown.pop("total_project_cost_per_kwdc")
        return CapexBreakdown(total=total, unit="$/kWdc", line_items=breakdown)

    def run_opex(self) -> OpexBreakdown:
        """
        Return an OpexBreakdown with total annual O&M cost in $/kWdc-yr and
        full line items.
        """
        breakdown = self.get_om_cost_breakdown()
        annual_total = breakdown.pop("total_om_per_kwdc_yr")
        return OpexBreakdown(annual_total=annual_total, unit="$/kWdc-yr", line_items=breakdown)

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
