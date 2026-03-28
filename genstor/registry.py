from genstor.models.bess import BESSCostModel
from genstor.models.solar_bess import SolarBESSCostModel

REGISTRY: dict[str, type] = {
    "bess":       BESSCostModel,
    "solar_bess": SolarBESSCostModel,
    # Future techs — uncomment as models are added:
    # "zinc_batteries":  ZincBESSCostModel,
    # "pumped_hydro_storage":  PumpedHydroStorageCostModel,
    # "geothermal":            GeothermalCostModel,
    # "carboncapture":    CarbonCaptureCostModel,
}