from genstor.models.bess_2025 import BESS2025CostModel
from genstor.models.solar_bess_2024Q1 import SolarBESS2024Q1CostModel

REGISTRY: dict[str, type] = {
    "bess_2025":       BESS2025CostModel,
    "solar_bess_2024Q1": SolarBESS2024Q1CostModel,
    # Future techs — uncomment as models are added:
    # "zinc_batteries":  ZincBESSCostModel,
    # "pumped_hydro_storage":  PumpedHydroStorageCostModel,
    # "geothermal":            GeothermalCostModel,
    # "carboncapture":    CarbonCaptureCostModel,
}