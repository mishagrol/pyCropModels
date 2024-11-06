# pyCropModels

Python package for modeling and analyzing various crop models and conduct sensitivity analysis under future climate.

## Table of Contents

- [pyCropModels](#pycropmodels)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Installation](#installation)
  - [Notebooks](#notebooks)
  - [Models](#models)
  - [Data](#data)
  - [Usage](#usage)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Overview

`pyCropModels` is a Python package designed for modeling and analyzing various crop models. This package provides tools for simulating crop growth, yield prediction, and analyzing the impact of different variables on crop performance.

## Installation

To install the `pyCropModels` package, follow these steps:

1. Clone the repository: `git clone https://github.com/your-repo/pyCropModels.git`
2. Navigate to the repository directory: `cd pyCropModels`
3. Install the required packages: `pip install -r requirements.txt`

## Notebooks

The `notebooks` folder contains Jupyter notebooks that demonstrate the usage of the `pyCropModels` and CSM models. These notebooks cover various aspects of crop modeling, including data preparation, model development, and scenario analysis.

1. `1. DSSAT-Spatial-Sensitivity-Wheat.ipynb`: Spatial sensitivity analysis for DSSAT model for soil parameters for wheat.
2. `2. LARS-WG.ipynb`: Converter of LARS-WG generated scenarios for models and NASA POWER to LARS-WG.
3. `3. Wheat-Soil-SA-DSSAT-24.ipynb`: Sensitivity analysis of DSSAT under current climate for soil parameters and wheat crop.
4. `4. MONICA-SA-Soil-Climate-Change.ipynb`: Sensitivity analysis of MONICA under future climate for soil parameters.
5. `5. Sensitivity analysis of Wofost for climate.ipynb`: Sensitivity analysis of Wofost under future climate for crop parameters.
6. `6. EnsembleCropSimulationModels.ipynb`: Ensemble crop simulation models using the DSSAT, WOFOST and MONICA models.
7. `6. Plots results.ipynb`: Plots for model ensembling performance.

## Models

The `pyCropModels` package includes the following crop models:

1. DSSAT model: A widely used crop simulation model that simulates crop growth and yield.
2. Machine learning models: Various machine learning algorithms, such as linear regression, decision trees, and random forests, are implemented for crop yield prediction.

## Data

The `data` folder contains sample datasets required for modeling. These datasets include weather data, soil data, and crop management data.

## Usage

Run docker with installed models and jupyter notebooks

`bash run_in_docker.sh`

## Contributing

Contributions to the `pyCropModels` package are welcome. If you would like to contribute, please follow these steps:

1. Fork the repository: `git fork https://github.com/tensorfields-llc/pyCropModels.git`
2. Create a new branch: `git branch new-feature`
3. Make changes and commit: `git commit -m "New feature"`
4. Push changes to the branch: `git push origin new-feature`
5. Create a pull request: `git pull-request new-feature`

## License

The `pyCropModels` package is licensed under the MIT License.

## Acknowledgments

The `pyCropModels` package was developed with the support of [Your Organization]. We would like to thank [Name] for their contributions to the package.
