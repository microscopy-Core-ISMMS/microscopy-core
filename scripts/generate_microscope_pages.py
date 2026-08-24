from pathlib import Path
import re


# ==================================================
# PROJECT DIRECTORIES
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = (
    PROJECT_DIR
    / "data"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "outputs"
)


# --------------------------------------------------
# Measurement data directories
# --------------------------------------------------

LASER_DATA_DIR = (
    DATA_DIR
    / "Laser_Power_Measurements"
)

PSF_DATA_DIR = (
    DATA_DIR
    / "PSF_Measurements"
)


# --------------------------------------------------
# Website page directories
# --------------------------------------------------

MICROSCOPE_PAGE_DIR = (
    PROJECT_DIR
    / "microscopes"
)

LASER_PAGE_DIR = (
    MICROSCOPE_PAGE_DIR
    / "laser_power"
)

PSF_PAGE_DIR = (
    MICROSCOPE_PAGE_DIR
    / "psf"
)


# --------------------------------------------------
# Create generated-page directories
# --------------------------------------------------

LASER_PAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PSF_PAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def display_name(
    name: str,
) -> str:
    """
    Convert folder names into
    human-readable microscope names.

    Examples:
        LSM_980
        ->
        LSM 980

        Andor_Dragonfly_620
        ->
        Andor Dragonfly 620
    """

    return name.replace(
        "_",
        " ",
    )


def wavelength_from_name(
    path: Path,
) -> int:
    """
    Extract wavelength from a laser plot filename.

    Examples:
        laser_power_405nm.png
        ->
        405

        laser_power_max_488nm.png
        ->
        488
    """

    match = re.search(
        r"(\d+)nm$",
        path.stem,
    )

    if match:

        return int(
            match.group(1)
        )

    return 99999


def objective_sort_key(
    name: str,
):
    """
    Sort objective names numerically.

    Examples:
        10x
        20xw
        40xo
        63xo
        100x
    """

    match = re.search(
        r"(\d+)",
        name,
    )

    if match:

        return (
            int(
                match.group(1)
            ),
            name.lower(),
        )

    return (
        99999,
        name.lower(),
    )


def detect_microscopes(
    data_folder: Path,
):
    """
    Return microscope directories inside
    a measurement data folder.

    Hidden directories are ignored.
    """

    if not data_folder.exists():

        print(
            "Warning: data directory "
            f"does not exist: "
            f"{data_folder}"
        )

        return []

    return sorted(
        [
            folder
            for folder
            in data_folder.iterdir()
            if (
                folder.is_dir()
                and not
                folder.name.startswith(".")
            )
        ],
        key=lambda folder:
            folder.name.lower(),
    )


# ==================================================
# DETECT MICROSCOPES
# ==================================================

laser_microscopes = (
    detect_microscopes(
        LASER_DATA_DIR
    )
)

psf_microscopes = (
    detect_microscopes(
        PSF_DATA_DIR
    )
)


print(
    "Laser Power microscopes:",
    ", ".join(
        folder.name
        for folder
        in laser_microscopes
    )
    or "None",
)

print(
    "PSF microscopes:",
    ", ".join(
        folder.name
        for folder
        in psf_microscopes
    )
    or "None",
)


# ==================================================
# GENERATE NAVBAR
# ==================================================

NAVBAR_FILE = (
    PROJECT_DIR
    / "_navbar.yml"
)


navbar_lines = [
    "website:",
    "  navbar:",
    "    left:",

    "      - href: index.html",
    '        text: "Home"',

    (
        '      - text: '
        '"Quality Assessment - '
        'Confocal Microscopes"'
    ),
    "        menu:",

    (
        '          - text: '
        '"Introduction"'
    ),
    (
        "            href: "
        "microscopes/index.html"
    ),

    (
        '          - text: '
        '"Laser Power Measurements"'
    ),
    (
        "            href: "
        "microscopes/"
        "laser_power/index.html"
    ),

    (
        '          - text: '
        '"PSF Measurements"'
    ),
    (
        "            href: "
        "microscopes/"
        "psf/index.html"
    ),

    (
        '      - text: '
        '"Image Analysis"'
    ),
    "        menu:",

    (
        '          - text: '
        '"Introduction"'
    ),
    (
        "            href: "
        "image_analysis/index.html"
    ),

    (
        '          - text: '
        '"FIJI/ImageJ Workflows"'
    ),
    (
        "            href: "
        "image_analysis/"
        "fiji_imagej/index.html"
    ),
]


NAVBAR_FILE.write_text(
    "\n".join(
        navbar_lines
    )
    + "\n",
    encoding="utf-8",
)


print(
    ""
)

print(
    "Generated navbar:"
)

print(
    "  Laser Power Measurements: "
    f"{len(laser_microscopes)} "
    "microscopes"
)

print(
    "  PSF Measurements: "
    f"{len(psf_microscopes)} "
    "microscopes"
)


# ==================================================
# LASER POWER MEASUREMENTS
# ==================================================


# --------------------------------------------------
# Laser Power landing page
# --------------------------------------------------

laser_index_lines = [
    "---",
    (
        'title: "Confocal Microscopes - '
        'Laser Power Measurements"'
    ),
    "toc: true",
    "---",
    "",
    "## Introduction",
    "",
    (
        "Quality assurance of illumination "
        "power stability is critical because "
        "fluorescence intensity measurements "
        "depend directly on the excitation "
        "power delivered to the sample. "
        "Under standard imaging conditions, "
        "the emitted fluorescence signal is "
        "proportional to the fluorophore "
        "concentration and the excitation "
        "light intensity. Any fluctuation in "
        "illumination power can therefore "
        "alter measured signal levels, "
        "potentially leading to incorrect "
        "conclusions about changes in "
        "fluorophore abundance, molecular "
        "interactions, or cellular dynamics. "
        "Ensuring stable and reproducible "
        "excitation conditions is essential "
        "for reliable quantitative "
        "fluorescence imaging."
    ),
    "",
    (
        "Over time, illumination sources such "
        "as lasers or LEDs can exhibit "
        "fluctuations due to component aging, "
        "temperature changes, electronic "
        "instability, or optical misalignment "
        "within the light path. These "
        "variations may occur over multiple "
        "time scales and can introduce "
        "unwanted variability between images "
        "acquired during a single experiment "
        "or across different experimental "
        "sessions. Routine monitoring of "
        "illumination power stability allows "
        "early detection of such fluctuations "
        "and helps ensure that excitation "
        "conditions remain consistent and "
        "reproducible."
    ),
    "",
    "## Laser Power Results",
    "",
    (
        "Select a confocal microscope to "
        "view its laser-power measurements."
    ),
    "",
]


for microscope_dir in (
    laser_microscopes
):

    microscope = (
        microscope_dir.name
    )

    title = display_name(
        microscope
    )

    laser_index_lines.append(
        f"- [{title}]"
        f"({microscope}.html)"
    )


(
    LASER_PAGE_DIR
    / "index.qmd"
).write_text(
    "\n".join(
        laser_index_lines
    )
    + "\n",
    encoding="utf-8",
)


print(
    "Generated Laser Power "
    "landing page."
)


# --------------------------------------------------
# Create one Laser Power page per microscope
# --------------------------------------------------

for microscope_dir in (
    laser_microscopes
):

    microscope = (
        microscope_dir.name
    )

    title = display_name(
        microscope
    )


    # ----------------------------------------------
    # Output locations
    # ----------------------------------------------

    microscope_output = (
        OUTPUT_DIR
        / microscope
    )

    plot_dir = (
        microscope_output
        / "plots"
    )

    excel_path = (
        microscope_output
        / "combined_power_data.xlsx"
    )


    # ----------------------------------------------
    # Find interactive calibration plots
    # ----------------------------------------------

    calibration_plots = []

    if plot_dir.exists():

        calibration_plots = sorted(
            [
                plot
                for plot
                in plot_dir.glob(
                    "laser_power_*nm.html"
                )
                if not
                plot.name.startswith(
                    "laser_power_max_"
                )
            ],
            key=wavelength_from_name,
        )


    # ----------------------------------------------
    # Find interactive maximum-power plots
    # ----------------------------------------------

    maximum_plots = []

    if plot_dir.exists():

        maximum_plots = sorted(
            plot_dir.glob(
                "laser_power_max_*nm.html"
            ),
            key=wavelength_from_name,
        )


    # ----------------------------------------------
    # Organize plots by wavelength
    # ----------------------------------------------

    calibration_by_wavelength = {
        wavelength_from_name(
            plot
        ): plot
        for plot
        in calibration_plots
    }

    maximum_by_wavelength = {
        wavelength_from_name(
            plot
        ): plot
        for plot
        in maximum_plots
    }


    wavelengths = sorted(
        set(
            calibration_by_wavelength.keys()
        )
        |
        set(
            maximum_by_wavelength.keys()
        )
    )


    # ----------------------------------------------
    # Start microscope page
    # ----------------------------------------------

    lines = [
        "---",
        f'title: "{title}"',
        "toc: true",
        "format:",
        "  html:",
        "    page-layout: full",
        "    grid:",
        "      body-width: 1250px",
        "      margin-width: 220px",
        "      gutter-width: 1.5rem",
        "other-links:",
        (
            '  - text: '
            '"← Back to Laser Power Measurements"'
        ),
        "    href: index.html",
        "---",
        "",
        "## Laser Power Measurements",
        "",
        (
            "Laser calibration and maximum-power "
            "measurements are shown below for each "
            "available wavelength."
        ),
        "",
        (
            "These plots are interactive. Hover over "
            "individual measurements to view values, "
            "click legend entries to show or hide "
            "measurements, and use the Plotly toolbar "
            "to zoom, pan, autoscale, or reset the plot."
        ),
        "",
    ]


    # ----------------------------------------------
    # Laser Power Dashboard
    # ----------------------------------------------

    if wavelengths:

        for wavelength in (
            wavelengths
        ):

            calibration_plot = (
                calibration_by_wavelength.get(
                    wavelength
                )
            )

            maximum_plot = (
                maximum_by_wavelength.get(
                    wavelength
                )
            )


            # ======================================
            # Wavelength heading and grid
            # ======================================

            lines.extend(
                [
                    f"### {wavelength} nm",
                    "",
                    "::: {.grid}",
                    "",
                ]
            )


            # ======================================
            # LEFT COLUMN
            # Laser Power Calibration
            # ======================================

            lines.extend(
                [
                    (
                        "::: "
                        "{.g-col-12 "
                        ".g-col-md-6 "
                        ".border "
                        ".rounded "
                        ".p-3}"
                    ),
                    "",
                    "#### Laser Power Trend",
                    "",
                ]
            )


            if calibration_plot is not None:

                calibration_plot_path = (
                    "../../outputs/"
                    f"{microscope}/"
                    "plots/"
                    f"{calibration_plot.name}"
                )

                lines.extend(
                    [
                        '<div class="plotly-dashboard">',
                        (
                            f'<iframe '
                            f'src="{calibration_plot_path}" '
                            f'width="100%" '
                            f'height="600" '
                            f'style="'
                            f'border:none; '
                            f'width:100%;" '
                            f'loading="lazy">'
                            f'</iframe>'
                        ),
                        "</div>",
                        "",
                    ]
                )

            else:

                lines.extend(
                    [
                        (
                            "No laser-power trend "
                            "plot is available."
                        ),
                        "",
                    ]
                )


            # Close left column
            lines.extend(
                [
                    ":::",
                    "",
                ]
            )


            # ======================================
            # RIGHT COLUMN
            # Maximum Laser Power
            # ======================================

            lines.extend(
                [
                    (
                        "::: "
                        "{.g-col-12 "
                        ".g-col-md-6 "
                        ".border "
                        ".rounded "
                        ".p-3}"
                    ),
                    "",
                    "#### Maximum Laser Power",
                    "",
                ]
            )


            if maximum_plot is not None:

                maximum_plot_path = (
                    "../../outputs/"
                    f"{microscope}/"
                    "plots/"
                    f"{maximum_plot.name}"
                )

                lines.extend(
                    [
                        '<div class="plotly-dashboard">',
                        (
                            f'<iframe '
                            f'src="{maximum_plot_path}" '
                            f'width="100%" '
                            f'height="600" '
                            f'style="'
                            f'border:none; '
                            f'width:100%;" '
                            f'loading="lazy">'
                            f'</iframe>'
                        ),
                        "</div>",
                        "",
                    ]
                )

            else:

                lines.extend(
                    [
                        (
                            "No maximum-power "
                            "plot is available."
                        ),
                        "",
                    ]
                )


            # Close right column
            lines.extend(
                [
                    ":::",
                    "",
                ]
            )


            # Close grid
            lines.extend(
                [
                    ":::",
                    "",
                ]
            )


    else:

        lines.extend(
            [
                (
                    "No interactive laser-power "
                    "plots are currently available."
                ),
                "",
            ]
        )


    # ----------------------------------------------
    # Excel download
    # ----------------------------------------------

    lines.extend(
        [
            (
                "## Download Data "
                "{.unnumbered .unlisted}"
            ),
            "",
        ]
    )


    if excel_path.exists():

        excel_link = (
            "../../outputs/"
            f"{microscope}/"
            "combined_power_data.xlsx"
        )

        lines.extend(
            [
                (
                    f"[Download {title} "
                    f"Excel workbook]"
                    f"({excel_link})"
                    "{.btn .btn-primary}"
                ),
                "",
            ]
        )

    else:

        lines.extend(
            [
                (
                    "The Excel workbook "
                    "is not available."
                ),
                "",
            ]
        )


    # ----------------------------------------------
    # Write microscope page
    # ----------------------------------------------

    page_path = (
        LASER_PAGE_DIR
        / f"{microscope}.qmd"
    )

    page_path.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8",
    )


    print(
        "Generated Laser Power page: "
        f"{page_path.name}"
    )


print(
    "Generated "
    f"{len(laser_microscopes)} "
    "Laser Power microscope pages."
)


# ==================================================
# PSF MEASUREMENTS
# ==================================================


# --------------------------------------------------
# PSF landing page
# --------------------------------------------------

psf_index_lines = [
    "---",
    (
        'title: "Confocal Microscopes - '
        'PSF Measurements"'
    ),
    "toc: true",
    "---",
    "",
    "## Introduction",
    "",
    (
        "Point spread function (PSF) "
        "measurements are used to evaluate "
        "the spatial resolution and optical "
        "performance of a microscope."
    ),
    "",
    (
        "Routine PSF measurements can help "
        "identify changes in microscope "
        "alignment, objective performance, "
        "optical aberrations, and other "
        "factors that may affect image "
        "quality and quantitative microscopy "
        "measurements."
    ),
    "",
    "## PSF Results",
    "",
    (
        "Select a confocal microscope to "
        "view its PSF measurements."
    ),
    "",
]


for microscope_dir in (
    psf_microscopes
):

    microscope = (
        microscope_dir.name
    )

    title = display_name(
        microscope
    )

    psf_index_lines.append(
        f"- [{title}]"
        f"({microscope}.html)"
    )


(
    PSF_PAGE_DIR
    / "index.qmd"
).write_text(
    "\n".join(
        psf_index_lines
    )
    + "\n",
    encoding="utf-8",
)


print(
    "Generated PSF landing page."
)


# --------------------------------------------------
# Create one PSF page per microscope
# --------------------------------------------------

for microscope_dir in (
    psf_microscopes
):

    microscope = (
        microscope_dir.name
    )

    title = display_name(
        microscope
    )


    # ----------------------------------------------
    # PSF output directories
    # ----------------------------------------------

    psf_output_dir = (
        OUTPUT_DIR
        / "PSF_Measurements"
        / microscope
    )

    psf_plot_dir = (
        psf_output_dir
        / "plots"
    )

    combined_psf_csv = (
        psf_output_dir
        / "combined_PSF_data.csv"
    )


    # ----------------------------------------------
    # Find XY Plotly plots
    # ----------------------------------------------

    xy_plots = []

    if psf_plot_dir.exists():

        xy_plots = sorted(
            psf_plot_dir.glob(
                "PSF_XY_*.html"
            ),
            key=lambda path:
                path.name.lower(),
        )


    # ----------------------------------------------
    # Find Z Plotly plots
    # ----------------------------------------------

    z_plots = []

    if psf_plot_dir.exists():

        z_plots = sorted(
            psf_plot_dir.glob(
                "PSF_Z_*.html"
            ),
            key=lambda path:
                path.name.lower(),
        )


    # ----------------------------------------------
    # Organize XY plots by objective
    # ----------------------------------------------

    xy_by_objective = {}

    for plot in xy_plots:

        objective = (
            plot.stem
            .replace(
                "PSF_XY_",
                "",
            )
        )

        xy_by_objective[
            objective
        ] = plot


    # ----------------------------------------------
    # Organize Z plots by objective
    # ----------------------------------------------

    z_by_objective = {}

    for plot in z_plots:

        objective = (
            plot.stem
            .replace(
                "PSF_Z_",
                "",
            )
        )

        z_by_objective[
            objective
        ] = plot


    # ----------------------------------------------
    # Determine all objectives
    # ----------------------------------------------

    objectives = sorted(
        set(
            xy_by_objective.keys()
        )
        |
        set(
            z_by_objective.keys()
        ),
        key=objective_sort_key,
    )


    # ----------------------------------------------
    # Start PSF microscope page
    # ----------------------------------------------

    psf_lines = [
        "---",
        f'title: "{title}"',
        "toc: true",
        "format:",
        "  html:",
        "    page-layout: full",
        "    grid:",
        "      body-width: 1250px",
        "      margin-width: 220px",
        "      gutter-width: 1.5rem",
        "other-links:",
        (
            '  - text: '
            '"← Back to PSF Measurements"'
        ),
        "    href: index.html",
        "---",
        "",
        "## PSF Measurements",
        "",
        (
            "Lateral and axial point spread "
            "function measurements are shown "
            "below for each objective."
        ),
        "",
        (
            "These plots are interactive. "
            "Hover over individual measurements "
            "to view values, click channels in "
            "the legend to show or hide them, "
            "and use the Plotly toolbar to zoom, "
            "pan, autoscale, or reset the plot."
        ),
        "",
    ]


    # ----------------------------------------------
    # PSF Dashboard
    # ----------------------------------------------

    if objectives:

        for objective in (
            objectives
        ):

            display_objective = (
                objective.upper()
            )


            xy_plot = (
                xy_by_objective.get(
                    objective
                )
            )

            z_plot = (
                z_by_objective.get(
                    objective
                )
            )


            # ======================================
            # Objective heading
            # ======================================

            psf_lines.extend(
                [
                    (
                        f"### "
                        f"{display_objective} "
                        f"Objective"
                    ),
                    "",
                    "::: {.grid}",
                    "",
                ]
            )


            # ======================================
            # LEFT COLUMN
            # Lateral PSF XY
            # ======================================

            psf_lines.extend(
                [
                    (
                        "::: "
                        "{.g-col-12 "
                        ".g-col-md-6 "
                        ".border "
                        ".rounded "
                        ".p-3}"
                    ),
                    "",
                    "#### Lateral PSF (XY)",
                    "",
                ]
            )


            if xy_plot is not None:

                xy_plot_path = (
                    "../../outputs/"
                    "PSF_Measurements/"
                    f"{microscope}/"
                    "plots/"
                    f"{xy_plot.name}"
                )   

                psf_lines.extend(
                    [
                        '<div class="plotly-dashboard">',
                        (
                            f'<iframe '
                            f'src="{xy_plot_path}" '
                            f'width="100%" '
                            f'height="600" '
                            f'style="'
                            f'border:none; '
                            f'width:100%;" '
                            f'loading="lazy">'
                            f'</iframe>'
                        ),
                        "</div>",
                        "",
                    ]
                )

            else:

                psf_lines.extend(
                    [
                        "No lateral PSF plot is available.",
                        "",
                    ]
                )


            # Close lateral column
            psf_lines.extend(
                [
                    ":::",
                    "",
                ]
            )


            # ======================================
            # RIGHT COLUMN
            # Axial PSF Z
            # ======================================

            psf_lines.extend(
                [
                    (
                        "::: "
                        "{.g-col-12 "
                        ".g-col-md-6 "
                        ".border "
                        ".rounded "
                        ".p-3}"
                    ),
                    "",
                    "#### Axial PSF (Z)",
                    "",
                ]
            )


            if z_plot is not None:

                z_plot_path = (
                    "../../outputs/"
                    "PSF_Measurements/"
                    f"{microscope}/"
                    "plots/"
                    f"{z_plot.name}"
                )

                psf_lines.extend(
                    [
                        '<div class="plotly-dashboard">',
                        (
                            f'<iframe '
                            f'src="{z_plot_path}" '
                            f'width="100%" '
                            f'height="600" '
                            f'style="'
                            f'border:none; '
                            f'width:100%;" '
                            f'loading="lazy">'
                            f'</iframe>'
                        ),
                        "</div>",
                        "",
                    ]
                )

            else:

                psf_lines.extend(
                    [
                        "No axial PSF plot is available.",
                        "",
                    ]
                )


            # Close axial column
            psf_lines.extend(
                [
                    ":::",
                    "",
                ]
            )


            # Close grid
            psf_lines.extend(
                [
                    ":::",
                    "",
                ]
            )


    else:

        psf_lines.extend(
            [
                (
                    "No PSF plots are "
                    "currently available."
                ),
                "",
            ]
        )


    # ----------------------------------------------
    # PSF data download
    # ----------------------------------------------

    psf_lines.extend(
        [
            (
                "## Download Data "
                "{.unnumbered .unlisted}"
            ),
            "",
        ]
    )


    if combined_psf_csv.exists():

        csv_link = (
            "../../outputs/"
            "PSF_Measurements/"
            f"{microscope}/"
            "combined_PSF_data.csv"
        )

        psf_lines.extend(
            [
                (
                    f"[Download {title} "
                    f"PSF data]"
                    f"({csv_link})"
                    "{.btn .btn-primary}"
                ),
                "",
            ]
        )

    else:

        psf_lines.extend(
            [
                (
                    "The combined PSF data "
                    "file is not available."
                ),
                "",
            ]
        )


    # ----------------------------------------------
    # Write PSF microscope page
    # ----------------------------------------------

    psf_page_path = (
        PSF_PAGE_DIR
        / f"{microscope}.qmd"
    )

    psf_page_path.write_text(
        "\n".join(
            psf_lines
        )
        + "\n",
        encoding="utf-8",
    )


    print(
        "Generated PSF page: "
        f"{psf_page_path.name}"
    )


print(
    "Generated "
    f"{len(psf_microscopes)} "
    "PSF microscope pages."
)


# ==================================================
# FINISHED
# ==================================================

print(
    ""
)

print(
    "----------------------------------------"
)

print(
    "Page generation complete"
)

print(
    "----------------------------------------"
)

print(
    "Laser Power pages: "
    f"{LASER_PAGE_DIR}"
)

print(
    "PSF pages: "
    f"{PSF_PAGE_DIR}"
)