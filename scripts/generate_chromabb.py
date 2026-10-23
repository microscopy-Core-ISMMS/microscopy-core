"""Generate chromatic-aberration tables and interactive plots."""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# Project directories
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]

CHROMATIC_DATA_DIR = PROJECT_DIR / "data" / "Chromatic_Aberration_Measurements"

CHROMATIC_OUTPUT_DIR = PROJECT_DIR / "outputs" / "Chromatic_Aberration_Measurements"

MICROMETERS_TO_NANOMETERS = 1_000

WAVELENGTH_COLORS = {
    405: "blue",
    488: "green",
    561: "orange",
    639: "red",
}

FALLBACK_COLORS = [
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
]


# --------------------------------------------------
# Input discovery and parsing
# --------------------------------------------------


def detect_microscopes(folder: Path) -> list[Path]:
    """Return microscope folders that contain Huygens shift files."""

    if not folder.exists():
        print(f"Warning: chromatic-aberration data directory does not exist: {folder}")
        return []

    return sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and any(path.glob("*.hgsc"))
        ],
        key=lambda path: path.name.lower(),
    )


def parse_filename(file_path: Path) -> tuple[datetime, str]:
    """Extract the measurement month and objective from an HGSC filename."""

    match = re.fullmatch(
        r"(?P<month>\d{1,2})-(?P<year>\d{2})_" r"(?P<objective>\d+x[wo]?)\.hgsc",
        file_path.name,
        flags=re.IGNORECASE,
    )

    if match is None:
        raise ValueError(
            "filename must use MM-YY_OBJECTIVE.hgsc, "
            f"for example 10-26_40xW.hgsc: {file_path.name}"
        )

    date = datetime(
        year=2000 + int(match.group("year")),
        month=int(match.group("month")),
        day=1,
    )
    objective = match.group("objective").lower()

    return date, objective


def parse_hgsc(file_path: Path) -> pd.DataFrame:
    """Parse channel shift vectors from one Huygens HGSC template."""

    date, objective = parse_filename(file_path)
    content = file_path.read_text(encoding="utf-8-sig")
    records = []

    shift_pattern = re.compile(
        r"^shift:(?P<shift>\d+)\s+\{(?P<body>.+)\}\s*$",
        flags=re.MULTILINE,
    )

    for shift_match in shift_pattern.finditer(content):
        body = shift_match.group("body")

        vector_match = re.search(r"\bvector\s+\{([^}]+)\}", body)
        channel_match = re.search(r"\bchannel\s+(\d+)", body)
        reference_match = re.search(r"\breference\s+(\d+)", body)
        excitation_match = re.search(r"\blambdaEx\s+(\d+(?:\.\d+)?)", body)
        emission_match = re.search(r"\blambdaEm\s+(\d+(?:\.\d+)?)", body)

        required_matches = {
            "vector": vector_match,
            "channel": channel_match,
            "reference": reference_match,
            "lambdaEx": excitation_match,
            "lambdaEm": emission_match,
        }
        missing_fields = [
            name
            for name, field_match in required_matches.items()
            if field_match is None
        ]

        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"shift:{shift_match.group('shift')} is missing: {missing}"
            )

        vector = [float(value) for value in vector_match.group(1).split()]

        if len(vector) != 3:
            raise ValueError(
                f"shift:{shift_match.group('shift')} must contain an X/Y/Z vector"
            )

        shift_x, shift_y, shift_z = vector

        records.append(
            {
                "Date": date,
                "Objective": objective,
                "Channel": int(channel_match.group(1)) + 1,
                "ExcitationWavelength": float(excitation_match.group(1)),
                "EmissionWavelength": float(emission_match.group(1)),
                "Reference": bool(int(reference_match.group(1))),
                "ShiftX": shift_x,
                "ShiftY": shift_y,
                "ShiftZ": shift_z,
                "EuclideanDistanceXY": float((shift_x**2 + shift_y**2) ** 0.5),
                "EuclideanDistanceXYZ": float(
                    (shift_x**2 + shift_y**2 + shift_z**2) ** 0.5
                ),
                "SourceFile": file_path.name,
            }
        )

    if not records:
        raise ValueError("no shift records were found")

    return pd.DataFrame(records)


# --------------------------------------------------
# Plot helpers
# --------------------------------------------------


def format_wavelength(wavelength: float) -> str:
    """Format a wavelength without an unnecessary decimal."""

    if wavelength.is_integer():
        return str(int(wavelength))

    return f"{wavelength:g}"


def get_channel_colors(microscope: str) -> dict[int, str]:
    """Return channel colors in the manufacturer's acquisition order."""

    microscope_lower = microscope.lower()

    if "leica" in microscope_lower:
        return {
            1: "blue",
            2: "green",
            3: "orange",
            4: "red",
        }

    if "zeiss" in microscope_lower or "lsm" in microscope_lower:
        return {
            1: "red",
            2: "orange",
            3: "green",
            4: "blue",
        }

    return {}


def get_channel_style(
    channel_data: pd.DataFrame,
    microscope: str,
) -> tuple[str, str]:
    """Return a stable legend label and color for one channel."""

    first_row = channel_data.iloc[0]
    channel = int(first_row["Channel"])
    excitation = float(first_row["ExcitationWavelength"])
    wavelength_label = format_wavelength(excitation)
    label = f"CH{channel} ({wavelength_label} nm)"

    if bool(first_row["Reference"]):
        label += " – reference"

    manufacturer_colors = get_channel_colors(microscope)
    color = manufacturer_colors.get(
        channel,
        WAVELENGTH_COLORS.get(
            int(round(excitation)),
            FALLBACK_COLORS[(channel - 1) % len(FALLBACK_COLORS)],
        ),
    )

    return label, color


def get_plot_date_range(dataframe: pd.DataFrame) -> list[pd.Timestamp]:
    """Return padded endpoints for a time-series plot."""

    dates = dataframe["Date"].dropna()
    padding = pd.Timedelta(days=15)

    return [dates.min() - padding, dates.max() + padding]


def apply_plot_layout(
    figure: go.Figure,
    title: str,
    yaxis_title: str,
    date_range: list[pd.Timestamp],
) -> None:
    """Apply the shared PSF-style layout to a chromatic-shift plot."""

    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=yaxis_title,
        legend_title="Channel",
        template="plotly_white",
        hovermode="x unified",
        height=500,
        margin=dict(
            l=70,
            r=30,
            t=70,
            b=70,
        ),
    )
    figure.update_xaxes(
        showgrid=True,
        tickformat="%b %Y",
        range=date_range,
    )
    figure.update_yaxes(
        showgrid=True,
        zeroline=True,
        zerolinecolor="#666",
        zerolinewidth=1,
    )


def write_plot(figure: go.Figure, output_path: Path) -> Path:
    """Write one responsive Plotly figure to HTML."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(
        output_path,
        include_plotlyjs="cdn",
        full_html=True,
        config={
            "responsive": True,
            "displaylogo": False,
        },
    )

    return output_path


def plot_chromatic_metric(
    dataframe: pd.DataFrame,
    objective: str,
    output_folder: Path,
    microscope: str,
    metric: str,
) -> Path | None:
    """Plot one shift component or a Euclidean distance metric."""

    plot_metrics = {
        "X": {
            "column": "ShiftX",
            "title": "Chromatic Aberration X",
            "yaxis": "Signed shift X (nm)",
            "hover": "Shift X",
            "filename": "Chromatic_Shift_X",
        },
        "Y": {
            "column": "ShiftY",
            "title": "Chromatic Aberration Y",
            "yaxis": "Signed shift Y (nm)",
            "hover": "Shift Y",
            "filename": "Chromatic_Shift_Y",
        },
        "Z": {
            "column": "ShiftZ",
            "title": "Chromatic Aberration Z",
            "yaxis": "Signed shift Z (nm)",
            "hover": "Shift Z",
            "filename": "Chromatic_Shift_Z",
        },
        "XY": {
            "column": "EuclideanDistanceXY",
            "title": "Chromatic Aberration Lateral Distance",
            "yaxis": "Lateral Euclidean distance XY (nm)",
            "hover": "Lateral distance",
            "filename": "Chromatic_Distance_XY",
        },
        "XYZ": {
            "column": "EuclideanDistanceXYZ",
            "title": "Chromatic Aberration 3D Distance",
            "yaxis": "Euclidean distance XYZ (nm)",
            "hover": "3D distance",
            "filename": "Chromatic_Distance_XYZ",
        },
    }

    if metric not in plot_metrics:
        raise ValueError(f"unsupported chromatic-aberration metric: {metric}")

    config = plot_metrics[metric]
    value_column = config["column"]
    plot_data = dataframe[
        dataframe["Date"].notna() & dataframe[value_column].notna()
    ].copy()

    if plot_data.empty:
        return None

    figure = go.Figure()

    for channel in sorted(plot_data["Channel"].unique()):
        channel_data = plot_data[plot_data["Channel"] == channel].sort_values("Date")
        label, color = get_channel_style(channel_data, microscope)
        shift_nanometers = channel_data[value_column] * MICROMETERS_TO_NANOMETERS

        figure.add_trace(
            go.Scatter(
                x=channel_data["Date"],
                y=shift_nanometers,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2),
                marker=dict(size=8),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%b %Y}<br>"
                    f"{config['hover']}: %{{y:.0f}} nm"
                    "<extra></extra>"
                ),
            )
        )

    apply_plot_layout(
        figure,
        title=f"{config['title']} - Objective {objective.upper()}",
        yaxis_title=config["yaxis"],
        date_range=get_plot_date_range(plot_data),
    )

    return write_plot(
        figure,
        output_folder / f"{config['filename']}_{objective}.html",
    )


# --------------------------------------------------
# Analysis workflow
# --------------------------------------------------


def run_chromatic_analysis(
    microscope_dir: Path,
    output_dir: Path,
) -> dict | None:
    """Parse HGSC files and generate plots for one microscope."""

    microscope = microscope_dir.name
    hgsc_files = sorted(microscope_dir.glob("*.hgsc"))

    print("\n----------------------------------------")
    print(f"Processing chromatic aberration: {microscope}")
    print("----------------------------------------")

    if not hgsc_files:
        print(f"No HGSC files found for {microscope}.")
        return None

    print(f"Found {len(hgsc_files)} HGSC file(s).")

    dataframes = []

    for file_path in hgsc_files:
        try:
            dataframes.append(parse_hgsc(file_path))
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"Skipping unreadable file: {file_path.name}")
            print(f"  Error: {exc}")

    if not dataframes:
        print("No readable chromatic-aberration data found.")
        return None

    combined_df = pd.concat(dataframes, ignore_index=True)
    combined_df["Date"] = pd.to_datetime(combined_df["Date"], errors="coerce")
    combined_df = combined_df.sort_values(["Objective", "Date", "Channel"]).reset_index(
        drop=True
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    combined_csv_path = output_dir / "combined_chromatic_aberration_data.csv"
    combined_df.to_csv(combined_csv_path, index=False)

    print("Saved combined chromatic-aberration data:")
    print(f"  {combined_csv_path}")

    plot_folder = output_dir / "plots"
    plot_folder.mkdir(parents=True, exist_ok=True)

    for old_plot in plot_folder.glob("Chromatic_*.html"):
        old_plot.unlink()

    generated_plots = []
    objectives = sorted(combined_df["Objective"].dropna().unique())

    print(
        "Objectives:",
        ", ".join(objective.upper() for objective in objectives) or "None",
    )

    for objective in objectives:
        objective_data = combined_df[combined_df["Objective"] == objective].copy()

        # Keep the individual component plot support available for future use.
        # Re-enable it by uncommenting "*_component_metrics" below.
        _component_metrics = ("X", "Y", "Z")
        enabled_metrics = (
            # *_component_metrics,
            "XY",
            "XYZ",
        )
        metric_plots = [
            plot_chromatic_metric(
                objective_data,
                objective,
                plot_folder,
                microscope,
                metric,
            )
            for metric in enabled_metrics
        ]

        for plot_path in metric_plots:
            if plot_path is not None:
                generated_plots.append(plot_path)
                print(f"Saved: {plot_path.name}")

    return {
        "microscope": microscope,
        "data": combined_df,
        "plots": generated_plots,
        "combined_csv": combined_csv_path,
    }


def main() -> None:
    """Generate chromatic-aberration outputs for every available microscope."""

    microscope_dirs = detect_microscopes(CHROMATIC_DATA_DIR)

    print("\n========================================")
    print("Chromatic Aberration Quality Assessment")
    print("========================================")
    print("Detected chromatic-aberration microscopes:")

    if microscope_dirs:
        for microscope_dir in microscope_dirs:
            print(f"  - {microscope_dir.name}")
    else:
        print("  None")

    results = {}

    for microscope_dir in microscope_dirs:
        microscope_output = CHROMATIC_OUTPUT_DIR / microscope_dir.name
        result = run_chromatic_analysis(microscope_dir, microscope_output)

        if result is not None:
            results[microscope_dir.name] = result

    print("\n========================================")
    print("Chromatic-aberration plotting complete.")
    print("========================================")
    print(f"Processed {len(results)} microscope(s).")
    print(f"Output directory: {CHROMATIC_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
