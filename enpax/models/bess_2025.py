"""
bess.py — Standalone Battery Energy Storage System (BESS) Cost Model

CAPEX Cost based on:
    Cole, Wesley, Vignesh Ramasamy, and Merve Turan. 2025.
    Cost Projections for Utility-Scale Battery Storage: 2025 Update.
    Golden, CO: National Renewable Energy Laboratory.
    NREL/TP-6A40-93281.
    https://www.nrel.gov/docs/fy25osti/93281.pdf

O&M Cost adapted from on:
    Modeled Market Price Utility-Scale PV System Cost Model (PVSCM), 2024 Q1
    U.S. Department of Energy (DOE)
    Lawrence Berkeley National Laboratory (LBNL)
    National Laboratory of the Rockies (NLR)
    Sandia National Laboratory (SNL)
    Ref: https://www.energy.gov/cmei/systems/solar-photovoltaic-system-cost-benchmarks

Representative system (default configuration):
    Domestically assembled ESS comprised of 80 pad-mounted lithium-ion battery
    cabinets, each with an energy storage capacity of 3 MWh, for a total of
    240 MWh of storage. Each ESS cabinet includes a bidirectional inverter rated
    at 750 kWac (4-hour discharge rate), for a total of 60 MWac of inverter
    capacity. 
    Costs are in 2024 USD (CPI-U = 313.7).

    The battery cells are imported and subject to import tariffs. The ESS
    producer receives a 45X tax credit of $10/kWh for battery modules; half
    of this credit is assumed to be passed along to the project developer in
    the form of reduced ESS pricing.

    EPC installation costs (permitting, interconnection, overhead) are
    normalized by the developer's annual installation volume.
"""

from pathlib import Path

import pandas as pd
import yaml

from enpax.base_model import BaseCostModel
from enpax.outputs import CapexBreakdown, OpexBreakdown, DesignSummary


DEFAULTS = {
    # -----------------------------------------------------------------------
    # 0. Project parameters
    #    Default: 60 MWdc / 240 MWh system (80 × 3 MWh cabinets),
    #    4-hour discharge duration, AC-coupled bidirectional inverter at 1:1
    #    power-to-capacity ratio (ESS_ILR = 1).
    # -----------------------------------------------------------------------
    "BatteryCapacity": 60,          # MWdc — nameplate DC battery capacity
    "BatteryDuration": 4,           # h — discharge duration at rated power
    "ESS_ILR": 1,                   # kWac/kWdc — inverter-to-battery ratio
    "AnnualESSProduction": 1_000_000,    # kWh-cap/yr — ESS plant annual output
    "AnnualEPCInstallation": 600_000,    # kWh-cap/yr — developer annual install volume

    # -----------------------------------------------------------------------
    # 1. Li-ion battery cabinets
    #    Domestically assembled 3 MWh-cap, 1 MWac, pad-mounted battery cabinets.
    #    Component costs and on-site assembly labor are direct costs;
    #    depreciation, electricity, maintenance, and shipping are indirect costs.
    #
    #    Battery cells are imported and subject to Section 301 tariff (25%).
    #    A general import duty of 3.4% also applies.
    #    45X tax credit = $10/kWh for battery modules; 50% passed to developer.
    # -----------------------------------------------------------------------
    "LiIonCells": 75.0,             # $/kWh-cap — cell cost before tariffs
    "GeneralDuty": 0.034,           # fraction — general import duty on cells
    "Tariff301": 0.25,              # fraction — Section 301 tariff on cells
    "BatteryPacks": 25.0,           # $/kWh-cap — battery pack hardware
    "Enclosure": 20.0,              # $/kWh-cap — cabinet enclosure
    "LaborCost": 2_500_000,         # $/yr — fixed plant labor cost
    "LaborRate": 34.0,              # $/hr — variable assembly labor rate
    "ESSLabor": 0.22,               # hr/kWh-cap — labor per unit capacity
    "ElectricityCost": 0.08,        # $/kWh — plant electricity cost
    "ESSElectricity": 30.5,         # kWh/kWh-cap — electricity consumed per unit
    "DepreciationCost": 7.0,        # $/kWh-cap/yr — capital depreciation rate
    "ESSDepreciation": 0.11,        # fraction/yr of capital invested
    "MaintenanceCost": 0.28,        # $/kWh-cap — maintenance cost per unit
    "ESSProfit": 0.25,              # fraction — profit margin on MSP
    "ShippingCost": 1.0,            # $/kg — shipping rate
    "ESSWeight": 9.4,               # kg/kWh-cap — cabinet weight per unit capacity
    "Battery45X": 10,               # $/kWh-cap — 45X tax credit for battery modules
    "45XPassthrough": 0.5,          # fraction — share of 45X credit passed to developer
    "ESSMarketPrice": 228,          # $/kWh-cap — modeled market price (MMP)

    # -----------------------------------------------------------------------
    # 2. Bidirectional inverter
    #    AC-coupled bidirectional inverter integrated into the ESS cabinet.
    #    Default: 750 kWac per cabinet (1 MWac per MWh at 4-hour rate),
    #    60 MWac total for the 60 MWdc / 240 MWh system.
    # -----------------------------------------------------------------------
    "BidirectionalInverter": 100.0,  # $/kWac — inverter cost per unit AC capacity

    # -----------------------------------------------------------------------
    # 3. SBOS — structural balance of system
    #    Site preparation and concrete pads for pad-mounted battery cabinets.
    #    All costs are direct costs.
    #
    #    Area is computed from container footprint (ESSInstallationArea) and
    #    container energy capacity (ESSContainer).
    # -----------------------------------------------------------------------
    "SitePrepStaging": 50.0,        # $/m2 — site preparation and staging
    "ConcretePads": 0.10,           # $/kg — concrete pad material cost
    "ESSInstallationArea": 80,      # m2/container — footprint per cabinet
    "ESSContainer": 3,              # MWh/container — energy per cabinet
    "ConcretePadThickness": 0.5,    # m — pad thickness
    "ConcreteDensity": 2400,        # kg/m3 — concrete density

    # -----------------------------------------------------------------------
    # 4. EBOS — electrical balance of system
    #    Electrical components for a utility-scale BESS connected to the grid.
    #    All hardware costs are direct costs; shipping is an indirect cost.
    #
    #    Transmission cost includes a fixed component (TransmissionCost) spread
    #    over the system's AC capacity, plus a variable per-kWac rate.
    #    NetworkUpgrade defaults to 0; set to non-zero for constrained sites.
    # -----------------------------------------------------------------------
    "Transformer": 40.0,            # $/kWac
    "SwitchGear": 6.5,              # $/kWac
    "Conductors": 21.0,             # $/kWac
    "BreakerDC": 15.0,              # $/kWac — DC breaker
    "Grounding": 9.5,               # $/kWac
    "SCADA": 3.5,                   # $/kWac — monitoring and control
    "Substation": 33.0,             # $/kWac
    "TransmissionCost": 680_000,    # $ — fixed transmission interconnect cost
    "Transmission": 17.0,           # $/kWac — variable transmission cost
    "NetworkUpgrade": 0.0,          # $/kWac — grid network upgrade (site-specific)
    "EBOSShipping": 1.2,            # $/kg
    "EBOSWeight": 2,                # kg/kWac — EBOS hardware weight

    # -----------------------------------------------------------------------
    # 5. Installation
    #    On-site labor for ESS cabinet installation.
    #    Labor rate includes burden (benefits, taxes, overhead).
    #    Installation cost is normalized by container footprint area.
    # -----------------------------------------------------------------------
    "ESSInstallHourlyLabor": 27.5,  # $/hr — installation labor rate
    "ESSInstallLabor": 2.15,        # hr/kWh-cap — labor hours per unit capacity
    "LaborBurdenRate": 0.54,        # fraction — labor burden on top of base rate

    # -----------------------------------------------------------------------
    # 6. Permitting
    #    Fixed permitting cost spread over developer's annual installation volume.
    # -----------------------------------------------------------------------
    "Permits": 200_000,             # $ — fixed permitting cost per project

    # -----------------------------------------------------------------------
    # 7. Interconnection
    #    Fixed plus variable interconnection costs.
    #    Set InterconnectFixed = 0 and Interconnect = 0 in the config to
    #    exclude interconnection (e.g. when co-located with a solar plant).
    # -----------------------------------------------------------------------
    "InterconnectFixed": 85_000,    # $ — fixed interconnection cost
    "Interconnect": 35.0,           # $/kWac — variable interconnection cost

    # -----------------------------------------------------------------------
    # 8. Sales tax
    #    Applied to hardware (core_basis: li-ion + inverter + SBOS + EBOS).
    # -----------------------------------------------------------------------
    "SalesTaxRate": 0.058,          # fraction — sales tax rate on hardware

    # -----------------------------------------------------------------------
    # 9. Contingency
    #    Applied to hardware (core_basis) as a fraction of direct hardware costs.
    # -----------------------------------------------------------------------
    "ContingencyRate": 0.025,       # fraction — contingency on hardware costs

    # -----------------------------------------------------------------------
    # 10. EPC overhead
    #     Indirect costs associated with EPC project management and logistics.
    #     All costs are indirect. Normalized by container footprint area and
    #     annual installation volume.
    # -----------------------------------------------------------------------
    "Warehousing": 1.1,             # $/m2 — warehousing cost per unit area
    "Logistics": 0.1,               # $/kg — logistics cost per unit weight
    "Engineering": 3.0,             # $/m2 — variable engineering cost
    "EngineeringFixed": 50_000,     # $ — fixed engineering cost per project
    "Outreach": 1.0,                # $/m2 — community outreach cost
    "OutreachFixed": 200_000,       # $ — fixed outreach cost per project
    "ManagementFixed": 1_000_000,   # $ — fixed project management cost
    "OverheadRate": 0.01,           # fraction — overhead on hardware costs

    # -----------------------------------------------------------------------
    # 11. Developer profit
    #     Applied to hardware (core_basis) as a fraction of direct hardware costs.
    # -----------------------------------------------------------------------
    "DeveloperProfit": 0.05,        # fraction — developer profit margin

    # -----------------------------------------------------------------------
    # 12. O&M parameters
    #    O&M includes SBOS replacement, inverter replacement, ESS replacement,
    #    land lease, property tax, insurance, and management.
    #    Replacement prices are based on MSP (not MMP) since replacements occur
    #    well into the future when current market prices may not apply.
    # -----------------------------------------------------------------------
    "PartsLossRate": 0.002,          # fraction/yr — annual parts loss/replacement
    "InverterLossRate": 0.09,        # fraction/yr — inverter replacement rate
    "ESSLossRate": 0.025,            # fraction/yr — ESS replacement rate
    #"LandArea": 872,                 # m2 containers/ha land — containers m2 / land area
    "LandArea": 2000,                 # m2 containers/ha land — containers m2 / land area
    "PropertyTaxRate": 0.002,        # fraction/yr of land value
    "InsuranceRate": 0.0025,         # fraction/yr of total capex
    "Cost_Land_Lease": 1800,       # $/ha-yr — land lease rate
    #"Cost_Land_Lease": 180000,       # $/ha-yr — land lease rate
    "Cost_OM_Management": 180_000,   # $/yr — fixed O&M management cost
}


class BESS2025CostModel(BaseCostModel):
    """
    Cost model for a standalone utility-scale battery energy storage system.

    Based on NREL/TP-6A40-93281 (Cole et al., 2025): Cost Projections for
    Utility-Scale Battery Storage: 2025 Update. Costs are in 2024 USD.

    The default system is 60 MWdc / 240 MWh (80 × 3 MWh cabinets) with a
    4-hour discharge duration and a 60 MWac bidirectional inverter.

    Parameters
    ----------
    name : str
        Identifier for this technology instance.
    tech_type : str
        Technology type string (should be "bess").
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

        # Pre-computed factors used across multiple subsystems
        cfg = self.config
        self.dur_ilr = cfg["BatteryDuration"] * cfg["ESS_ILR"]  # h × kWac/kWdc
        self.area_per_kwh = cfg["ESSInstallationArea"] / cfg["ESSContainer"] / 1000  # m2/kWh-cap

    @property
    def core_basis(self) -> float:
        """
        Hardware cost basis used for sales tax, contingency, and profit.

        Equals the sum of li-ion cabinets + bidirectional inverter + SBOS + EBOS,
        all in $/kWh-cap.
        """
        return (self.calculate_li_ion_cost_per_kwh()
                + self.calculate_bi_directional_inverter_cost_per_kwh()
                + self.calculate_sbos_cost_per_kwh()
                + self.calculate_ebos_cost_per_kwh())

    # ------------------------------------------------------------------
    # Subsystem cost breakdowns
    # Each method returns a dict of component costs plus a single
    # "total_*" key consumed by get_cost_breakdown().
    # ------------------------------------------------------------------

    def get_li_ion_cost_breakdown(self) -> dict:
        """
        Li-ion battery cabinet manufacturing cost breakdown.

        Domestically assembled 3 MWh-cap, 1 MWac pad-mounted cabinets.
        Component costs and on-site assembly labor are direct costs;
        depreciation, electricity, maintenance, and shipping are indirect.

        Cell cost includes Section 301 tariff (25%) and general duty (3.4%).
        45X passthrough credit reduces effective cell cost.
        Profit is back-calculated from the modeled market price (MMP).

        Returns costs in $/kWh-cap.
        """
        cfg = self.config
        cells = cfg["LiIonCells"] * (1 + cfg["GeneralDuty"] + cfg["Tariff301"])
        labor = (cfg["LaborCost"] / cfg["AnnualESSProduction"]) + (cfg["LaborRate"] * cfg["ESSLabor"])
        elec  = cfg["ElectricityCost"] * cfg["ESSElectricity"]
        depr  = cfg["DepreciationCost"] * cfg["ESSDepreciation"]

        # Profit base: all manufacturing inputs including inverter (normalized by dur_ilr)
        p_base = (cells + cfg["BatteryPacks"] + cfg["Enclosure"]
                  + (cfg["BidirectionalInverter"] / self.dur_ilr)
                  + labor + elec + depr + cfg["MaintenanceCost"]
                  - (cfg["45XPassthrough"] * cfg["Battery45X"])
                  + (cfg["ShippingCost"] * cfg["ESSWeight"]))

        res = {
            "li_ion_cells":       cells,
            "battery_packs":      cfg["BatteryPacks"],
            "enclosure":          cfg["Enclosure"],
            "labor":              labor,
            "electricity":        elec,
            "depreciation":       depr,
            "maintenance":        cfg["MaintenanceCost"],
            "profit":             cfg["ESSMarketPrice"] - p_base,
            "shipping":           cfg["ShippingCost"] * cfg["ESSWeight"],
            "passthrough_credit": -cfg["45XPassthrough"] * cfg["Battery45X"],
        }
        res["total_li_ion_cost_per_kwh"] = sum(res.values())
        return res

    def get_bi_directional_inverter_cost_breakdown(self) -> dict:
        """
        Bidirectional AC/DC inverter cost breakdown.

        Cost is normalized by discharge duration × ESS_ILR to convert from
        $/kWac to $/kWh-cap.

        Returns cost in $/kWh-cap.
        """
        val = self.config["BidirectionalInverter"] / self.dur_ilr
        return {"bi_directional_inverter": val, "total_bi_directional_inverter_per_kwh": val}

    def get_sbos_cost_breakdown(self) -> dict:
        """
        Structural balance-of-system cost breakdown.

        Includes site preparation/staging and concrete pads for pad-mounted
        battery cabinets. All costs are direct costs.

        Area basis is derived from cabinet footprint (ESSInstallationArea)
        and cabinet energy capacity (ESSContainer).

        Returns costs in $/kWh-cap.
        """
        cfg = self.config
        prep = cfg["SitePrepStaging"] * self.area_per_kwh
        pads = (cfg["ConcretePads"] * cfg["ConcretePadThickness"]
                * cfg["ConcreteDensity"] * self.area_per_kwh)
        return {"site_prep": prep, "concrete_pads": pads, "total_sbos_per_kwh": prep + pads}

    def get_ebos_cost_breakdown(self) -> dict:
        """
        Electrical balance-of-system cost breakdown.

        Electrical components for a utility-scale BESS connected to the grid.
        All hardware costs are direct costs; shipping is an indirect cost.

        Costs are normalized by discharge duration × ESS_ILR (dur_ilr) to
        convert from $/kWac to $/kWh-cap.

        Returns costs in $/kWh-cap.
        """
        cfg, d_i = self.config, self.dur_ilr
        t301 = 1 + cfg["Tariff301"]

        res = {
            "transformer":    cfg["Transformer"] / d_i,
            "switch_gear":    cfg["SwitchGear"] / d_i * t301,
            "conductors":     cfg["Conductors"] / d_i,
            "breaker_dc":     cfg["BreakerDC"] / d_i * t301,
            "grounding":      cfg["Grounding"] / d_i,
            "scada":          cfg["SCADA"] / d_i,
            "substation":     cfg["Substation"] / d_i * t301,
            "transmission":   (cfg.get("TransmissionCost", 0)
                               / (cfg["BatteryCapacity"] / cfg["ESS_ILR"] * 1000)
                               + cfg["Transmission"]) / d_i,
            "network_upgrade":cfg["NetworkUpgrade"] / d_i,
            "shipping":       cfg["EBOSShipping"] * cfg["EBOSWeight"] / d_i,
        }
        res["total_ebos_per_kwh"] = sum(res.values())
        return res

    def get_installation_cost_breakdown(self) -> dict:
        """
        On-site ESS installation labor cost breakdown.

        Labor rate includes burden (benefits, taxes, overhead).
        Cost is normalized by cabinet footprint area per unit capacity.

        Returns cost in $/kWh-cap.
        """
        cfg = self.config
        val = (cfg["ESSInstallHourlyLabor"] * cfg["ESSInstallLabor"]
               * (1 + cfg["LaborBurdenRate"]) * self.area_per_kwh)
        return {"installation": val, "total_installation_per_kwh": val}

    def get_permitting_cost_breakdown(self) -> dict:
        """
        Permitting cost breakdown.

        Fixed permitting cost spread over the developer's annual installation
        volume (AnnualEPCInstallation).

        Returns cost in $/kWh-cap.
        """
        val = self.config["Permits"] / self.config["AnnualEPCInstallation"]
        return {"permitting": val, "total_permitting_per_kwh": val}

    def get_interconnection_cost_breakdown(self) -> dict:
        """
        Interconnection cost breakdown.

        Includes a fixed cost (spread over annual installation volume) plus
        a variable cost per kWac normalized to $/kWh-cap via dur_ilr.

        Set both InterconnectFixed and Interconnect to 0 in the config to
        exclude interconnection costs (e.g. when co-located with a solar plant).

        Returns cost in $/kWh-cap.
        """
        cfg = self.config
        val = ((cfg["InterconnectFixed"] / cfg["AnnualEPCInstallation"])
               + (cfg["Interconnect"] / self.dur_ilr))
        return {"interconnection": val, "total_interconnection_per_kwh": val}

    def _basis_rate_calc(self, rate_key: str, total_key: str, label: str) -> dict:
        """Helper for costs computed as core_basis × a config rate."""
        val = self.core_basis * self.config[rate_key]
        return {label: val, total_key: val}

    def get_sales_tax_cost_breakdown(self) -> dict:
        """
        Sales tax on hardware (core_basis × SalesTaxRate).

        Returns cost in $/kWh-cap.
        """
        return self._basis_rate_calc("SalesTaxRate", "total_sales_tax_per_kwh", "sales_tax")

    def get_contingency_cost_breakdown(self) -> dict:
        """
        Contingency on hardware (core_basis × ContingencyRate).

        Returns cost in $/kWh-cap.
        """
        return self._basis_rate_calc("ContingencyRate", "total_contingency_per_kwh", "contingency")

    def get_profit_cost_breakdown(self) -> dict:
        """
        Developer profit on hardware (core_basis × DeveloperProfit).

        Returns cost in $/kWh-cap.
        """
        return self._basis_rate_calc("DeveloperProfit", "total_profit_per_kwh", "profit")

    def get_epc_overhead_cost_breakdown(self) -> dict:
        """
        EPC overhead cost breakdown.

        Indirect costs for EPC project management, logistics, engineering,
        outreach, and warehousing. All costs are indirect.

        Costs are normalized by cabinet footprint area and annual installation
        volume. Management includes a fixed component plus an overhead rate
        applied to the hardware cost basis.

        Returns costs in $/kWh-cap.
        """
        cfg, a_m = self.config, self.area_per_kwh
        ann = cfg["AnnualEPCInstallation"]
        res = {
            "warehousing": cfg["Warehousing"] * a_m,
            "logistics":   cfg["Logistics"] * cfg["ESSWeight"],
            "engineering": (cfg["EngineeringFixed"] / ann) + cfg["Engineering"] * a_m,
            "outreach":    (cfg["OutreachFixed"] / ann) + cfg["Outreach"] * a_m,
            "management":  (cfg["ManagementFixed"] / ann) + cfg["OverheadRate"] * self.core_basis,
        }
        res["total_epc_overhead_per_kwh"] = sum(res.values())
        return res

    def get_om_cost_breakdown(self) -> dict:
        """
        Annual O&M cost breakdown.
 
        Covers all recurring costs associated with operating and maintaining the
        plant: component replacements (BOS, inverters, ESS), land lease, property 
        tax, insurance, and management.
 
        New ESS cost is zeroed when IncludeESS is False. Replacement costs use
        MSP rather than MMP, as replacements occur well into the future when
        current market prices may not apply.

        Replacement costs use MMP rather than MSP.
 
        Returns costs in $/kWh-cap.
        """
        cfg = self.config
        batt_kwh = cfg["BatteryCapacity"] * cfg["BatteryDuration"] * 1000  
 
 
        # --- Component replacements ---
        new_bos = (
            self.get_sbos_cost_breakdown()["total_sbos_per_kwh"]
            * cfg["PartsLossRate"]
        )
        new_inverters = (
            self.get_bi_directional_inverter_cost_breakdown()["total_bi_directional_inverter_per_kwh"]
            * cfg["InverterLossRate"]
        )
        new_ess = (
            (
                self.get_li_ion_cost_breakdown()["total_li_ion_cost_per_kwh"]
            )
            * cfg["ESSLossRate"]
        )
 
        # --- Site & financial costs ---
        # Land lease: Cost_Land_Lease [$/ha-yr] × LandArea [ha/kWdc] 
        land_lease = cfg["Cost_Land_Lease"] / cfg["LandArea"] * self.area_per_kwh
 
        total_capex = self.get_cost_breakdown()["total_project_cost_per_kwh"]
        property_tax = total_capex * cfg["PropertyTaxRate"]
        insurance    = total_capex * cfg["InsuranceRate"]
 
        # Management: fixed annual cost spread over system capacity
        management = cfg["Cost_OM_Management"] / batt_kwh
 
        res = {
            "new_bos":      new_bos,
            "new_inverters":new_inverters,
            "new_ess":      new_ess,
            "land_lease":   land_lease,
            "property_tax": property_tax,
            "insurance":    insurance,
            "management":   management,
        }
        res["total_om_per_kwh_yr"] = sum(res.values())
        return res

    # ------------------------------------------------------------------
    # Dynamic attribute resolution
    # Allows calling calculate_<subsystem>_per_kwh() to get the scalar
    # total for any subsystem without writing explicit wrapper methods.
    # ------------------------------------------------------------------

    def __getattr__(self, name):
        if name.startswith("calculate_") and name.endswith("_per_kwh"):
            target_getter = "get_" + name[10:-8] + "_breakdown"
            if hasattr(self, target_getter):
                breakdown = getattr(self, target_getter)()
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
            Values are in $/kWh-cap.
        """
        subsystems = {
            "li_ion":          self.get_li_ion_cost_breakdown,
            "inverter":        self.get_bi_directional_inverter_cost_breakdown,
            "sbos":            self.get_sbos_cost_breakdown,
            "ebos":            self.get_ebos_cost_breakdown,
            "installation":    self.get_installation_cost_breakdown,
            "permitting":      self.get_permitting_cost_breakdown,
            "interconnection": self.get_interconnection_cost_breakdown,
            "sales_tax":       self.get_sales_tax_cost_breakdown,
            "contingency":     self.get_contingency_cost_breakdown,
            "epc_overhead":    self.get_epc_overhead_cost_breakdown,
            "developer_profit":self.get_profit_cost_breakdown,
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
        """Return a CapexBreakdown with total cost in $/kWh-cap and full line items."""
        breakdown = self.get_cost_breakdown(higher_resolution=True)
        total = breakdown.pop("total_project_cost_per_kwh")
        return CapexBreakdown(total=total, unit="$/kWh-cap", line_items=breakdown)

    def run_opex(self) -> OpexBreakdown:
        """
        Return an OpexBreakdown with total annual O&M cost in $/kWdc-yr and
        full line items.
        """
        breakdown = self.get_om_cost_breakdown()
        annual_total = breakdown.pop("total_om_per_kwh_yr")
        return OpexBreakdown(annual_total=annual_total, unit="$/kWh-yr", line_items=breakdown)

    def run_design(self) -> DesignSummary:
        """
        Return key design parameters for this standalone BESS configuration.

        Includes battery capacity, storage duration, and bidirectional inverter
        capacity derived from BatteryCapacity and ESS_ILR.
        """
        cfg = self.config
        battery_capacity_mwdc = cfg["BatteryCapacity"]
        batt_dur = cfg["BatteryDuration"]
        batt_inv_mwac = battery_capacity_mwdc / cfg["ESS_ILR"]

        return DesignSummary(line_items={
            "battery_capacity_mwdc":          battery_capacity_mwdc,
            "storage_duration_h":             batt_dur,
            "battery_inverter_capacity_mwac": batt_inv_mwac,
        })