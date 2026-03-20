# genstorbosse/pvscm_nrel_solar+bess_model.py
import copy
import pandas as pd
from pathlib import Path
import yaml

DEFAULTS = {
    # 0. System Parameters
    "SystemSize": 100_000,           # kWdc (solar pv module)
    "ILR": 1.32,                     # kWdc modules/kWac inverter
    "StorageDuration": 2.4,          # kWh-cap/kWdc modules
    "IncludeESS": True,              # Toggle for Storage Costs
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
    "ModuleAnnualProduction": 1_500_000, 
    "ModuleLaborFixed": 700_000,     
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
    "InverterAnnualProduction": 1_000_000, 
    "InverterLaborFixed": 5_800_000, 
    "Cost_Inv_PCBA": 14.00,          # $/kWac
    "Cost_Inv_ElecParts": 5.00,      # $/kWac
    "Cost_Inv_ClimateControl": 3.00, # $/kWac
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
    "ESSAnnualProduction": 1_000_000, 
    "ESSLaborFixed": 2_500_000,      
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
    "Fastener45X": 2.28,             
    "TorqueTube45X": 0.87,           
    "FastenerWeight": 0.2,           
    "TorqueTubeWeight": 4.8,         
    "SBOSshippingWeight": 10,        
    "PiersPerRow": 11,               
    "RowLength": 86.3,               
    "Cost_SBOS_TorqueTubes": 2.70,   
    "Cost_SBOS_Piers": 100.00,       
    "Cost_SBOS_Rails": 1.80,         
    "Cost_SBOS_Fasteners": 3.30,     
    "Cost_SBOS_SlewDrive": 300.00,   
    "Cost_SBOS_Dampers": 6.40,       
    "Cost_SBOS_Motor": 440.00,       
    "Cost_SBOS_Electronics": 110.00, 
    "Cost_SBOS_Shipping": 0.40,      
    "Cost_SBOS_ESSPad": 4.00,        

    # 5. EBOS (Electrical Balance of System)
    "EBOSweight": 2,                 
    "TransmissionFixed": 679_747,    
    "Cost_EBOS_Transformers": 40.00, 
    "Cost_EBOS_Switches": 6.50,      
    "Cost_EBOS_Breakers": 15.00,     
    "Cost_EBOS_Conductors": 21.00,   
    "Cost_EBOS_Combiners": 9.60,     
    "Cost_EBOS_Grounding": 9.50,     
    "Cost_EBOS_Substation": 33.00,   
    "Cost_EBOS_Transmission": 17.00, 
    "Cost_EBOS_NetwUpgrade": 66.00,  
    "Cost_EBOS_Shipping": 1.20,      

    # 6. Fieldwork
    "PVElectricalLabor": 0.25,       
    "PVConstructionLabor": 0.4,      
    "ESSInstallLabor": 2.15,         
    "LaborBurdenRate": 0.54,         
    "Cost_Field_EBOSLabor": 33.00,   
    "Cost_Field_SBOSLabor": 24.00,   
    "Cost_Field_ESSLabor": 27.50,    
    "Cost_Field_SitePrep": 8.00,     
    "Cost_Field_EqpmtRental": 10.00, 
    "Cost_Field_Inspection": 1.60,   
    
    # 7. Officework
    "Office_EngineeringFixed": 50_000, 
    "Office_PermitsFixed": 200_000,    
    "Office_InterconnectFixed": 85_000, 
    "Office_OutreachFixed": 200_000,   
    "Cost_Office_Warehousing": 1.10,   
    "Cost_Office_Logistics": 0.10,     
    "Cost_Office_Engineering": 3.00,   
    "Cost_Office_Permits": 0.00,       
    "Cost_Office_Interconnect": 35.00, 
    "Cost_Office_Outreach": 1.00,      

    # 8. Other
    "SalesTaxRate": 0.058,           
    "ContingencyRate": 0.025,        
    "OverheadRate": 0.01,            
    "DeveloperProfit": 0.05,         
    "AnnualInstallations": 200_000,  
    "ManagementFixed": 1_000_000,    

    # 9. O&M
    "PartsLossRate": 0.002,          
    "InverterLossRate": 0.09,        
    "ModuleLossRate": 0.001,         
    "ESSLossRate": 0.025,            
    "LandArea": 3000,                
    "PropertyTaxRate": 0.002,        
    "InsuranceRate": 0.0025          
}

class SolBatBOSSEModel:
    def __init__(self, user_config: dict = None):
        if user_config and not isinstance(user_config, dict):
            raise ValueError("user_config must be a dictionary.")
        self.config = {**DEFAULTS, **(user_config or {})}
        
        cfg = self.config
        # kWac ESS / kWdc Solar
        self.dur_ilr = cfg["BatteryDuration"] * cfg["ESS_ILR"]
        self.system_cap_kwdc = cfg["SystemSize"]


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

    def get_pv_module_cost_breakdown(self):
        cfg = self.config
        mods_per_kw = 1 / (cfg["ModuleWidth"] * cfg["ModuleHeight"] * cfg["ModuleEfficiency"])
        inv_eff = 1 / cfg["ModuleEfficiency"]
        
        cells = cfg["Cost_Cells"] * (1 / cfg["CellToModule"])
        frame = cfg["Cost_Frame"] * (2 * (cfg["ModuleWidth"] + cfg["ModuleHeight"])) * mods_per_kw
        sheets = cfg["Cost_Sheets"] * inv_eff
        other = cfg["Cost_OtherMat"] * mods_per_kw
        
        ann_prod = cfg.get("ModuleAnnualProduction", 1_500_000)
        labor = (cfg["ModuleLaborFixed"] / ann_prod) + (cfg["Cost_Labor"] * (cfg["ModuleLabor"] * inv_eff))
        elec = cfg["Cost_Electricity"] * (cfg["ModuleElectricity"] * inv_eff)
        depr = cfg["Cost_Depreciation"] * cfg["ModuleDepreciation"]
        ship = cfg["Cost_Shipping"] * (cfg["ModuleWeight"] * inv_eff)
        
        mfg_sum = cells + frame + sheets + other + labor + elec + depr + cfg["Cost_Maintenance"] + ship
        profit = cfg["ModuleMarketPrice"] - mfg_sum
        
        res = {
            "cells": cells, "frame": frame, "sheets": sheets, "other_material": other,
            "labor": labor, "electricity": elec, "depreciation": depr,
            "maintenance": cfg["Cost_Maintenance"], "shipping": ship, "profit": profit
        }
        res["total_pv_module_per_kwdc"] = sum(res.values())
        return res

    def get_three_phase_inverter_cost_breakdown(self):
        cfg = self.config
        ilr = cfg["ILR"]
        ann_prod = cfg.get("InverterAnnualProduction", 1_000_000)
        
        labor = (cfg["InverterLaborFixed"] / ann_prod) + (cfg["Cost_Inv_Labor"] * cfg["InverterLabor"])
        elec = cfg["Cost_Inv_Electricity"] * cfg["InverterElectricity"]
        ship = cfg["Cost_Inv_Shipping"] * cfg["InverterWeight"]
        depr = cfg["Cost_Inv_Depreciation"] * cfg["InverterDepreciation"]
        
        mfg_sum = cfg["Cost_Inv_PCBA"] + cfg["Cost_Inv_ElecParts"] + cfg["Cost_Inv_ClimateControl"] + \
                  cfg["Cost_Inv_Enclosure"] + labor + elec + ship + depr + cfg["Cost_Inv_Maintenance"]
        profit = cfg["InverterMarketPrice"] - mfg_sum
        
        res = {
            "pcb_assemblies": cfg["Cost_Inv_PCBA"] / ilr, "electrical_parts": cfg["Cost_Inv_ElecParts"] / ilr,
            "climate_control": cfg["Cost_Inv_ClimateControl"] / ilr, "enclosure": cfg["Cost_Inv_Enclosure"] / ilr,
            "labor": labor / ilr, "electricity": elec / ilr, "shipping": ship / ilr,
            "depreciation": depr / ilr, "maintenance": cfg["Cost_Inv_Maintenance"] / ilr, "profit": profit / ilr
        }
        res["total_three_phase_inverter_per_kwdc"] = sum(res.values())
        return res

    def get_li_ion_cost_breakdown(self):
        cfg = self.config
        ess_mult = int(cfg["IncludeESS"])
        dur = cfg["StorageDuration"]
        ann_prod = cfg.get("ESSAnnualProduction", 1_000_000)
        
        cells = (cfg["Cost_ESS_LiIonCells"] * (1 + cfg["GeneralDuty"] + cfg["Tariff301"])) * dur * ess_mult
        labor = ((cfg["ESSLaborFixed"] / ann_prod) + (cfg["Cost_ESS_Labor"] * cfg["ESSLabor"])) * dur * ess_mult
        elec = (cfg["Cost_ESS_Electricity"] * cfg["ESSElectricity"]) * dur * ess_mult
        depr = (cfg["Cost_ESS_Depreciation"] * cfg["ESSDepreciation"]) * dur * ess_mult
        ship = (cfg["Cost_ESS_Shipping"] * cfg["ESSWeight"]) * dur * ess_mult
        
        conv_val = (cfg["Cost_ESS_ACDC_Conv"] / self.dur_ilr) * dur
        p_base = cells + (cfg["Cost_ESS_BatteryPacks"] * dur * ess_mult) + \
                 (cfg["Cost_ESS_Enclosure"] * dur * ess_mult) + (conv_val * ess_mult) + \
                 labor + elec + depr + (cfg["Cost_ESS_Maintenance"] * dur * ess_mult) - \
                 (cfg["45XPassthrough"] * cfg["Battery45X"] * dur * ess_mult) + ship
        
        profit = ((cfg["ESSMarketPrice"] * dur) - p_base) if ess_mult else 0.0

        res = {
            "li_ion_cells": cells, "battery_packs": cfg["Cost_ESS_BatteryPacks"] * dur * ess_mult,
            "enclosure": cfg["Cost_ESS_Enclosure"] * dur * ess_mult, "labor": labor,
            "electricity": elec, "depreciation": depr, "maintenance": cfg["Cost_ESS_Maintenance"] * dur * ess_mult,
            "profit": profit, "shipping": ship, "passthrough_credit": -cfg["45XPassthrough"] * cfg["Battery45X"] * dur * ess_mult
        }
        res["total_li_ion_cost_per_kwdc"] = sum(res.values())
        return res

    def get_bi_directional_inverter_cost_breakdown(self):
        ess_mult = int(self.config["IncludeESS"])
        val = (self.config["Cost_ESS_ACDC_Conv"] / self.dur_ilr) * self.config["StorageDuration"] * ess_mult
        return {"bi_directional_inverter": val, "total_bi_directional_inverter_per_kwdc": val}

    def get_sbos_cost_breakdown(self):
        cfg = self.config
        inv_eff = 1 / cfg["ModuleEfficiency"]
        row_area = cfg["RowLength"] * cfg["ModuleHeight"]
        t301 = 1 + cfg["Tariff301"]
        ess_mult = int(cfg["IncludeESS"])
        
        tube_net = cfg["Cost_SBOS_TorqueTubes"] - (cfg["45XPassthrough"] * cfg["TorqueTube45X"])
        tubes = tube_net * cfg["TorqueTubeWeight"] * inv_eff
        
        piers_per_m2 = cfg["PiersPerRow"] / row_area
        piers = cfg["Cost_SBOS_Piers"] * piers_per_m2 * inv_eff

        fasteners_net_cost = cfg["Cost_SBOS_Fasteners"] - (cfg["45XPassthrough"] * cfg["Fastener45X"])
        fasteners = fasteners_net_cost * cfg["FastenerWeight"] * inv_eff
        
        row_unit_m2 = 1 / row_area
        res = {
            "torque_tubes": tubes, "driven_piers": piers,
            "module_rails": (cfg["Cost_SBOS_Rails"] * (1/cfg["ModuleWidth"]) * inv_eff) * t301,
            "fasteners": fasteners, "slew_drive": (cfg["Cost_SBOS_SlewDrive"] * row_unit_m2 * inv_eff) * t301,
            "dampers": (cfg["Cost_SBOS_Dampers"] * piers_per_m2 * inv_eff) * t301,
            "motor": (cfg["Cost_SBOS_Motor"] * row_unit_m2 * inv_eff) * t301,
            "control_electronics": (cfg["Cost_SBOS_Electronics"] * row_unit_m2 * inv_eff) * t301,
            "shipping": cfg["Cost_SBOS_Shipping"] * cfg["SBOSshippingWeight"] * inv_eff,
            "ess_pad": cfg["Cost_SBOS_ESSPad"] * cfg["StorageDuration"] * ess_mult
        }
        res["total_sbos_per_kwdc"] = sum(res.values())
        return res

    def get_ebos_cost_breakdown(self):
        cfg = self.config
        ilr, t301 = cfg["ILR"], 1 + cfg["Tariff301"]
        trans_fix = cfg["TransmissionFixed"] / (cfg["SystemSize"] / ilr)
        
        res = {
            "transformers": cfg["Cost_EBOS_Transformers"] / ilr,
            "switches": (cfg["Cost_EBOS_Switches"] / ilr) * t301,
            "breakers": (cfg["Cost_EBOS_Breakers"] / ilr) * t301,
            "conductors": cfg["Cost_EBOS_Conductors"] / ilr,
            "combiner_boxes": (cfg["Cost_EBOS_Combiners"] / ilr) * t301,
            "grounding": cfg["Cost_EBOS_Grounding"] / ilr,
            "substation": (cfg["Cost_EBOS_Substation"] / ilr) * t301,
            "transmission": (trans_fix + cfg["Cost_EBOS_Transmission"]) / ilr,
            "network_upgrade": cfg["Cost_EBOS_NetwUpgrade"] / ilr,
            "shipping": (cfg["Cost_EBOS_Shipping"] * cfg["EBOSweight"]) / ilr
        }
        res["total_ebos_per_kwdc"] = sum(res.values())
        return res

    def get_fieldwork_cost_breakdown(self):
        cfg = self.config
        inv_eff, burden, ess_mult = 1/cfg["ModuleEfficiency"], 1+cfg["LaborBurdenRate"], int(cfg["IncludeESS"])
        
        res = {
            "ebos_labor": cfg["Cost_Field_EBOSLabor"] * (cfg["PVElectricalLabor"] * burden) * inv_eff,
            "sbos_labor": cfg["Cost_Field_SBOSLabor"] * (cfg["PVConstructionLabor"] * burden) * inv_eff,
            "ess_labor": cfg["Cost_Field_ESSLabor"] * (cfg["ESSInstallLabor"] * cfg["StorageDuration"] * burden) * ess_mult,
            "site_prep": cfg["Cost_Field_SitePrep"] * inv_eff,
            "equipment_rental": cfg["Cost_Field_EqpmtRental"] * inv_eff,
            "inspection": cfg["Cost_Field_Inspection"] * inv_eff
        }
        res["total_fieldwork_per_kwdc"] = sum(res.values())
        return res

    def get_officework_cost_breakdown(self):
        cfg = self.config
        inv_eff, ilr, sys_size = 1/cfg["ModuleEfficiency"], cfg["ILR"], cfg["SystemSize"]
        
        res = {
            "warehousing": cfg["Cost_Office_Warehousing"] * inv_eff,
            "logistics": cfg["Cost_Office_Logistics"] * (cfg["ModuleWeight"] * inv_eff),
            "engineering": (cfg["Office_EngineeringFixed"] / sys_size) + (cfg["Cost_Office_Engineering"] * inv_eff),
            "permits": (cfg["Office_PermitsFixed"] / sys_size) + (cfg["Cost_Office_Permits"] / ilr),
            "interconnect": (cfg["Office_InterconnectFixed"] / sys_size) + (cfg["Cost_Office_Interconnect"] / ilr),
            "outreach": (cfg["Office_OutreachFixed"] / sys_size) + (cfg["Cost_Office_Outreach"] * inv_eff)
        }
        res["total_officework_per_kwdc"] = sum(res.values())
        return res

    def get_other_cost_breakdown(self):
        cfg = self.config
        hw = self.get_pv_module_cost_breakdown()["total_pv_module_per_kwdc"] + \
             self.get_three_phase_inverter_cost_breakdown()["total_three_phase_inverter_per_kwdc"] + \
             self.get_li_ion_cost_breakdown()["total_li_ion_cost_per_kwdc"] + \
             self.get_bi_directional_inverter_cost_breakdown()["total_bi_directional_inverter_per_kwdc"] + \
             self.get_sbos_cost_breakdown()["total_sbos_per_kwdc"] + \
             self.get_ebos_cost_breakdown()["total_ebos_per_kwdc"]
        
        direct = hw + self.get_fieldwork_cost_breakdown()["total_fieldwork_per_kwdc"] + \
                 self.get_officework_cost_breakdown()["total_officework_per_kwdc"]
        
        tax = cfg["SalesTaxRate"] * hw
        cont = cfg["ContingencyRate"] * direct
        mgt = (cfg["ManagementFixed"] / cfg["AnnualInstallations"]) + (cfg["OverheadRate"] * direct)
        
        subtotal = direct + tax + cont + mgt
        profit = cfg.get("DeveloperProfit", 0.05) * subtotal
        
        res = {"sales_tax": tax, "contingency": cont, "management": mgt, "developer_profit": profit}
        res["total_other_per_kwdc"] = sum(res.values())
        return res

    def __getattr__(self, name):
        if name.startswith("calculate_") and name.endswith("_per_kwh"):
            target = "get_" + name[10:-8] + "_breakdown"
            if hasattr(self, target):
                breakdown = getattr(self, target)()
                return lambda: breakdown[next(k for k in breakdown if k.startswith("total_"))]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_cost_breakdown(self, higher_resolution=False):
        subsystems = {
            "pv_module": self.get_pv_module_cost_breakdown, "three_phase_inverter": self.get_three_phase_inverter_cost_breakdown,
            "li_ion": self.get_li_ion_cost_breakdown, "bi_directional_inverter": self.get_bi_directional_inverter_cost_breakdown,
            "sbos": self.get_sbos_cost_breakdown, "ebos": self.get_ebos_cost_breakdown,
            "fieldwork": self.get_fieldwork_cost_breakdown, "officework": self.get_officework_cost_breakdown, "other": self.get_other_cost_breakdown
        }
        output, total = {}, 0.0
        for name, func in subsystems.items():
            sub = func()
            val = sub[next(k for k in sub if k.startswith("total_"))]
            total += val
            output[name] = {"total": val, "components": {k: v for k, v in sub.items() if not k.startswith("total_")}} if higher_resolution else val
        output["total_project_cost_per_kwh"] = total
        return output