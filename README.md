# ENPAX
 
[![PyPI version](https://badge.fury.io/py/enpax.svg)](https://badge.fury.io/py/enpax)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/enpax)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
 
ENPAX (**EN**ergy **P**latform — **A**utomated e**X**penditures) is an open-source Python library that provides modular, bottom-up capital and operating expenditure (CAPEX/OPEX) models for energy technologies. Cost estimates are derived using system design, characteristics, site specific details, power system considerations and infrastructure assumptions.
 
## Software Requirements
 
- Python 3.10+
## Installing ENPAX
 
### PyPI
 
```bash
pip install enpax
```
 
### Source Installation
 
1. Using Git, navigate to a local target directory and clone the repository:
    ```bash
    git clone https://github.com/NatLabRockies/ENPAX.git
    ```
 
2. Navigate to `ENPAX`:
    ```bash
    cd ENPAX
    ```
 
3. Create a new virtual environment and activate it. Using Conda and naming it `enpax`:
    ```bash
    conda create --name enpax python=3.11 -y
    conda activate enpax
    ```
 
4. Install ENPAX and its dependencies:
    - To use ENPAX only:
        ```bash
        pip install .
        ```
    - To install in editable mode with development dependencies:
        ```bash
        pip install -e ".[develop]"
        ```
    - To install with example/notebook dependencies:
        ```bash
        pip install -e ".[examples]"
        ```
    - To install all optional dependencies at once:
        ```bash
        pip install -e ".[all]"
        ```
 
## Usage
 
ENPAX models can be configured and run either via YAML config files or Python dictionaries. Example notebooks are provided in the `examples/` directory:
 
- `examples_using_yaml_config_files.ipynb` — configure and run models using `.yaml` files from the `configs/` directory
- `examples_using_dictionaries.ipynb` — configure and run models programmatically in Python
### Quick Start
 
```python
from enpax.runner import CentralRunner
 
runner = CentralRunner(config="configs/solar_bess.yaml")
results = runner.run()
print(results)
```
 
## Available Models

The library is structured around a shared abstract base class (BaseCostModel) that enforces a consistent interface — run_capex(), run_opex(), and run_design() — across all technology models, and a central runner (CentralRunner) that assembles multi-technology systems from YAML configuration files and returns structured output objects (TechResult, SystemResult). The current release includes two fully detailed technology models as well as the ability for a user to define their own technology cost model, both applicable for CAPEX and O&M cost estimations. 

| Model | Description |
|-------|-------------|
| `solar_bess_2024Q1` | Solar PV + BESS hybrid CAPEX/OPEX model |
| `bess_2025` | Standalone battery energy storage CAPEX/OPEX model |
| `generic_passthrough` | Generic passthrough model for custom CAPEX/OPEX inputs |
 
## Release Notes
 
1. Ensure all tests pass.
2. Ensure this README is up to date.
3. Ensure dependency and Python versions are current.
4. Ensure `CHANGELOG.md` is up to date.
5. Bump the version in `pyproject.toml` using semantic versioning (<https://semver.org/>).
6. Make a pull request into `main` from `develop` or a patch release branch.
   1. Merge `main` back into `develop` if `develop` was not the base branch.
7. Tag the new release and push it:
    ```bash
    git tag -a v0.1.0 -m "message for v0.1.0"
    git push origin v0.1.0
    ```
    1. This will trigger the **Deploy to Test PyPI** GitHub Action. If it passes, proceed to step 8. If it fails, continue below.
    2. Delete the tag locally and on remote:
        ```bash
        git tag -d v0.1.0
        git push --delete origin v0.1.0
        ```
    3. Create a new branch off `main`, fix the build issue, and return to step 5.
8. Create a new release at <https://github.com/NatLabRockies/ENPAX/releases>, ensuring that:
   1. The newly created tag is selected, and
   2. **Generate release notes** is selected.
   This will trigger the **Deploy to PyPI** GitHub Action.
## Contributing
 
Contributions are welcome. Please open an issue or submit a pull request against the `develop` branch.
 
## Authors
 
- [Daniel Mulas Hernando](mailto:daniel.mulashernando@nlr.gov) — National Laboratory of the Rockies
- [Kaitlin Brunik](mailto:kaitlin.brunik@nlr.gov) — National Laboratory of the Rockies
- [Elenya Grant](mailto:elenya.grant@nlr.gov) — National Laboratory of the Rockies
## License
 
This project is licensed under the BSD 3-Clause License. See [LICENSE](LICENSE) for details.