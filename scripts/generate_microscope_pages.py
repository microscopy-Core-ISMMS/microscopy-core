"""Generate Quarto navigation and microscope pages from available data."""

import csv
import re
from datetime import datetime
from pathlib import Path

# ==================================================
# PROJECT DIRECTORIES
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_DIR / "data"

OUTPUT_DIR = PROJECT_DIR / "outputs"


# --------------------------------------------------
# Measurement data directories
# --------------------------------------------------

LASER_DATA_DIR = DATA_DIR / "Laser_Power_Measurements"

PSF_DATA_DIR = DATA_DIR / "PSF_Measurements"


# --------------------------------------------------
# Website page directories
# --------------------------------------------------

MICROSCOPE_PAGE_DIR = PROJECT_DIR / "microscopes"

LASER_PAGE_DIR = MICROSCOPE_PAGE_DIR / "laser_power"

PSF_PAGE_DIR = MICROSCOPE_PAGE_DIR / "psf"


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

        return int(match.group(1))

    return 99999


def wavelength_color(wavelength: int) -> str:
    """Return a legible accent color for a laser wavelength."""

    palette = {
        405: "#7c5ce7",
        445: "#536ee8",
        458: "#3577df",
        488: "#008eac",
        514: "#13856f",
        561: "#b06e00",
        594: "#d15b28",
        633: "#d63d51",
        639: "#cf354d",
        640: "#cf354d",
        685: "#a33a62",
        730: "#73507e",
        750: "#684a75",
        785: "#5a4569",
        790: "#574366",
    }

    return palette.get(wavelength, "#4f6670")


def objective_color(name: str) -> str:
    """Return a stable accent color for a microscope objective."""

    match = re.search(r"(\d+)", name)
    magnification = int(match.group(1)) if match else 0
    palette = {
        10: "#7c5ce7",
        20: "#3577df",
        25: "#008eac",
        40: "#0787b5",
        60: "#13856f",
        63: "#13856f",
        100: "#b06e00",
    }

    return palette.get(magnification, "#4f6670")


def optional_float(value):
    """Convert a generated CSV value to float when available."""

    if value in (None, "", "nan", "NaN"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_laser_summary(output_dir: Path) -> list[dict]:
    """Read the per-wavelength operational QA summary."""

    summary_path = output_dir / "laser_power_summary.csv"

    if not summary_path.exists():
        return []

    rows = []

    with summary_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                wavelength = int(row["wavelength_nm"])
            except (KeyError, TypeError, ValueError):
                continue

            rows.append(
                {
                    **row,
                    "wavelength_nm": wavelength,
                    "latest_power_mW": optional_float(row.get("latest_power_mW")),
                    "previous_power_mW": optional_float(row.get("previous_power_mW")),
                    "change_percent": optional_float(row.get("change_percent")),
                    "reference_maximum_mW": optional_float(
                        row.get("reference_maximum_mW")
                    ),
                    "out_of_spec_threshold_mW": optional_float(
                        row.get("out_of_spec_threshold_mW")
                    ),
                    "percent_of_reference": optional_float(
                        row.get("percent_of_reference")
                    ),
                    "measurement_count": int(float(row.get("measurement_count", 0))),
                }
            )

    return sorted(rows, key=lambda row: row["wavelength_nm"])


def format_month(value: str | None) -> str:
    """Format an ISO measurement month for display."""

    if not value:
        return "Not available"

    try:
        return datetime.strptime(value, "%Y-%m").strftime("%b %Y")
    except ValueError:
        return value


def format_power(value) -> str:
    """Format power values without hiding small measurements."""

    if value is None:
        return "—"

    if abs(value) < 1:
        return f"{value:.3f} mW"

    return f"{value:.2f} mW"


def format_length(value) -> str:
    """Format PSF values in nanometers for dashboard summaries."""

    if value is None:
        return "—"

    return f"{value:,.0f} nm"


def status_class(status: str | None) -> str:
    """Map QA status text to a visual state class."""

    if status == "Review":
        return "status-review"

    if status == "Within spec":
        return "status-pass"

    return "status-neutral"


def objective_label(name: str) -> str:
    """Format compact objective tokens for dashboard display."""

    match = re.fullmatch(r"(\d+)x([ow]?)", name.lower())

    if not match:
        return name.upper()

    suffix = {
        "o": " oil",
        "w": " water",
        "": "",
    }[match.group(2)]

    return f"{match.group(1)}×{suffix}"


def average_values(rows: list[dict], column: str) -> float | None:
    """Average a numeric column from generated PSF records."""

    values = [
        value for row in rows if (value := optional_float(row.get(column))) is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


def read_psf_summary(combined_csv: Path) -> list[dict]:
    """Build one dashboard summary row per microscope objective."""

    if not combined_csv.exists():
        return []

    grouped: dict[str, list[dict]] = {}

    with combined_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            objective = row.get("Objective", "").strip().lower()
            date = row.get("Date", "").strip()

            if not objective or not date:
                continue

            grouped.setdefault(objective, []).append(row)

    summaries = []

    for objective, rows in grouped.items():
        dates = sorted({row["Date"] for row in rows if row.get("Date")})

        if not dates:
            continue

        latest_date = dates[-1]
        latest_rows = [row for row in rows if row.get("Date") == latest_date]
        previous_rows = []

        if len(dates) > 1:
            previous_rows = [row for row in rows if row.get("Date") == dates[-2]]

        latest_xy = average_values(latest_rows, "AvgXY")
        latest_z = average_values(latest_rows, "MaxZ")
        previous_xy = average_values(previous_rows, "AvgXY")
        xy_change_percent = None

        if latest_xy is not None and previous_xy not in (None, 0):
            xy_change_percent = ((latest_xy / previous_xy) - 1) * 100

        summaries.append(
            {
                "objective": objective,
                "latest_date": latest_date[:7],
                "latest_xy_nm": latest_xy * 1000 if latest_xy is not None else None,
                "latest_z_nm": latest_z * 1000 if latest_z is not None else None,
                "xy_change_percent": xy_change_percent,
                "channel_count": len(
                    {row.get("Channel") for row in latest_rows if row.get("Channel")}
                ),
                "measurement_count": len(dates),
                "record_count": len(rows),
            }
        )

    return sorted(
        summaries,
        key=lambda row: objective_sort_key(row["objective"]),
    )


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
            int(match.group(1)),
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

        print("Warning: data directory " f"does not exist: " f"{data_folder}")

        return []

    return sorted(
        [
            folder
            for folder in data_folder.iterdir()
            if (folder.is_dir() and not folder.name.startswith("."))
        ],
        key=lambda folder: folder.name.lower(),
    )


# ==================================================
# DETECT MICROSCOPES
# ==================================================

laser_microscopes = detect_microscopes(LASER_DATA_DIR)

psf_microscopes = detect_microscopes(PSF_DATA_DIR)


print(
    "Laser Power microscopes:",
    ", ".join(folder.name for folder in laser_microscopes) or "None",
)

print(
    "PSF microscopes:",
    ", ".join(folder.name for folder in psf_microscopes) or "None",
)


# ==================================================
# GENERATE NAVBAR
# ==================================================

NAVBAR_FILE = PROJECT_DIR / "_navbar.yml"


navbar_lines = [
    "website:",
    "  navbar:",
    "    left:",
    "      - href: index.html",
    '        text: "Home"',
    ("      - text: " '"Quality Assessment - ' 'Confocal Microscopes"'),
    "        menu:",
    ("          - text: " '"Introduction"'),
    ("            href: " "microscopes/index.html"),
    ("          - text: " '"Laser Power Measurements"'),
    ("            href: " "microscopes/" "laser_power/index.html"),
    ("          - text: " '"PSF Measurements"'),
    ("            href: " "microscopes/" "psf/index.html"),
    ("      - text: " '"Image Analysis"'),
    "        menu:",
    ("          - text: " '"Introduction"'),
    ("            href: " "image_analysis/index.html"),
    ("          - text: " '"FIJI/ImageJ Workflows"'),
    ("            href: " "image_analysis/" "fiji_imagej/index.html"),
]


NAVBAR_FILE.write_text(
    "\n".join(navbar_lines) + "\n",
    encoding="utf-8",
)


print("")

print("Generated navbar:")

print("  Laser Power Measurements: " f"{len(laser_microscopes)} " "microscopes")

print("  PSF Measurements: " f"{len(psf_microscopes)} " "microscopes")


# ==================================================
# LASER POWER MEASUREMENTS
# ==================================================


# --------------------------------------------------
# Laser Power landing page
# --------------------------------------------------

laser_index_lines = [
    "---",
    'title: "Laser Power Measurements"',
    "toc: false",
    "format:",
    "  html:",
    "    page-layout: full",
    "    grid:",
    "      body-width: 1180px",
    "      gutter-width: 2rem",
    "---",
    "",
    "::: {.laser-introduction}",
    "## Introduction",
    "",
    (
        "Quality assurance of illumination power stability is critical because "
        "fluorescence intensity measurements depend directly on the excitation "
        "power delivered to the sample. Under standard imaging conditions, the "
        "emitted fluorescence signal is proportional to the fluorophore "
        "concentration and the excitation light intensity. Any fluctuation in "
        "illumination power can therefore alter measured signal levels, "
        "potentially leading to incorrect conclusions about changes in "
        "fluorophore abundance, molecular interactions, or cellular dynamics. "
        "Ensuring stable and reproducible excitation conditions is essential "
        "for reliable quantitative fluorescence imaging."
    ),
    "",
    (
        "Over time, illumination sources such as lasers or LEDs can exhibit "
        "fluctuations due to component aging, temperature changes, electronic "
        "instability, or optical misalignment within the light path. These "
        "variations may occur over multiple time scales and can introduce "
        "unwanted variability between images acquired during a single "
        "experiment or across different experimental sessions. Routine "
        "monitoring of illumination power stability allows early detection of "
        "such fluctuations and helps ensure that excitation conditions remain "
        "consistent and reproducible."
    ),
    ":::",
    "",
    "## Microscope dashboards",
    "",
    '<div class="microscope-grid">',
]


for microscope_dir in laser_microscopes:

    microscope = microscope_dir.name

    title = display_name(microscope)

    summary = read_laser_summary(OUTPUT_DIR / microscope)
    review_count = sum(row.get("status") == "Review" for row in summary)
    latest_month = max(
        (row.get("latest_month", "") for row in summary),
        default="",
    )

    if review_count:
        state = f"{review_count} channel{'s' if review_count != 1 else ''} to review"
        state_class = "status-review"
    elif summary:
        state = "All channels within spec"
        state_class = "status-pass"
    else:
        state = "Analysis pending"
        state_class = "status-neutral"

    laser_index_lines.extend(
        [
            f'<a class="microscope-card" href="{microscope}.html">',
            '<div class="microscope-card-top">',
            f"<h3>{title}</h3>",
            '<span aria-hidden="true" class="card-arrow">→</span>',
            "</div>",
            f'<span class="status-pill {state_class}">{state}</span>',
            '<div class="microscope-card-meta">',
            f"<span><strong>{len(summary)}</strong> wavelengths</span>",
            f"<span>Latest: {format_month(latest_month)}</span>",
            "</div>",
            "</a>",
        ]
    )


laser_index_lines.extend(
    [
        "</div>",
        "",
        "::: {.qa-method-note}",
        "#### How status is determined",
        "",
        (
            "A channel is flagged for review when its latest measured maximum "
            "falls below 70% of the configured reference measurement. Use the "
            "interactive trend to assess changes over time before making an "
            "experimental decision."
        ),
        ":::",
    ]
)


(LASER_PAGE_DIR / "index.qmd").write_text(
    "\n".join(laser_index_lines) + "\n",
    encoding="utf-8",
)


print("Generated Laser Power " "landing page.")


# --------------------------------------------------
# Create one Laser Power page per microscope
# --------------------------------------------------

for microscope_dir in laser_microscopes:

    microscope = microscope_dir.name

    title = display_name(microscope)

    # ----------------------------------------------
    # Output locations
    # ----------------------------------------------

    microscope_output = OUTPUT_DIR / microscope

    plot_dir = microscope_output / "plots"

    excel_path = microscope_output / "combined_power_data.xlsx"

    summary_csv_path = microscope_output / "laser_power_summary.csv"

    summary_rows = read_laser_summary(microscope_output)

    summary_by_wavelength = {row["wavelength_nm"]: row for row in summary_rows}

    # ----------------------------------------------
    # Find interactive calibration plots
    # ----------------------------------------------

    calibration_plots = []

    if plot_dir.exists():

        calibration_plots = sorted(
            [
                plot
                for plot in plot_dir.glob("laser_power_*nm.html")
                if not plot.name.startswith("laser_power_max_")
            ],
            key=wavelength_from_name,
        )

    # ----------------------------------------------
    # Find interactive maximum-power plots
    # ----------------------------------------------

    maximum_plots = []

    if plot_dir.exists():

        maximum_plots = sorted(
            plot_dir.glob("laser_power_max_*nm.html"),
            key=wavelength_from_name,
        )

    # ----------------------------------------------
    # Organize plots by wavelength
    # ----------------------------------------------

    calibration_by_wavelength = {
        wavelength_from_name(plot): plot for plot in calibration_plots
    }

    maximum_by_wavelength = {wavelength_from_name(plot): plot for plot in maximum_plots}

    wavelengths = sorted(
        set(calibration_by_wavelength.keys())
        | set(maximum_by_wavelength.keys())
        | set(summary_by_wavelength.keys())
    )

    review_count = sum(row.get("status") == "Review" for row in summary_rows)
    latest_month = max(
        (row.get("latest_month", "") for row in summary_rows),
        default="",
    )
    measurement_count = sum(row.get("measurement_count", 0) for row in summary_rows)

    if review_count:
        overall_status = "Review needed"
        overall_class = "status-review"
    elif summary_rows:
        overall_status = "Within spec"
        overall_class = "status-pass"
    else:
        overall_status = "Analysis pending"
        overall_class = "status-neutral"

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
        ("  - text: " '"← Back to Laser Power Measurements"'),
        "    href: index.html",
        "---",
        "",
        '<div class="laser-dashboard-hero">',
        '<div class="laser-dashboard-heading">',
        '<p class="laser-eyebrow">Laser power quality assurance</p>',
        "<h2>Measurement overview</h2>",
        (
            "<p>Review the latest output at a glance, then inspect calibration "
            "and maximum-power history for each wavelength. Review badges mark "
            "readings below 70% of the configured reference.</p>"
        ),
        "</div>",
        f'<span class="status-pill status-large {overall_class}">{overall_status}</span>',
        "</div>",
        "",
        '<div class="laser-kpi-grid">',
        '<div class="laser-kpi">',
        '<span class="kpi-label">Wavelengths monitored</span>',
        f'<strong class="kpi-value">{len(wavelengths)}</strong>',
        "</div>",
        '<div class="laser-kpi">',
        '<span class="kpi-label">Latest measurement</span>',
        f'<strong class="kpi-value kpi-value-text">{format_month(latest_month)}</strong>',
        "</div>",
        '<div class="laser-kpi">',
        '<span class="kpi-label">Measurements on record</span>',
        f'<strong class="kpi-value">{measurement_count}</strong>',
        "</div>",
        '<div class="laser-kpi">',
        '<span class="kpi-label">Channels to review</span>',
        f'<strong class="kpi-value">{review_count}</strong>',
        "</div>",
        "</div>",
        "",
    ]

    if wavelengths:
        lines.extend(
            [
                '<nav class="wavelength-nav" aria-label="Jump to wavelength">',
                '<span class="wavelength-nav-label">Jump to</span>',
            ]
        )

        for wavelength in wavelengths:
            color = wavelength_color(wavelength)
            lines.append(
                f'<a href="#wave-{wavelength}" style="--laser-color: {color}">'
                f'<span class="wavelength-dot"></span>{wavelength} nm</a>'
            )

        lines.extend(["</nav>", ""])

    # ----------------------------------------------
    # Laser Power Dashboard
    # ----------------------------------------------

    if wavelengths:

        for wavelength in wavelengths:

            calibration_plot = calibration_by_wavelength.get(wavelength)

            maximum_plot = maximum_by_wavelength.get(wavelength)

            summary = summary_by_wavelength.get(wavelength)

            color = wavelength_color(wavelength)

            if summary:
                status = summary.get("status", "No baseline")
                state_class = status_class(status)
                change = summary.get("change_percent")

                if change is None:
                    change_text = "No prior reading"
                    change_class = "trend-neutral"
                elif change > 0:
                    change_text = f"+{change:.1f}% vs prior"
                    change_class = "trend-up"
                elif change < 0:
                    change_text = f"{change:.1f}% vs prior"
                    change_class = "trend-down"
                else:
                    change_text = "No change vs prior"
                    change_class = "trend-neutral"

                baseline_text = (
                    f"{format_power(summary.get('reference_maximum_mW'))} · "
                    f"{format_month(summary.get('reference_month'))}"
                )
                threshold_text = format_power(summary.get("out_of_spec_threshold_mW"))
                latest_text = format_power(summary.get("latest_power_mW"))
                latest_date = format_month(summary.get("latest_month"))
            else:
                status = "No summary"
                state_class = "status-neutral"
                change_text = "No prior reading"
                change_class = "trend-neutral"
                baseline_text = "—"
                threshold_text = "—"
                latest_text = "—"
                latest_date = "Not available"

            # ======================================
            # Wavelength heading and grid
            # ======================================

            lines.extend(
                [
                    ("::: {.laser-wave-section " f'style="--laser-color: {color};"}}'),
                    "",
                    f"### {wavelength} nm {{#wave-{wavelength}}}",
                    "",
                    '<div class="wave-summary-row">',
                    '<div class="wave-latest">',
                    '<span class="metric-label">Latest maximum</span>',
                    f'<strong class="metric-value">{latest_text}</strong>',
                    f'<span class="metric-context">{latest_date}</span>',
                    "</div>",
                    '<div class="wave-metric">',
                    '<span class="metric-label">Reference</span>',
                    f"<strong>{baseline_text}</strong>",
                    "</div>",
                    '<div class="wave-metric">',
                    '<span class="metric-label">Review threshold</span>',
                    f"<strong>{threshold_text}</strong>",
                    "</div>",
                    '<div class="wave-status">',
                    f'<span class="status-pill {state_class}">{status}</span>',
                    f'<span class="trend-label {change_class}">{change_text}</span>',
                    "</div>",
                    "</div>",
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
                    ("::: " "{.g-col-12 " ".g-col-md-6 " ".laser-chart-card}"),
                    "",
                    "#### Calibration response",
                    "",
                    '<p class="chart-description">Measured output across the configured laser power range.</p>',
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
                            f"<iframe "
                            f'src="{calibration_plot_path}" '
                            f'width="100%" '
                            f'height="500" '
                            f'title="{title} {wavelength} nm calibration response" '
                            f'style="'
                            f"border:none; "
                            f'width:100%;" '
                            f'loading="lazy">'
                            f"</iframe>"
                        ),
                        "</div>",
                        "",
                    ]
                )

            else:

                lines.extend(
                    [
                        ("No laser-power trend " "plot is available."),
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
                    ("::: " "{.g-col-12 " ".g-col-md-6 " ".laser-chart-card}"),
                    "",
                    "#### Maximum output history",
                    "",
                    '<p class="chart-description">Peak measured power with the reference and review threshold.</p>',
                    "",
                ]
            )

            if maximum_plot is not None:

                maximum_plot_path = (
                    "../../outputs/" f"{microscope}/" "plots/" f"{maximum_plot.name}"
                )

                lines.extend(
                    [
                        '<div class="plotly-dashboard">',
                        (
                            f"<iframe "
                            f'src="{maximum_plot_path}" '
                            f'width="100%" '
                            f'height="500" '
                            f'title="{title} {wavelength} nm maximum output history" '
                            f'style="'
                            f"border:none; "
                            f'width:100%;" '
                            f'loading="lazy">'
                            f"</iframe>"
                        ),
                        "</div>",
                        "",
                    ]
                )

            else:

                lines.extend(
                    [
                        ("No maximum-power " "plot is available."),
                        "",
                    ]
                )

            # Close right column
            lines.extend(
                [
                    ":::",
                    "",
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
                ("No interactive laser-power " "plots are currently available."),
                "",
            ]
        )

    # ----------------------------------------------
    # Excel download
    # ----------------------------------------------

    lines.extend(
        [
            ("## Download Data " "{.unnumbered .unlisted}"),
            "",
        ]
    )

    if excel_path.exists():

        excel_link = "../../outputs/" f"{microscope}/" "combined_power_data.xlsx"

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
                ("The Excel workbook " "is not available."),
                "",
            ]
        )

    if summary_csv_path.exists():

        summary_link = "../../outputs/" f"{microscope}/" "laser_power_summary.csv"

        lines.extend(
            [
                (
                    f"[Download {title} QA summary]"
                    f"({summary_link})"
                    "{.btn .btn-outline-primary}"
                ),
                "",
            ]
        )

    # ----------------------------------------------
    # Write microscope page
    # ----------------------------------------------

    page_path = LASER_PAGE_DIR / f"{microscope}.qmd"

    page_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("Generated Laser Power page: " f"{page_path.name}")


print("Generated " f"{len(laser_microscopes)} " "Laser Power microscope pages.")


# ==================================================
# PSF MEASUREMENTS
# ==================================================


# --------------------------------------------------
# PSF landing page
# --------------------------------------------------

psf_index_lines = [
    "---",
    'title: "Point Spread Function Measurements"',
    "toc: false",
    "format:",
    "  html:",
    "    page-layout: full",
    "    grid:",
    "      body-width: 1180px",
    "      gutter-width: 2rem",
    "---",
    "",
    "::: {.laser-introduction .psf-introduction}",
    "## Introduction",
    "",
    (
        "Quality assurance of axial and lateral resolution, typically assessed "
        "by measuring the point spread function (PSF), verifies whether a "
        "microscope can resolve fine details as expected. Even small deviations "
        "in the PSF can reduce image sharpness, distort structures, and "
        "compromise quantitative measurements."
    ),
    "",
    (
        "Optical components drift, age, or become misaligned over time, causing "
        "gradual loss of resolution. Routine PSF monitoring helps detect these "
        "changes early and supports consistent, reproducible imaging."
    ),
    ":::",
    "",
    "## Microscope dashboards",
    "",
    '<div class="microscope-grid">',
]


for microscope_dir in psf_microscopes:

    microscope = microscope_dir.name

    title = display_name(microscope)

    combined_csv = (
        OUTPUT_DIR / "PSF_Measurements" / microscope / "combined_PSF_data.csv"
    )
    summary = read_psf_summary(combined_csv)
    latest_month = max(
        (row.get("latest_date", "") for row in summary),
        default="",
    )

    psf_index_lines.extend(
        [
            f'<a class="microscope-card" href="{microscope}.html">',
            '<div class="microscope-card-top">',
            f"<h3>{title}</h3>",
            '<span aria-hidden="true" class="card-arrow">→</span>',
            "</div>",
            '<span class="status-pill status-neutral">Measurements available</span>',
            '<div class="microscope-card-meta">',
            f"<span><strong>{len(summary)}</strong> objectives</span>",
            f"<span>Latest: {format_month(latest_month)}</span>",
            "</div>",
            "</a>",
        ]
    )


psf_index_lines.extend(
    [
        "</div>",
        "",
        "::: {.qa-method-note}",
        "#### Reading the PSF dashboards",
        "",
        (
            "Lateral (XY) and axial (Z) values are displayed in nanometers. "
            "Use each objective dashboard to compare channels and follow "
            "resolution measurements across acquisition dates."
        ),
        ":::",
    ]
)


(PSF_PAGE_DIR / "index.qmd").write_text(
    "\n".join(psf_index_lines) + "\n",
    encoding="utf-8",
)


print("Generated PSF landing page.")


# --------------------------------------------------
# Create one PSF page per microscope
# --------------------------------------------------

for microscope_dir in psf_microscopes:

    microscope = microscope_dir.name

    title = display_name(microscope)

    # ----------------------------------------------
    # PSF output directories
    # ----------------------------------------------

    psf_output_dir = OUTPUT_DIR / "PSF_Measurements" / microscope

    psf_plot_dir = psf_output_dir / "plots"

    combined_psf_csv = psf_output_dir / "combined_PSF_data.csv"

    summary_rows = read_psf_summary(combined_psf_csv)

    summary_by_objective = {row["objective"]: row for row in summary_rows}

    # ----------------------------------------------
    # Find XY Plotly plots
    # ----------------------------------------------

    xy_plots = []

    if psf_plot_dir.exists():

        xy_plots = sorted(
            psf_plot_dir.glob("PSF_XY_*.html"),
            key=lambda path: path.name.lower(),
        )

    # ----------------------------------------------
    # Find Z Plotly plots
    # ----------------------------------------------

    z_plots = []

    if psf_plot_dir.exists():

        z_plots = sorted(
            psf_plot_dir.glob("PSF_Z_*.html"),
            key=lambda path: path.name.lower(),
        )

    # ----------------------------------------------
    # Organize XY plots by objective
    # ----------------------------------------------

    xy_by_objective = {}

    for plot in xy_plots:

        objective = plot.stem.replace(
            "PSF_XY_",
            "",
        )

        xy_by_objective[objective] = plot

    # ----------------------------------------------
    # Organize Z plots by objective
    # ----------------------------------------------

    z_by_objective = {}

    for plot in z_plots:

        objective = plot.stem.replace(
            "PSF_Z_",
            "",
        )

        z_by_objective[objective] = plot

    # ----------------------------------------------
    # Determine all objectives
    # ----------------------------------------------

    objectives = sorted(
        set(xy_by_objective.keys())
        | set(z_by_objective.keys())
        | set(summary_by_objective.keys()),
        key=objective_sort_key,
    )

    latest_month = max(
        (row.get("latest_date", "") for row in summary_rows),
        default="",
    )
    measurement_count = sum(row.get("measurement_count", 0) for row in summary_rows)
    record_count = sum(row.get("record_count", 0) for row in summary_rows)

    if summary_rows:
        overall_status = "Measurements available"
        overall_class = "status-neutral"
    else:
        overall_status = "Analysis pending"
        overall_class = "status-neutral"

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
        ("  - text: " '"← Back to PSF Measurements"'),
        "    href: index.html",
        "---",
        "",
        '<div class="laser-dashboard-hero psf-dashboard-hero">',
        '<div class="laser-dashboard-heading">',
        '<p class="laser-eyebrow">Resolution quality assurance</p>',
        "<h2>Measurement overview</h2>",
        (
            "<p>Review the latest lateral and axial resolution measurements at "
            "a glance, then inspect the history for each objective and channel.</p>"
        ),
        "</div>",
        f'<span class="status-pill status-large {overall_class}">{overall_status}</span>',
        "</div>",
        "",
        '<div class="laser-kpi-grid psf-kpi-grid">',
        '<div class="laser-kpi">',
        '<span class="kpi-label">Objectives monitored</span>',
        f'<strong class="kpi-value">{len(objectives)}</strong>',
        "</div>",
        '<div class="laser-kpi">',
        '<span class="kpi-label">Latest measurement</span>',
        f'<strong class="kpi-value kpi-value-text">{format_month(latest_month)}</strong>',
        "</div>",
        '<div class="laser-kpi">',
        '<span class="kpi-label">Measurement sessions</span>',
        f'<strong class="kpi-value">{measurement_count}</strong>',
        "</div>",
        '<div class="laser-kpi">',
        '<span class="kpi-label">Channel records</span>',
        f'<strong class="kpi-value">{record_count}</strong>',
        "</div>",
        "</div>",
        "",
    ]

    if objectives:
        psf_lines.extend(
            [
                '<nav class="wavelength-nav objective-nav" aria-label="Jump to objective">',
                '<span class="wavelength-nav-label">Jump to</span>',
            ]
        )

        for objective in objectives:
            color = objective_color(objective)
            label = objective_label(objective)
            psf_lines.append(
                f'<a href="#objective-{objective}" style="--laser-color: {color}">'
                f'<span class="wavelength-dot"></span>{label}</a>'
            )

        psf_lines.extend(["</nav>", ""])

    # ----------------------------------------------
    # PSF Dashboard
    # ----------------------------------------------

    if objectives:

        for objective in objectives:

            display_objective = objective_label(objective)

            xy_plot = xy_by_objective.get(objective)

            z_plot = z_by_objective.get(objective)

            summary = summary_by_objective.get(objective)

            color = objective_color(objective)

            if summary:
                latest_xy_text = format_length(summary.get("latest_xy_nm"))
                latest_z_text = format_length(summary.get("latest_z_nm"))
                latest_date = format_month(summary.get("latest_date"))
                channel_count = summary.get("channel_count", 0)
                channel_text = (
                    f"{channel_count} channel{'s' if channel_count != 1 else ''}"
                )
                session_count = summary.get("measurement_count", 0)
                session_text = (
                    f"{session_count} session{'s' if session_count != 1 else ''}"
                )
                change = summary.get("xy_change_percent")

                if change is None:
                    change_text = "No prior measurement"
                    change_class = "trend-neutral"
                elif change < 0:
                    change_text = f"{abs(change):.1f}% narrower vs prior"
                    change_class = "trend-up"
                elif change > 0:
                    change_text = f"{change:.1f}% wider vs prior"
                    change_class = "trend-down"
                else:
                    change_text = "No change vs prior"
                    change_class = "trend-neutral"
            else:
                latest_xy_text = "—"
                latest_z_text = "—"
                latest_date = "Not available"
                channel_text = "—"
                session_text = "No sessions"
                change_text = "No prior measurement"
                change_class = "trend-neutral"

            # ======================================
            # Objective heading
            # ======================================

            psf_lines.extend(
                [
                    (
                        "::: {.laser-wave-section .psf-objective-section "
                        f'style="--laser-color: {color};"}}'
                    ),
                    "",
                    f"### {display_objective} objective {{#objective-{objective}}}",
                    "",
                    '<div class="wave-summary-row psf-summary-row">',
                    '<div class="wave-latest">',
                    '<span class="metric-label">Latest lateral (XY)</span>',
                    f'<strong class="metric-value">{latest_xy_text}</strong>',
                    f'<span class="metric-context">{latest_date}</span>',
                    "</div>",
                    '<div class="wave-metric">',
                    '<span class="metric-label">Latest axial (Z)</span>',
                    f"<strong>{latest_z_text}</strong>",
                    "</div>",
                    '<div class="wave-metric">',
                    '<span class="metric-label">Channels at latest</span>',
                    f"<strong>{channel_text}</strong>",
                    "</div>",
                    '<div class="wave-status">',
                    f'<span class="status-pill status-neutral">{session_text}</span>',
                    f'<span class="trend-label {change_class}">{change_text}</span>',
                    "</div>",
                    "</div>",
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
                    ("::: " "{.g-col-12 " ".g-col-md-6 " ".laser-chart-card}"),
                    "",
                    "#### Lateral PSF (XY)",
                    "",
                    '<p class="chart-description">Lateral resolution history by fluorescence channel.</p>',
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
                            f"<iframe "
                            f'src="{xy_plot_path}" '
                            f'width="100%" '
                            f'height="500" '
                            f'title="{title} {display_objective} lateral PSF history" '
                            f'style="'
                            f"border:none; "
                            f'width:100%;" '
                            f'loading="lazy">'
                            f"</iframe>"
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
                    ("::: " "{.g-col-12 " ".g-col-md-6 " ".laser-chart-card}"),
                    "",
                    "#### Axial PSF (Z)",
                    "",
                    '<p class="chart-description">Axial resolution history by fluorescence channel.</p>',
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
                            f"<iframe "
                            f'src="{z_plot_path}" '
                            f'width="100%" '
                            f'height="500" '
                            f'title="{title} {display_objective} axial PSF history" '
                            f'style="'
                            f"border:none; "
                            f'width:100%;" '
                            f'loading="lazy">'
                            f"</iframe>"
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

            # Close axial column and chart grid
            psf_lines.extend(
                [
                    ":::",
                    "",
                    ":::",
                    "",
                ]
            )

            # Close objective section
            psf_lines.extend(
                [
                    ":::",
                    "",
                ]
            )

    else:

        psf_lines.extend(
            [
                ("No PSF plots are " "currently available."),
                "",
            ]
        )

    # ----------------------------------------------
    # PSF data download
    # ----------------------------------------------

    psf_lines.extend(
        [
            ("## Download Data " "{.unnumbered .unlisted}"),
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
                ("The combined PSF data " "file is not available."),
                "",
            ]
        )

    # ----------------------------------------------
    # Write PSF microscope page
    # ----------------------------------------------

    psf_page_path = PSF_PAGE_DIR / f"{microscope}.qmd"

    psf_page_path.write_text(
        "\n".join(psf_lines) + "\n",
        encoding="utf-8",
    )

    print("Generated PSF page: " f"{psf_page_path.name}")


print("Generated " f"{len(psf_microscopes)} " "PSF microscope pages.")


# ==================================================
# FINISHED
# ==================================================

print("")

print("----------------------------------------")

print("Page generation complete")

print("----------------------------------------")

print("Laser Power pages: " f"{LASER_PAGE_DIR}")

print("PSF pages: " f"{PSF_PAGE_DIR}")
