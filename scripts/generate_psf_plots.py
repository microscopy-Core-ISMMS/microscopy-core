"""Generate PSF quality-assessment tables and plots."""

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# Project directories
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]

PSF_DATA_DIR = PROJECT_DIR / "data" / "PSF_Measurements"

PSF_OUTPUT_DIR = PROJECT_DIR / "outputs" / "PSF_Measurements"

MICROMETERS_TO_NANOMETERS = 1_000


# --------------------------------------------------
# Detect microscopes
# --------------------------------------------------


def detect_microscopes(folder: Path) -> list[Path]:
    """
    Detect microscope folders inside the PSF data directory.
    """

    if not folder.exists():
        print(f"Warning: PSF data directory does not exist: " f"{folder}")
        return []

    return sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ],
        key=lambda path: path.name.lower(),
    )


# --------------------------------------------------
# Detect objectives from filenames
# --------------------------------------------------


def detect_objectives(csv_files: list[Path]) -> list[str]:
    """
    Detect objective magnifications from filenames.

    Examples:
        10x
        20xW
        40xO

    Objective names are stored internally in lowercase.
    """

    objectives = set()

    for file_path in csv_files:

        filename = file_path.name.lower()

        match = re.search(
            r"(\d+x[wo]?)",
            filename,
        )

        if match:
            objectives.add(match.group(1))

    return sorted(objectives)


# --------------------------------------------------
# Parse one PSF CSV
# --------------------------------------------------


def parse_psf_csv(file_path: Path) -> pd.DataFrame:
    """
    Parse MaxX, MaxY and MaxZ measurements from
    one PSF CSV file.

    This preserves the logic from the original
    PSF notebook.
    """

    with file_path.open(
        "r",
        encoding="latin1",
    ) as file:

        lines = [line.strip() for line in file]

    # ----------------------------------------------
    # Extract measurement date from filename
    # ----------------------------------------------

    date_match = re.search(
        r"(\d{1,2})-(\d{2})",
        file_path.name,
    )

    if date_match:

        month = int(date_match.group(1))

        year = 2000 + int(date_match.group(2))

        date_obj = datetime(
            year=year,
            month=month,
            day=1,
        )

    else:

        date_obj = None

    # ----------------------------------------------
    # PSF sections
    # ----------------------------------------------

    sections = {
        "X": "maxx",
        "Y": "maxy",
        "Z": "maxz",
    }

    section_data = {}

    # ----------------------------------------------
    # Parse each section
    # ----------------------------------------------

    for axis, section_name in sections.items():

        header_index = next(
            (
                index
                for index, line in enumerate(lines)
                if line.lower().startswith(f"ch,{section_name}")
            ),
            None,
        )

        if header_index is None:

            section_data[axis] = {}
            continue

        values = {}

        for line in lines[header_index + 1 :]:

            # Stop when the next channel section starts
            if line.lower().startswith("ch,"):
                break

            if not line:
                continue

            if line.upper().startswith("FWHM"):
                continue

            parts = line.split(",")

            if len(parts) < 2:
                continue

            try:

                channel = int(parts[0])

                # Avoid duplicate entries
                if channel in values:
                    continue

                raw_value = parts[1].strip()

                if raw_value == "-----":

                    value = np.nan

                else:

                    value = float(raw_value)

                    if value == 0:
                        value = np.nan

                values[channel] = value

            except (
                ValueError,
                TypeError,
            ):

                continue

        section_data[axis] = values

    # ----------------------------------------------
    # Determine all channels
    # ----------------------------------------------

    all_channels = sorted(
        set(
            list(section_data["X"].keys())
            + list(section_data["Y"].keys())
            + list(section_data["Z"].keys())
        )
    )

    # ----------------------------------------------
    # Build records
    # ----------------------------------------------

    records = []

    for channel in all_channels:

        x = section_data["X"].get(
            channel,
            np.nan,
        )

        y = section_data["Y"].get(
            channel,
            np.nan,
        )

        z = section_data["Z"].get(
            channel,
            np.nan,
        )

        if np.isnan(x) and np.isnan(y):

            avg_xy = np.nan

        else:

            avg_xy = np.nanmean([x, y])

        records.append(
            {
                "Date": date_obj,
                # Same channel numbering behavior
                # as the original notebook
                "Channel": (f"CH{channel + 1}"),
                "MaxX": x,
                "MaxY": y,
                "AvgXY": avg_xy,
                "MaxZ": z,
                "SourceFile": (file_path.name),
            }
        )

    return pd.DataFrame(records)


# --------------------------------------------------
# Create XY plot
# --------------------------------------------------


def get_channel_colors(microscope: str) -> dict:
    """
    Return channel colors based on microscope manufacturer.

    Leica:
        CH1 = blue
        CH2 = green
        CH3 = orange
        CH4 = red

    Zeiss:
        CH1 = red
        CH2 = orange
        CH3 = green
        CH4 = blue
    """

    microscope_lower = microscope.lower()

    if "leica" in microscope_lower:

        return {
            "CH1": "blue",
            "CH2": "green",
            "CH3": "orange",
            "CH4": "red",
        }

    if "zeiss" in microscope_lower or "lsm" in microscope_lower:

        return {
            "CH1": "red",
            "CH2": "orange",
            "CH3": "green",
            "CH4": "blue",
        }

    # Default mapping
    return {
        "CH1": "blue",
        "CH2": "green",
        "CH3": "orange",
        "CH4": "red",
    }


def plot_psf_xy(
    dataframe: pd.DataFrame,
    objective: str,
    output_folder: Path,
    microscope: str,
) -> Path | None:
    """
    Create an interactive Plotly lateral PSF plot.
    """

    if dataframe.empty:
        return None

    channel_colors = get_channel_colors(microscope)

    figure = go.Figure()

    plotted = False

    for channel in sorted(dataframe["Channel"].unique()):

        channel_data = dataframe[dataframe["Channel"] == channel].copy()

        channel_data = channel_data[channel_data["AvgXY"].notna()]

        if channel_data.empty:
            continue

        channel_data = channel_data.sort_values("Date")

        xy_nanometers = (
            channel_data["AvgXY"] * MICROMETERS_TO_NANOMETERS
        )

        figure.add_trace(
            go.Scatter(
                x=channel_data["Date"],
                y=xy_nanometers,
                mode="lines+markers",
                name=channel,
                line=dict(
                    color=channel_colors.get(channel),
                    width=2,
                ),
                marker=dict(
                    size=8,
                ),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%b %Y}<br>"
                    "XY: %{y:.0f} nm"
                    "<extra></extra>"
                ),
            )
        )

        plotted = True

    if not plotted:
        return None

    figure.update_layout(
        title=(f"PSF XY - Objective " f"{objective.upper()}"),
        xaxis_title="Date",
        yaxis_title="XY (nm)",
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
    )

    figure.update_yaxes(
        showgrid=True,
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_folder / f"PSF_XY_{objective}.html"

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


# --------------------------------------------------
# Create Z plot
# --------------------------------------------------


def plot_psf_z(
    dataframe: pd.DataFrame,
    objective: str,
    output_folder: Path,
    microscope: str,
) -> Path | None:
    """
    Create an interactive Plotly axial PSF plot.
    """

    if dataframe.empty:
        return None

    channel_colors = get_channel_colors(microscope)

    figure = go.Figure()

    plotted = False

    for channel in sorted(dataframe["Channel"].unique()):

        channel_data = dataframe[dataframe["Channel"] == channel].copy()

        channel_data = channel_data[channel_data["MaxZ"].notna()]

        if channel_data.empty:
            continue

        channel_data = channel_data.sort_values("Date")

        z_nanometers = (
            channel_data["MaxZ"] * MICROMETERS_TO_NANOMETERS
        )

        figure.add_trace(
            go.Scatter(
                x=channel_data["Date"],
                y=z_nanometers,
                mode="lines+markers",
                name=channel,
                line=dict(
                    color=channel_colors.get(channel),
                    width=2,
                ),
                marker=dict(
                    size=8,
                ),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%b %Y}<br>"
                    "Z: %{y:.0f} nm"
                    "<extra></extra>"
                ),
            )
        )

        plotted = True

    if not plotted:
        return None

    figure.update_layout(
        title=(f"PSF Z - Objective " f"{objective.upper()}"),
        xaxis_title="Date",
        yaxis_title="Z (nm)",
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
    )

    figure.update_yaxes(
        showgrid=True,
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_folder / f"PSF_Z_{objective}.html"

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


# --------------------------------------------------
# Run PSF analysis for one microscope
# --------------------------------------------------


def run_psf_analysis(
    microscope_dir: Path,
    output_dir: Path,
):
    """
    Process all PSF CSV files for one microscope.
    """

    microscope = microscope_dir.name

    print("")
    print("----------------------------------------")

    print(f"Processing PSF: " f"{microscope}")

    print("----------------------------------------")

    # ----------------------------------------------
    # Find CSV files
    # ----------------------------------------------

    csv_files = sorted(microscope_dir.glob("*.csv"))

    if not csv_files:

        print(f"No PSF CSV files found " f"for {microscope}.")

        return None

    print(f"Found " f"{len(csv_files)} " f"CSV file(s).")

    # ----------------------------------------------
    # Detect objectives
    # ----------------------------------------------

    objectives = detect_objectives(csv_files)

    print(
        "Objectives:",
        ", ".join(objective.upper() for objective in objectives) or "None",
    )

    if not objectives:

        print("No objectives could be " "identified from filenames.")

        return None

    # ----------------------------------------------
    # Create plot folder
    # ----------------------------------------------

    plot_folder = output_dir / "plots"

    plot_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ----------------------------------------------
    # Remove old plots
    # ----------------------------------------------

    for old_plot in plot_folder.glob("*.html"):

        old_plot.unlink()

    all_records = []

    # ----------------------------------------------
    # Process files by objective
    # ----------------------------------------------

    for objective in objectives:

        objective_files = [
            file_path for file_path in csv_files if objective in file_path.name.lower()
        ]

        print(
            f"Processing objective "
            f"{objective.upper()}: "
            f"{len(objective_files)} file(s)"
        )

        for file_path in objective_files:

            try:

                dataframe = parse_psf_csv(file_path)

                if dataframe.empty:

                    print("No usable data in: " f"{file_path.name}")

                    continue

                dataframe["Objective"] = objective

                all_records.append(dataframe)

            except Exception as exc:

                print("Skipping unreadable file: " f"{file_path.name}")

                print(f"  Error: {exc}")

    # ----------------------------------------------
    # Combine data
    # ----------------------------------------------

    if not all_records:

        print("No readable PSF data found.")

        return None

    combined_df = pd.concat(
        all_records,
        ignore_index=True,
    )

    # Explicitly convert Date column
    # to Pandas datetime
    combined_df["Date"] = pd.to_datetime(
        combined_df["Date"],
        errors="coerce",
    )

    combined_df = combined_df.sort_values(
        [
            "Objective",
            "Date",
            "Channel",
        ]
    ).reset_index(drop=True)

    # ----------------------------------------------
    # Save combined data
    # ----------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined_csv_path = output_dir / "combined_PSF_data.csv"

    combined_df.to_csv(
        combined_csv_path,
        index=False,
    )

    print("Saved combined PSF data:")

    print(f"  {combined_csv_path}")

    # ----------------------------------------------
    # Create plots
    # ----------------------------------------------

    generated_plots = []

    for objective in objectives:

        df_obj = combined_df[combined_df["Objective"] == objective].copy()

        if df_obj.empty:
            continue

        # Remove rows with invalid dates
        df_obj = df_obj[df_obj["Date"].notna()].copy()

        if df_obj.empty:

            print(
                "No valid dated measurements " f"for objective " f"{objective.upper()}."
            )

            continue

        df_obj = df_obj.sort_values("Date")

        df_obj["Date_str"] = df_obj["Date"].dt.strftime("%Y-%m")

        # ------------------------------------------
        # XY plot
        # ------------------------------------------

        xy_plot = plot_psf_xy(
            df_obj,
            objective,
            plot_folder,
            microscope,
        )

        if xy_plot is not None:

            generated_plots.append(xy_plot)

            print(f"Saved: " f"{xy_plot.name}")

        # ------------------------------------------
        # Z plot
        # ------------------------------------------

        z_plot = plot_psf_z(
            df_obj,
            objective,
            plot_folder,
            microscope,
        )

        if z_plot is not None:

            generated_plots.append(z_plot)

            print(f"Saved: " f"{z_plot.name}")

    # ----------------------------------------------
    # Return results
    # ----------------------------------------------

    return {
        "microscope": (microscope),
        "data": (combined_df),
        "plots": (generated_plots),
        "combined_csv": (combined_csv_path),
    }


def main() -> None:
    """Generate plots and combined data for every PSF microscope."""
    psf_microscopes = detect_microscopes(PSF_DATA_DIR)

    print("\n========================================")
    print("PSF Quality Assessment")
    print("========================================")
    print("Detected PSF microscopes:")

    if psf_microscopes:
        for microscope_dir in psf_microscopes:
            print(f"  - {microscope_dir.name}")
    else:
        print("  None")

    psf_results = {}
    for microscope_dir in psf_microscopes:
        microscope_output = PSF_OUTPUT_DIR / microscope_dir.name
        result = run_psf_analysis(microscope_dir, microscope_output)
        if result is not None:
            psf_results[microscope_dir.name] = result

    print("\n========================================")
    print("PSF plotting complete.")
    print("========================================")
    print(f"Processed {len(psf_results)} microscope(s).")
    print(f"PSF output directory: {PSF_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
