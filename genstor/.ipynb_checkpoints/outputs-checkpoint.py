from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CapexBreakdown:
    total: float
    unit: str                             # e.g. "$/kWh-cap" or "$/kWdc"
    line_items: dict[str, float] = field(default_factory=dict)
    # line_items can be flat or nested {"subsystem": {"component": value}}

@dataclass
class OpexBreakdown:
    annual_total: float
    unit: str                             # e.g. "$/kW-yr"
    line_items: dict[str, float] = field(default_factory=dict)

@dataclass
class TechResult:
    tech_name: str
    tech_type: str
    capex: Optional[CapexBreakdown] = None
    opex: Optional[OpexBreakdown] = None

@dataclass
class SystemResult:
    project_name: str
    tech_results: list[TechResult] = field(default_factory=list)

    @property
    def total_capex(self) -> dict[str, float]:
        """
        Returns per-unit totals keyed by unit string.
        Warns if mixing units — caller should be aware.
        """
        totals: dict[str, float] = {}
        for t in self.tech_results:
            if t.capex:
                totals[t.tech_name] = t.capex.total
        return totals

    @property
    def total_annual_opex(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for t in self.tech_results:
            if t.opex:
                totals[t.tech_name] = t.opex.annual_total
        return totals

    def capex_by_tech(self) -> dict[str, dict]:
        return {
            t.tech_name: {"total": t.capex.total, "unit": t.capex.unit}
            for t in self.tech_results if t.capex
        }

    def opex_by_tech(self) -> dict[str, dict]:
        return {
            t.tech_name: {"annual_total": t.opex.annual_total, "unit": t.opex.unit}
            for t in self.tech_results if t.opex
        }

    def summary(self) -> dict:
        return {
            "project": self.project_name,
            "capex_by_tech": self.capex_by_tech(),
            "opex_by_tech": self.opex_by_tech(),
        }