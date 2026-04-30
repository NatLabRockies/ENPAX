"""
generic_passthrough.py — Generic Passthrough Cost Model

Use this model type when a technology's costs are known up front but a
dedicated bottom-up model does not yet exist (or is not needed). Rather
than computing costs from first principles, you supply the CAPEX and/or
OPEX totals and their units directly in the YAML config (or as params in
a dictionary) along with any free-form design characteristics you want to
track.

The model passes those inputs straight through to the standard
CapexBreakdown / OpexBreakdown / DesignSummary output objects, so it is
fully compatible with CentralRunner and the rest of the ENPAX reporting
stack.

Typical use cases
-----------------
- Placeholder technology in a hybrid project while a full model is
  being developed.
- Third-party cost estimates received as a lump sum (e.g. from a quote
  or a techno-economic study) that need to sit alongside modeled techs.
- Technologies with well-known industry benchmark costs that don't
  warrant a bespoke model (e.g. a small diesel genset, a generic
  transmission line segment).

Minimal YAML example
--------------------
    technologies:
      - name: wind_turbine_placeholder
        type: generic_passthrough
        params:
          capex_total: 1450          # $/kW
          capex_unit: "$/kW"
          opex_annual_total: 43      # $/kW-yr
          opex_unit: "$/kW-yr"

Extended YAML example (with line items and design characteristics)
-----------------------------------------------------------------
    technologies:
      - name: geothermal_binary
        type: generic_passthrough
        params:
          capex_total: 4200          # $/kW
          capex_unit: "$/kW"
          capex_line_items:
            drilling:     1800
            power_block:   950
            bop:           800
            epc_overhead:  650
          opex_annual_total: 110     # $/kW-yr
          opex_unit: "$/kW-yr"
          opex_line_items:
            labor:          40
            maintenance:    35
            land_lease:     20
            insurance:      15
          design:
            capacity_mw:        50
            capacity_factor:    0.92
            plant_lifetime_yr:  30
"""

from __future__ import annotations

from enpax.base_model import BaseCostModel
from enpax.outputs import CapexBreakdown, DesignSummary, OpexBreakdown


class GenericPassthroughCostModel(BaseCostModel):
    """
    A thin pass-through wrapper around BaseCostModel.

    Parameters (all optional except capex_total or opex_annual_total)
    -----------------------------------------------------------------
    capex_total : float
        CAPEX expressed in whatever unit is declared in ``capex_unit``.
        If omitted, no CapexBreakdown is produced.
    capex_unit : str
        Human-readable unit string for CAPEX (e.g. ``"$/kW"``,
        ``"$/kWh-cap"``, ``"$/kWdc"``). Defaults to ``"$/kW"``.
    capex_line_items : dict[str, float]
        Optional flat mapping of cost-component names to their values
        (same unit as ``capex_total``). Used for reporting only.

    opex_annual_total : float
        Annual OPEX expressed in whatever unit is declared in
        ``opex_unit``. If omitted, no OpexBreakdown is produced.
    opex_unit : str
        Human-readable unit string for OPEX (e.g. ``"$/kW-yr"``).
        Defaults to ``"$/kW-yr"``.
    opex_line_items : dict[str, float]
        Optional flat mapping of O&M cost-component names to their
        values (same unit as ``opex_annual_total``).

    design : dict[str, float | str]
        Optional free-form dictionary of design characteristics to
        surface in the DesignSummary (e.g. capacity, efficiency, fuel
        type). All values are passed through as-is.
    """

    DEFAULTS: dict = {
        "capex_total":        None,   # float | None — required for CAPEX output
        "capex_unit":         "$/kW",
        "capex_line_items":   {},
        "opex_annual_total":  None,   # float | None — required for OPEX output
        "opex_unit":          "$/kW-yr",
        "opex_line_items":    {},
        "design":             {},
    }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        cfg = self.config
        if cfg["capex_total"] is None and cfg["opex_annual_total"] is None:
            raise ValueError(
                f"[{self.name}] GenericPassthroughCostModel requires at least one of "
                "'capex_total' or 'opex_annual_total' to be set in params."
            )
        for key in ("capex_total", "opex_annual_total"):
            val = cfg[key]
            if val is not None and not isinstance(val, (int, float)):
                raise TypeError(
                    f"[{self.name}] '{key}' must be a number, got {type(val).__name__}."
                )
        for key in ("capex_line_items", "opex_line_items", "design"):
            if not isinstance(cfg[key], dict):
                raise TypeError(
                    f"[{self.name}] '{key}' must be a dict, got {type(cfg[key]).__name__}."
                )

    # ------------------------------------------------------------------
    # BaseCostModel interface
    # ------------------------------------------------------------------

    def run_capex(self) -> CapexBreakdown | None:
        """
        Return a CapexBreakdown populated directly from config values.
        Returns None if ``capex_total`` was not provided.
        """
        self._validate()
        cfg = self.config
        if cfg["capex_total"] is None:
            return None
        return CapexBreakdown(
            total=float(cfg["capex_total"]),
            unit=cfg["capex_unit"],
            line_items=dict(cfg["capex_line_items"]),
        )

    def run_opex(self) -> OpexBreakdown | None:
        """
        Return an OpexBreakdown populated directly from config values.
        Returns None if ``opex_annual_total`` was not provided.
        """
        cfg = self.config
        if cfg["opex_annual_total"] is None:
            return None
        return OpexBreakdown(
            annual_total=float(cfg["opex_annual_total"]),
            unit=cfg["opex_unit"],
            line_items=dict(cfg["opex_line_items"]),
        )

    def run_design(self) -> DesignSummary:
        """
        Return a DesignSummary from the free-form ``design`` dict in config.
        Returns an empty DesignSummary if no design characteristics were provided.
        """
        return DesignSummary(line_items=dict(self.config["design"]))
