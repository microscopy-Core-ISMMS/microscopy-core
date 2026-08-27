# Microscopy Core quality-assessment website

This repository builds the Microscopy and Advanced BioImaging CoRE's Quarto
website. It turns tracked laser-power and point-spread-function (PSF)
measurements into plots, summary tables, and microscope-specific pages.

## Requirements

- Python 3.12 or newer
- [Quarto](https://quarto.org/docs/get-started/)

Create a virtual environment and install the runtime dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Build the website

Run the generators in this order from the repository root:

```bash
python scripts/generate_microscope_pages.py
quarto render index.ipynb --execute
python scripts/generate_psf_plots.py
python scripts/generate_microscope_pages.py
quarto render
```

The first page-generation pass creates `_navbar.yml`, which Quarto expects
before rendering. The analysis steps write generated artifacts to `outputs/`,
and the second pass adds links to those artifacts. The finished site is placed
in `_site/`. Both directories are intentionally ignored by Git.

## Development checks

Install the development tools and run the same checks used by CI:

```bash
python -m pip install -r requirements-dev.txt
python -m black --check scripts
python -m ruff check scripts
python -m compileall -q scripts
```

## Repository layout

- `data/` contains source QA measurements. Treat these files as scientific
  records; do not rewrite them as part of code-only changes.
- `scripts/` contains the page and plot generators.
- `microscopes/` and `image_analysis/` contain Quarto source pages.
- `images/` contains site images and workflow screenshots.
- `.github/workflows/pages.yml` builds and publishes the site from `main`.

GitHub Actions performs the complete build and deploys the resulting `_site/`
artifact to GitHub Pages.
