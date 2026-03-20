# genstorbosse/pvscm_nrel_solar+bess_model.py
import copy
import pandas as pd
from pathlib import Path
import yaml

DEFAULTS = {
    # 0. System Parameters
    "SystemSize": 100_000,           # kWdc (solar pv module)
    "ILR": 1.32,                     # kWdc modules/kWac inverter
    "IncludeESS": True,              # TOGGLE: True=1 (solar + bat), False=0 (solar)
    "StorageDuration": 2.4,          # kWh-cap/kWdc modules
    "GeneralDuty": 0.034,            # $ duties/$ cost
    "Tariff201": 0.1425,             # $ tariff/$ cost
    "Tariff301": 0.25,               # $ tariff/$ cost
    "Tariff301high": 0.5,            # $ tariff/$ cost

    # 1. Module Parameters
    "ModuleEfficiency": 0.206,       # kWdc modules/m2 modules
    "ModuleHeight": 2.27,            # m
    "ModuleWidth": 1.13,             # m
    "ModuleWeight": 11.5,            # kg modules/m2 modules
    "CellToModule": 0.98,            # kWdc modules/kWdc cells
    "ModuleLabor": 0.109,            # hour/m2 modules
    "ModuleElectricity": 5.79,       # kWh consumed/m2 modules
    "ModuleDepreciation": 0.118,     # $/yr/$ invested
    "ModuleProfitMSP": 0.15,         # $ profit/$ invested
    "ModuleMarketPrice": 336,        # $/kWdc

    # -- 1.0 Annual Production (kWdc) --
    "ModuleAnnualProduction": 1_500_000, # $ Fixed Cost per Year
    
    # -- 1.1 Fixed Costs ($/Unit) --
    "ModuleLaborFixed": 700_000,     # $ Fixed Cost per Year
    
    # -- 1.2 Cost per Intrinsic Unit ($/Unit) --
    "Cost_Cells": 130.00,            # $/kWdc
    "Cost_Frame": 1.50,              # $/m
    "Cost_Sheets": 7.70,             # $/m2
    "Cost_OtherMat": 6.30,           # $/module
    "Cost_Labor": 3.00,              # $/hour
    "Cost_Electricity": 0.06,        # $/kWh
    "Cost_Depreciation": 45.00,      # $/kWdc/yr
    "Cost_Maintenance": 1.80,        # $/kWdc
    "Cost_Shipping": 0.60,           # $/kg

    # 2. Inverter Parameters
    "InverterWeight": 0.935,         # kg inverter/kWac inverter
    "InverterLabor": 0.045,          # hours labor/kWac inverter
    "InverterElectricity": 8.42,     # kWh consumed/kWac inverter
    "InverterDepreciation": 0.118,   # $/yr/$ invested
    "InverterProfitMSP": 0.25,       # $ profit/$ invested
    "InverterMarketPrice": 44,       # $/kWac

    # -- 2.0 Annual Production (kWdc) --
    "InverterAnnualProduction": 1_000_000, # $ Fixed Cost per Year
    
    # -- 2.1 Inverter Fixed Costs ($/Unit) --
    "InverterLaborFixed": 5_800_000, # $ Fixed Cost per Year

    # -- 2.2 Inverter Cost per Intrinsic Unit ($/Unit) --
    "Cost_Inv_PCBA": 14.00,          # $/kWac
    "Cost_Inv_ElecParts": 5.00,      # $/kWac
    "Cost_Inv_ClimateControl": 3.00,        # $/kWac
    "Cost_Inv_Enclosure": 4.00,      # $/kWac
    "Cost_Inv_Labor": 39.00,         # $/hour
    "Cost_Inv_Electricity": 0.10,    # $/kWh
    "Cost_Inv_Depreciation": 10.00,  # $/kWac/yr
    "Cost_Inv_Maintenance": 0.40,    # $/kWac
    "Cost_Inv_Shipping": 1.50,       # $/kg

    # 3. ESS (Energy Storage System)
    "Battery45X": 10,                # $ credit/kWh-cap
    "45XPassthrough": 0.5,           # %/100 share
    "BatteryDuration": 4,            # kWh-cap/kWdc battery
    "ESS_ILR": 1,                    # kWac ESS/kWdc battery
    "ESSWeight": 9.4,                # kg ESS/kWh-cap
    "ESSLabor": 0.22,                # hours labor/kWh-cap
    "ESSElectricity": 30.5,          # kWh consumed/kWh-cap
    "ESSDepreciation": 0.11,         # $/yr/$ invested
    "ESSProfitMSP": 0.25,            # $ profit/$ invested
    "ESSMarketPrice": 228,           # $/kWh-cap

    # -- 3.0 Annual Production (kWdc) --
    "ESSAnnualProduction": 1_000_000, # $ Fixed Cost per Year
    
    # -- 3.1 ESS Fixed Costs ($/Unit) --
    "ESSLaborFixed": 2_500_000,      # $ Fixed Cost per Year

    # -- 3.2 ESS Cost per Intrinsic Unit ($/Unit) --
    "Cost_ESS_LiIonCells": 75.00,    # $/kWh-cap
    "Cost_ESS_BatteryPacks": 25.00,  # $/kWh-cap
    "Cost_ESS_Enclosure": 20.00,     # $/kWh-cap
    "Cost_ESS_ACDC_Conv": 100.00,    # $/kWac
    "Cost_ESS_Labor": 34.00,         # $/hour
    "Cost_ESS_Electricity": 0.08,    # $/kWh
    "Cost_ESS_Depreciation": 7.00,   # $/kWh-cap/yr
    "Cost_ESS_Maintenance": 0.28,    # $/kWh-cap
    "Cost_ESS_Shipping": 1.00,       # $/kg

    # 4. SBOS (Structural Balance of System)
    "Fastener45X": 2.28,             # $/kg fasteners
    "TorqueTube45X": 0.87,           # $/kg tubes
    "FastenerWeight": 0.2,           # kg/m2 modules
    "TorqueTubeWeight": 4.8,         # kg/m2 modules
    "SBOSshippingWeight": 10,        # kg/m2 modules
    "PiersPerRow": 11,               # piers/row
    "RowLength": 86.3,               # m

    # -- 4.1 SBOS Cost per Intrinsic Unit ($/Unit) --
    "Cost_SBOS_TorqueTubes": 2.70,   # $/kg
    "Cost_SBOS_Piers": 100.00,       # $/pier
    "Cost_SBOS_Rails": 1.80,         # $/m
    "Cost_SBOS_Fasteners": 3.30,     # $/kg
    "Cost_SBOS_SlewDrive": 300.00,   # $/row
    "Cost_SBOS_Dampers": 6.40,       # $/pier
    "Cost_SBOS_Motor": 440.00,       # $/row
    "Cost_SBOS_Electronics": 110.00, # $/row
    "Cost_SBOS_Shipping": 0.40,      # $/kg
    "Cost_SBOS_ESSPad": 4.00,        # $/kWh-cap             
    
    # 5. EBOS (Electrical Balance of System)
    "EBOSweight": 2,                 # kg EBOS/kWac inverter
    # -- 5.1 EBOS Fixed Costs ($/Unit) --
    "TransmissionFixed": 679_747,    # $ Fixed Cost per System

    # -- 5.2 EBOS Cost per Intrinsic Unit ($/Unit) --
    "Cost_EBOS_Transformers": 40.00, # $/kWac
    "Cost_EBOS_Switches": 6.50,      # $/kWac
    "Cost_EBOS_Breakers": 15.00,     # $/kWac
    "Cost_EBOS_Conductors": 21.00,   # $/kWac
    "Cost_EBOS_Combiners": 9.60,     # $/kWac
    "Cost_EBOS_Grounding": 9.50,     # $/kWac
    "Cost_EBOS_Substation": 33.00,   # $/kWac
    "Cost_EBOS_Transmission": 17.00, # $/kWac
    "Cost_EBOS_NetwUpgrade": 66.00,  # $/kWac
    "Cost_EBOS_Shipping": 1.20,      # $/kg

    # 6. Fieldwork
    "PVElectricalLabor": 0.25,       # hours labor/m2 modules
    "PVConstructionLabor": 0.4,      # hours labor/m2 modules
    "ESSInstallLabor": 2.15,         # hours labor/kWh-cap
    "LaborBurdenRate": 0.54,         # $ burden/$ labor
    # -- 6.1 Fieldwork Cost per Intrinsic Unit ($/Unit) --
    "Cost_Field_EBOSLabor": 33.00,   # $/hour
    "Cost_Field_SBOSLabor": 24.00,   # $/hour
    "Cost_Field_ESSLabor": 27.50,    # $/hour
    "Cost_Field_SitePrep": 8.00,     # $/m2
    "Cost_Field_EqpmtRental": 10.00, # $/m2
    "Cost_Field_Inspection": 1.60,   # $/m2
    
    # 7. Officework
    #-- 7.1 Officework Fixed Costs ($/Unit) --
    "Office_EngineeringFixed": 50_000, # $ Fixed Cost per System
    "Office_PermitsFixed": 200_000,    # $ Fixed Cost per System
    "Office_InterconnectFixed": 85_000, # $ Fixed Cost per System
    "Office_OutreachFixed": 200_000,   # $ Fixed Cost per System

    # -- 7.2 Officework Cost per Intrinsic Unit ($/Unit) --
    "Cost_Office_Warehousing": 1.10,   # $/m2
    "Cost_Office_Logistics": 0.10,     # $/kg
    "Cost_Office_Engineering": 3.00,   # $/m2
    "Cost_Office_Permits": 0.00,       # $/kWac
    "Cost_Office_Interconnect": 35.00, # $/kWac
    "Cost_Office_Outreach": 1.00,      # $/m2
    

    # 8. Other
    "SalesTaxRate": 0.058,           # $ tax/$ cost
    "ContingencyRate": 0.025,        # $ reserved/$ cost
    "OverheadRate": 0.01,            # $ overhead/$ cost
    "DeveloperProfit": 0.05,         # $ profit/$ cost
    # -- 8.0 Annual Installations (kWdc) --
    "AnnualInstallations": 200_000,  # kWdc
    
    # -- 8.1 Other Fixed Costs ($/Unit) --
    "ManagementFixed": 1_000_000,    # $ Fixed Cost per Year

    # 9. O&M (Operations & Maintenance)
    "PartsLossRate": 0.002,          # fraction/year
    "InverterLossRate": 0.09,        # fraction/year
    "ModuleLossRate": 0.001,         # fraction/year
    "ESSLossRate": 0.025,            # fraction/year
    "LandArea": 3000,                # m2 modules/ha land
    "PropertyTaxRate": 0.002,        # $ tax/year/$ cost
    "InsuranceRate": 0.0025,         # $ premium/year/$ cost
}

class SolBatBOSSEModel:
    def __init__(self, user_config: dict = None):
        # Ensures we start with DEFAULTS and override with user_config if it's a dict
        if user_config and not isinstance(user_config, dict):
            raise ValueError("user_config must be a dictionary.")
    
        self.config = {**DEFAULTS, **(user_config or {})}
    
        # Pre-calculate common factors
        cfg = self.config
        self.dur_ilr = cfg["BatteryDuration"] * cfg["ESS_ILR"]

    @classmethod
    def from_config_file(cls, file_name: str):
        from pathlib import Path
        import json

        # 1. Starting point: where model.py lives
        base_dir = Path(__file__).parent.absolute()
        
        # 2. Define potential locations to search
        search_paths = [
            base_dir / file_name,                        # Same folder as model.py
            base_dir / "configs" / file_name,             # In a subfolder called configs
            base_dir.parent.parent / "configs" / file_name # In the parallel configs folder
        ]

        full_path = None
        for p in search_paths:
            if p.exists():
                full_path = p
                break
        
        # 3. Final fallback: try the literal string provided
        if not full_path:
            full_path = Path(file_name)

        if not full_path.exists():
            # Provide a very clear error message showing where we looked
            tried = "\n".join([str(p) for p in search_paths])
            raise FileNotFoundError(f"Could not find {file_name}. Checked:\n{tried}")

        # ... (rest of your loading logic for JSON/YAML)

        with open(full_path, 'r') as f:
            if full_path.suffix == '.json':
                import json
                data = json.load(f)
            elif full_path.suffix in ['.yaml', '.yml']:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required for .yaml files. Install with 'pip install pyyaml'")
            else:
                raise ValueError(f"Extension {full_path.suffix} not supported. Use .json or .yaml")
    
        return cls(user_config=data)

    @property    
    def get_pv_module_cost_breakdown(self):
        cfg = self.config
        # Helper scaling: modules per kWdc
        mods_per_kw = 1 / (cfg["ModuleWidth"] * cfg["ModuleHeight"] * cfg["ModuleEfficiency"])
        
        # 1. Direct Materials & Tariffs
        cells = cfg["Cost_Cells"] * (1 / cfg["CellToModule"])
        frame = cfg["Cost_Frame"] * (2 * (cfg["ModuleWidth"] + cfg["ModuleHeight"])) * mods_per_kw
        sheets = cfg["Cost_Sheets"] * (1 / cfg["ModuleEfficiency"])
        other = cfg["Cost_OtherMat"] * mods_per_kw
        
        # 2. Manufacturing & OpEx
        # Assuming intensities: ModuleLabor (hr/m2), ModuleElectricity (kWh/m2)
        ann_prod = cfg.get("ModuleAnnualProduction", 1_000_000)
        labor = (cfg["ModuleLaborFixed"] / ann_prod) + (cfg["Cost_Labor"] * (cfg.get("ModuleLabor", 0.1) / cfg["ModuleEfficiency"]))
        elec = cfg["Cost_Electricity"] * (cfg.get("ModuleElectricity", 15.0) / cfg["ModuleEfficiency"])
        depr = cfg["Cost_Depreciation"] * cfg.get("ModuleDepreciation", 1.0)
        maint = cfg["Cost_Maintenance"]
        ship = cfg["Cost_Shipping"] * (cfg["ModuleWeight"] / cfg["ModuleEfficiency"])
        
        # 3. Profit Calculation
        mfg_sum = cells + frame + sheets + other + labor + elec + depr + maint + ship
        profit = cfg["ModuleMarketPrice"] - mfg_sum
        
        res = {
            "cells": cells,
            "frame": frame,
            "sheets": sheets,
            "other_material": other,
            "labor": labor,
            "electricity": elec,
            "depreciation": depr,
            "maintenance": maint,
            "shipping": ship,
            "profit": profit
        }
        res["total_pv_module_per_kwdc"] = sum(res.values())
        return res

    def get_three_phase_inverter_cost_breakdown(self):
        cfg = self.config
        # Scaling helper: kWdc basis
        ilr = cfg["ILR"]
        # Note: All Cost_Inv_X units are already in $/kWac per your defaults
        
        # 1. Direct Materials
        pcba = cfg["Cost_Inv_PCBA"]
        elec_parts = cfg["Cost_Inv_ElecParts"]
        climate = cfg["Cost_Inv_ClimateControl"]
        enclosure = cfg["Cost_Inv_Enclosure"]
        
        # 2. Manufacturing & OpEx
        # Intensity factors: InverterLabor (hr/kWac), InverterElectricity (kWh/kWac)
        ann_prod = cfg.get("InverterAnnualProduction", 500_000) # kWac/yr
        labor = (cfg["InverterLaborFixed"] / ann_prod) + (cfg["Cost_Inv_Labor"] * cfg["InverterLabor"])
        elec = cfg["Cost_Inv_Electricity"] * cfg["InverterElectricity"]
        
        # 3. Logistics & Maintenance
        ship = cfg["Cost_Inv_Shipping"] * cfg["InverterWeight"]
        depr = cfg["Cost_Inv_Depreciation"] * cfg["InverterDepreciation"]
        maint = cfg["Cost_Inv_Maintenance"]
        
        # 4. Profit Calculation (Residual)
        # MarketPrice - (Materials + Labor + Elec + Shipping + Depr + Maint)
        mfg_sum = pcba + elec_parts + climate + enclosure + labor + elec + ship + depr + maint
        profit = cfg["InverterMarketPrice"] - mfg_sum
        
        res = {
            "pcb_assemblies": pcba / ilr,
            "electrical_parts": elec_parts / ilr,
            "climate_control": climate / ilr,
            "enclosure": enclosure / ilr,
            "labor": labor / ilr,
            "electricity": elec / ilr,
            "shipping": ship / ilr,
            "depreciation": depr / ilr,
            "maintenance": maint / ilr,
            "profit": profit / ilr
        }
        res["total_three_phase_inverter_per_kwdc"] = sum(res.values())
        return res

    def get_li_ion_cost_breakdown(self):
        cfg = self.config
        # Scaling factor: kWh-cap per kWdc of solar
        dur = cfg["StorageDuration"]
        
        # 1. Base Components (scaled by duration to $/kWdc)
        cells = (cfg["Cost_ESS_LiIonCells"] * (1 + cfg.get("GeneralDuty", 0.034) + cfg["Tariff301"])) * dur
        labor = ((cfg["ESSLaborFixed"] / cfg.get("ESSAnnualProduction", 1_000_000)) + 
                 (cfg["Cost_ESS_Labor"] * cfg["ESSLabor"])) * dur
        elec = (cfg["Cost_ESS_Electricity"] * cfg["ESSElectricity"]) * dur
        depr = (cfg["Cost_ESS_Depreciation"] * cfg["ESSDepreciation"]) * dur
        ship = (cfg["Cost_ESS_Shipping"] * cfg["ESSWeight"]) * dur
        
        # 2. Profit Base (The sum of all manufacturing costs per kWdc)
        # Includes the inverter normalized by duration/ilr and the 45X credit
        conv_val = (cfg["Cost_ESS_ACDC_Conv"] / self.dur_ilr) * dur
        p_base = (cells + 
                  (cfg["Cost_ESS_BatteryPacks"] * dur) + 
                  (cfg["Cost_ESS_Enclosure"] * dur) + 
                  conv_val + labor + elec + depr + 
                  (cfg["Cost_ESS_Maintenance"] * dur) - 
                  (cfg.get("45XPassthrough", 0.5) * cfg["Battery45X"] * dur) + 
                  ship)
        
        res = {
            "li_ion_cells": cells, 
            "battery_packs": cfg["Cost_ESS_BatteryPacks"] * dur, 
            "enclosure": cfg["Cost_ESS_Enclosure"] * dur,
            "labor": labor, 
            "electricity": elec, 
            "depreciation": depr, 
            "maintenance": cfg["Cost_ESS_Maintenance"] * dur,
            "profit": (cfg["ESSMarketPrice"] * dur) - p_base, 
            "shipping": ship,
            "passthrough_credit": -cfg["45XPassthrough"] * cfg["Battery45X"] * dur
        }
        res["total_li_ion_cost_per_kwdc"] = sum(res.values())
        return res

    def get_bi_directional_inverter_cost_breakdown(self):
        # Normalizing the AC/DC Converter to the solar kWdc basis
        val = (self.config["Cost_ESS_ACDC_Conv"] / self.dur_ilr) * self.config["StorageDuration"]
        return {"bi_directional_inverter": val, "total_bi_directional_inverter_per_kwdc": val}

    def get_sbos_cost_breakdown(self):
        cfg = self.config
        # Scaling helper: Multiplier to go from $/m2 to $/kWdc
        inv_eff = 1 / cfg["ModuleEfficiency"]
        # Area of a single row
        row_area = cfg["RowLength"] * cfg["ModuleHeight"]
        # Tariff multiplier (e.g., 1.25)
        t301 = 1 + cfg["Tariff301"]
        
        # 1. Torque Tubes (Net of 45X Credit)
        # Logic: (Cost - Credit_Share) * Weight * Area_Factor
        tube_net_cost = cfg["Cost_SBOS_TorqueTubes"] - (cfg["45XPassthrough"] * cfg["TorqueTube45X"])
        tubes = tube_net_cost * cfg["TorqueTubeWeight"] * inv_eff
        
        # 2. Driven Piers (No tariff/credit specified in your update)
        piers_per_m2 = cfg["PiersPerRow"] / row_area
        piers = cfg["Cost_SBOS_Piers"] * piers_per_m2 * inv_eff
        
        # 3. Components subject to Tariff 301
        rails = (cfg["Cost_SBOS_Rails"] * (1 / cfg["ModuleWidth"]) * inv_eff) * t301
        fasteners_net_cost = cfg["Cost_SBOS_Fasteners"] - (cfg["45XPassthrough"] * cfg["Fastener45X"])
        fasteners = fasteners_net_cost * cfg["FastenerWeight"] * inv_eff
        
        # Row-based components subject to Tariff 301
        row_unit_m2 = 1 / row_area
        slew = (cfg["Cost_SBOS_SlewDrive"] * row_unit_m2 * inv_eff) * t301
        dampers = (cfg["Cost_SBOS_Dampers"] * piers_per_m2 * inv_eff) * t301
        motor = (cfg["Cost_SBOS_Motor"] * row_unit_m2 * inv_eff) * t301
        electronics = (cfg["Cost_SBOS_Electronics"] * row_unit_m2 * inv_eff) * t301
        
        # 4. Logistics & ESS Specifics
        ship = cfg["Cost_SBOS_Shipping"] * cfg["SBOSshippingWeight"] * inv_eff
        ess_pad = cfg["Cost_SBOS_ESSPad"] * cfg["StorageDuration"]
        
        res = {
            "torque_tubes": tubes,
            "driven_piers": piers,
            "module_rails": rails,
            "fasteners": fasteners,
            "slew_drive": slew,
            "dampers": dampers,
            "motor": motor,
            "control_electronics": electronics,
            "shipping": ship,
            "ess_pad": ess_pad
        }
        res["total_sbos_per_kwdc"] = sum(res.values())
        return res
        

    def get_ebos_cost_breakdown(self):
        cfg = self.config
        # Scaling helper: Normalize from kWac to kWdc
        ilr = cfg["ILR"]
        # Tariff multiplier (e.g., 1.25)
        t301 = 1 + cfg["Tariff301"]
        
        # 1. Primary Electrical Equipment
        trans = cfg["Cost_EBOS_Transformers"] / ilr
        # Applied Tariff 301 to Switches and Breakers
        switches = (cfg["Cost_EBOS_Switches"] / ilr) * t301
        breakers = (cfg["Cost_EBOS_Breakers"] / ilr) * t301
        
        # 2. Collection System & DC Balance
        cond = cfg["Cost_EBOS_Conductors"] / ilr
        # Applied Tariff 301 to Combiner Boxes
        comb = (cfg["Cost_EBOS_Combiners"] / ilr) * t301
        ground = cfg["Cost_EBOS_Grounding"] / ilr
        
        # 3. Grid Interconnection & Infrastructure
        # Applied Tariff 301 to Substation
        sub = (cfg["Cost_EBOS_Substation"] / ilr) * t301
        
        # Transmission includes the Fixed Cost distribution + Variable
        # Fixed / (System MWdc * 1000) converts total $ to $/kWdc
        trans_fixed_val = cfg["TransmissionFixed"] / (cfg["SystemSize"]/ilr)
        transmission = (trans_fixed_val + cfg["Cost_EBOS_Transmission"]) / ilr
        
        net_up = cfg["Cost_EBOS_NetwUpgrade"] / ilr
        
        # 4. Logistics
        ship = (cfg["Cost_EBOS_Shipping"] * cfg["EBOSweight"]) / ilr
        
        res = {
            "transformers": trans,
            "switches": switches,
            "breakers": breakers,
            "conductors": cond,
            "combiner_boxes": comb,
            "grounding": ground,
            "substation": sub,
            "transmission": transmission,
            "network_upgrade": net_up,
            "shipping": ship
        }
        res["total_ebos_per_kwdc"] = sum(res.values())
        return res


    def get_fieldwork_cost_breakdown(self):
        cfg = self.config
        # Scaling helper: $/m2 to $/kWdc
        inv_eff = 1 / cfg["ModuleEfficiency"]
        # Labor burden multiplier (e.g., 1.54)
        burden = 1 + cfg["LaborBurdenRate"]
        
        # 1. Electrical & Structural Labor
        # Logic: Hourly Rate * (Hours/m2 * Burden) * m2/kWdc
        ebos_labor = cfg["Cost_Field_EBOSLabor"] * (cfg["PVElectricalLabor"] * burden) * inv_eff
        sbos_labor = cfg["Cost_Field_SBOSLabor"] * (cfg["PVConstructionLabor"] * burden) * inv_eff
        
        # 2. ESS Installation Labor
        # Logic: $/hr * (hr/kWh * kWh/kWdc * Burden)
        # Note: ModuleEfficiency cancels out in your provided equation
        ess_labor = cfg["Cost_Field_ESSLabor"] * (cfg["ESSInstallLabor"] * cfg["StorageDuration"] * burden)
        
        # 3. Civil & Indirect Field Costs
        # Logic: $/m2 * m2/kWdc
        site_prep = cfg["Cost_Field_SitePrep"] * inv_eff
        eq_rental = cfg["Cost_Field_EqpmtRental"] * inv_eff
        inspection = cfg["Cost_Field_Inspection"] * inv_eff
        
        res = {
            "ebos_labor": ebos_labor,
            "sbos_labor": sbos_labor,
            "ess_labor": ess_labor,
            "site_prep": site_prep,
            "equipment_rental": eq_rental,
            "inspection": inspection
        }
        res["total_fieldwork_per_kwdc"] = sum(res.values())
        return res


    def get_officework_cost_breakdown(self):
        cfg = self.config
        # Scaling helpers
        inv_eff = 1 / cfg["ModuleEfficiency"]
        ilr = cfg["ILR"]
        sys_size = cfg["SystemSize"]  # Total kWdc of the plant
        
        # 1. Logistics & Storage (Area/Weight based)
        warehousing = cfg["Cost_Office_Warehousing"] * inv_eff
        logistics = cfg["Cost_Office_Logistics"] * (cfg["ModuleWeight"] * inv_eff)
        
        # 2. Engineering (Fixed + Area Variable)
        eng_fixed = cfg["Office_EngineeringFixed"] / sys_size
        engineering = eng_fixed + (cfg["Cost_Office_Engineering"] * inv_eff)
        
        # 3. Regulatory & Grid (Fixed + AC-Power Variable)
        # Note: Permitting and Interconnect usually scale with the Inverter (AC) rating
        perm_fixed = cfg["Office_PermitsFixed"] / sys_size
        permits = perm_fixed + (cfg.get("Cost_Office_Permits", 0.0) / ilr)
        
        int_fixed = cfg["Office_InterconnectFixed"] / sys_size
        interconnect = int_fixed + (cfg["Cost_Office_Interconnect"] / ilr)
        
        # 4. Community Outreach (Fixed + Area Variable)
        out_fixed = cfg["Office_OutreachFixed"] / sys_size
        outreach = out_fixed + (cfg["Cost_Office_Outreach"] * inv_eff)
        
        res = {
            "warehousing": warehousing,
            "logistics": logistics,
            "engineering": engineering,
            "permits": permits,
            "interconnect": interconnect,
            "outreach": outreach
        }
        res["total_officework_per_kwdc"] = sum(res.values())
        return res

    def get_other_cost_breakdown(self):
        cfg = self.config
        
        # 1. Pull Sub-breakdowns for aggregation
        pv_mod = self.get_pv_module_cost_breakdown()["total_pv_module_per_kwdc"]
        inv_3ph = self.get_three_phase_inverter_cost_breakdown()["total_three_phase_inverter_per_kwdc"]
        ess_bat = self.get_li_ion_cost_breakdown()["total_li_ion_cost_per_kwdc"]
        ess_conv = self.get_bi_directional_inverter_cost_breakdown()["total_bi_directional_inverter_per_kwdc"]
        sbos = self.get_sbos_cost_breakdown()["total_sbos_per_kwdc"]
        ebos = self.get_ebos_cost_breakdown()["total_ebos_per_kwdc"]
        
        field = self.get_fieldwork_cost_breakdown()["total_fieldwork_per_kwdc"]
        office = self.get_officework_cost_breakdown()["total_officework_per_kwdc"]

        # 2. Define Logical Sums
        # Hardware Sum (Taxable base)
        hardware_sum = pv_mod + inv_3ph + ess_bat + ess_conv + sbos + ebos
        # Total Direct Cost (Hardware + Labor + Development)
        direct_cost_sum = hardware_sum + field + office

        # 3. Calculate "Other" Factors
        sales_tax = cfg["SalesTaxRate"] * hardware_sum
        contingency = cfg["ContingencyRate"] * direct_cost_sum
        
        # Management: Fixed spread across annual volume + Variable overhead
        ann_vol = cfg["AnnualInstallations"]
        mgt_fixed = cfg["ManagementFixed"] / ann_vol
        management = mgt_fixed + (cfg["OverheadRate"] * direct_cost_sum)

        # 4. Developer Profit
        # Applied to the "All-in" cost including tax and contingency
        subtotal_before_profit = direct_cost_sum + sales_tax + contingency + management
        profit = cfg.get("DeveloperProfit", 0.05) * subtotal_before_profit

        res = {
            "sales_tax": sales_tax,
            "contingency": contingency,
            "management": management,
            "developer_profit": profit
        }
        res["total_other_per_kwdc"] = sum(res.values())
        return res

    # Logic to generate all calculate_X methods dynamically to save 50+ lines of code
    def __getattr__(self, name):
        if name.startswith("calculate_") and name.endswith("_per_kwh"):
            target_getter = "get_" + name[10:-8] + "_breakdown"
            if hasattr(self, target_getter):
                breakdown = getattr(self, target_getter)()
                return lambda: breakdown[next(k for k in breakdown if k.startswith("total_"))]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_cost_breakdown(self, higher_resolution=False):
        subsystems = {
            "pv_module": self.get_pv_module_cost_breakdown, "three_phase_inverter": self.get_three_phase_inverter_cost_breakdown,
            "li_ion": self.get_li_ion_cost_breakdown, "bi_directional_inverter": self.get_bi_directional_inverter_cost_breakdown,
            "sbos": self.get_sbos_cost_breakdown, "ebos": self.get_ebos_cost_breakdown,
            "fieldwork": self.get_fieldwork_cost_breakdown, "officework": self.get_officework_cost_breakdown,
            "other": self.get_other_cost_breakdown
        }
        output, total = {}, 0.0
        for name, func in subsystems.items():
            sub = func()
            val = sub[next(k for k in sub if k.startswith("total_"))]
            total += val
            output[name] = {"total": val, "components": {k: v for k, v in sub.items() if not k.startswith("total_")}} if higher_resolution else val
        output["total_project_cost_per_kwh"] = total
        return output