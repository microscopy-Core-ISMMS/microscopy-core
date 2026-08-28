# Microscopy and Advanced BioImaging CoRE

[![Publish Quarto website](https://github.com/microscopy-Core-ISMMS/microscopy-core/actions/workflows/pages.yml/badge.svg)](https://github.com/microscopy-Core-ISMMS/microscopy-core/actions/workflows/pages.yml)

This repository contains the quality-assessment website for the Microscopy and
Advanced BioImaging CoRE. It turns routine microscope measurements into
interactive plots, downloadable summary files, and microscope-specific pages.
The website is built with Python and [Quarto](https://quarto.org/) and is
published automatically through GitHub Pages.

## What the project provides

- Longitudinal laser-power measurements organized by microscope and wavelength
- Point-spread-function (PSF) measurements organized by microscope, objective,
  and channel
- Interactive Plotly charts, including PSF plots displayed in nanometers
- Downloadable combined CSV and Excel summaries
- Automatically generated Quarto pages and navigation
- Automated code-quality checks and GitHub Pages deployment

## Repository structure

```text
microscopy-core/
├── data/
│   ├── Laser_Power_Measurements/   # Source laser-power records
│   └── PSF_Measurements/           # Source PSF records
├── image_analysis/                  # Image-analysis documentation
├── images/                          # Website images and screenshots
├── microscopes/                     # Quarto microscope pages
│   ├── laser_power/
│   └── psf/
├── scripts/
│   ├── generate_microscope_pages.py
│   └── generate_psf_plots.py
├── index.ipynb                      # Laser-power analysis and home page
├── _quarto.yml                      # Quarto website configuration
├── requirements.txt                 # Runtime Python dependencies
└── requirements-dev.txt             # Development and CI dependencies
```

The build creates `outputs/`, `_navbar.yml`, and `_site/`. These generated
artifacts are not intended to be edited manually.

## Requirements

- Python 3.12 or newer
- [Quarto](https://quarto.org/docs/get-started/)
- Jupyter support for Quarto

## Local setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/microscopy-Core-ISMMS/microscopy-core.git
cd microscopy-core
```

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Build the website

Run the following commands from the repository root:

```bash
python scripts/generate_microscope_pages.py
quarto render index.ipynb --execute
python scripts/generate_psf_plots.py
python scripts/generate_microscope_pages.py
quarto render
```

The first page-generation pass creates `_navbar.yml`, which Quarto needs before
rendering. The analysis steps then create plots and summary files under
`outputs/`. Running the page generator again adds links to those artifacts. The
finished website is written to `_site/`.

To preview the site locally after generating the analysis outputs, run:

```bash
quarto preview
```

## Add measurement data

Treat files under `data/` as scientific source records. Add new files without
rewriting previous measurements.

Create one underscore-delimited folder per microscope, using the same folder
name in the relevant measurement directories. For example:

```text
data/Laser_Power_Measurements/Zeiss_LSM880/
data/PSF_Measurements/Zeiss_LSM880/
```

Laser-power filenames use the measurement month, year, and wavelength:

```text
MM-YY_WAVELENGTH.csv
02-26_405.csv
```

A laser-power microscope folder may also contain `target_month.txt`. Its value
must use the `MM-YY` format.

PSF filenames must include the measurement month and year followed by an
objective token such as `10x`, `20xW`, `40xO`, `63xO`, or `100x`:

```text
01-26_10x.csv
07-25_40xO.csv
```

After adding data, run the complete build so plots, summaries, pages, and
navigation are regenerated.

## Development checks

Run the same Python checks used by GitHub Actions:

```bash
python -m black --check scripts
python -m ruff check scripts
python -m compileall -q scripts
```

To apply Black formatting before committing:

```bash
python -m black scripts
```

## Deployment

The workflow in `.github/workflows/pages.yml` runs whenever changes are pushed
to `main` or when it is started manually. It performs the following steps:

1. Installs Python and Quarto.
2. Runs Black, Ruff, and Python compilation checks.
3. Generates the microscope analyses, plots, pages, and navigation.
4. Renders the Quarto website into `_site/`.
5. Publishes `_site/` to GitHub Pages.

Deployment status and logs are available from the repository's **Actions** tab.

## Contributing

1. Create a branch for your change.
2. Add or update the relevant source data, script, or Quarto page.
3. Run the development checks and complete website build locally.
4. Commit the change and open a pull request against `main`.

When changing folder names, update the matching data paths consistently so the
page and plot generators continue to associate measurements with the correct
microscope.
