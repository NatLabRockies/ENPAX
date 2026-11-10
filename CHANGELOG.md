# CHANGELOG

## v0.1.0 - 14 May 2026

- Solar PV + BESS hybrid CAPEX/OPEX model
- Standalone battery energy storage CAPEX/OPEX model
- Generic passthrough model for custom CAPEX/OPEX inputs

## v0.1.1 - 02 Jun 2026

- Added README, CHANGELOG, LICENSE
- Registered on PyPI
- Added PyPI publishing workflows
- Added DISCLAIMER

## Unreleased

- Added `solar_bess_2025Q1`: utility-scale PV + BESS CAPEX/OPEX model based on PVSCM 2025 (UPV 2025Q1, 2024 USD). It keeps the `solar_bess_2024Q1` structure and reports CAPEX at modeled market price (MMP), reproducing the PVSCM 2025 spreadsheet MMP and O&M totals. It adds an `IncludeIndirect` toggle ([#2](https://github.com/NatLabRockies/ENPAX/issues/2))
- Added `configs/solar_bess_2025Q1.yaml` and tests against the PVSCM 2025 reference values
- Added `examples/compare_pvscm_2024Q1_vs_2025Q1.ipynb`, which compares the PVSCM Excel CAPEX totals with the ENPAX `solar_bess_2024Q1` and `solar_bess_2025Q1` models
