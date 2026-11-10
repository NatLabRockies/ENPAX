from enpax.models.bess_2025 import BESS2025CostModel
from enpax.models.solar_bess_2024Q1 import SolarBESS2024Q1CostModel
from enpax.models.solar_bess_2025Q1 import SolarBESS2025Q1CostModel
from enpax.models.generic_passthrough import GenericPassthroughCostModel

REGISTRY: dict[str, type] = {
    "bess_2025":       BESS2025CostModel,
    "solar_bess_2024Q1": SolarBESS2024Q1CostModel,
    "solar_bess_2025Q1": SolarBESS2025Q1CostModel,
    "generic_passthrough": GenericPassthroughCostModel
    # Future techs — uncomment as models are added:
    # "zinc_batteries":  ZincBESSCostModel,
    # "pumped_hydro_storage":  PumpedHydroStorageCostModel,
    # "geothermal":            GeothermalCostModel,
    # "carboncapture":    CarbonCaptureCostModel,
}