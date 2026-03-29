from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import json
import yaml

from genstor.outputs import DesignSummary, CapexBreakdown, OpexBreakdown, TechResult


class BaseCostModel(ABC):

    # Subclasses declare their defaults dict at class level
    DEFAULTS: dict = {}

    def __init__(self, name: str, tech_type: str, params: dict):
        self.name = name
        self.tech_type = tech_type
        if params and not isinstance(params, dict):
            raise ValueError("params must be a dictionary.")
        self.config = {**self.DEFAULTS, **(params or {})}

    # ------------------------------------------------------------------
    # Config loading — shared by all subclasses, no duplication needed
    # ------------------------------------------------------------------
    @classmethod
    def from_config_file(cls, file_name: str, name: str = None, tech_type: str = None):
        base_dir = Path(__file__).parent.absolute()
        search_paths = [
            base_dir / file_name,
            base_dir / "configs" / file_name,
            base_dir.parent / "configs" / file_name,
            base_dir.parent / "configs" / "single_tech" / file_name,
        ]
        full_path = next((p for p in search_paths if p.exists()), Path(file_name))

        if not full_path.exists():
            tried = "\n".join(str(p) for p in search_paths)
            raise FileNotFoundError(f"Could not find '{file_name}'. Checked:\n{tried}")

        with open(full_path) as f:
            if full_path.suffix == ".json":
                data = json.load(f)
            elif full_path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported format: {full_path.suffix}. Use .json or .yaml")

        resolved_name = name or data.pop("name", cls.__name__)
        resolved_type = tech_type or data.pop("tech_type", cls.__name__.lower())
        return cls(name=resolved_name, tech_type=resolved_type, params=data)

    # ------------------------------------------------------------------
    # Abstract interface every tech model must implement
    # ------------------------------------------------------------------
    @abstractmethod
    def run_capex(self) -> CapexBreakdown:
        """Return a CapexBreakdown with total, unit, and line_items."""
        pass

    def run_opex(self) -> Optional[OpexBreakdown]:
        """
        Override in subclass if this tech has OPEX.
        Returns None by default — runner skips gracefully.
        """
        return None

    # ------------------------------------------------------------------
    # Dynamic attribute resolution — preserves existing __getattr__ pattern
    # ------------------------------------------------------------------
    def __getattr__(self, name: str):
        if name.startswith("calculate_") and "_per_" in name:
            # e.g. calculate_li_ion_cost_per_kwh → get_li_ion_cost_breakdown
            suffix_start = name.rfind("_per_")
            getter_name = "get_" + name[10:suffix_start] + "_breakdown"
            if hasattr(self.__class__, getter_name) or getter_name in self.__dict__:
                def _caller():
                    breakdown = getattr(self, getter_name)()
                    return breakdown[next(k for k in breakdown if k.startswith("total_"))]
                return _caller
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    # ------------------------------------------------------------------
    # Top-level runner — produces a TechResult
    # ------------------------------------------------------------------
    def run(self) -> TechResult:
        return TechResult(
            tech_name=self.name,
            tech_type=self.tech_type,
            capex=self.run_capex(),
            opex=self.run_opex(),
            design=self.run_design(),
            
        )