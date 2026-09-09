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

LASER_DATA_DIR = PROJECT_DIR / "data" / "Laser_Power_Measurements"

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
# Read reference month
# --------------------------------------------------


def get_target_month(microscope: str) -> str | None:
    """Read the laser-power reference month for a microscope."""

    target_file = LASER_DATA_DIR / microscope / "target_month.txt"

    if not target_file.exists():
        return None

    target_month = target_file.read_text(encoding="utf-8").strip()

    if not target_month:
        return None

    try:
        pd.Period(target_month, freq="M")
    except ValueError as exc:
        raise ValueError(
            f"{target_file} must contain a month in YYYY-MM format. "
            f"Found: {target_month}"
        ) from exc

    return target_month


# --------------------------------------------------
# Parse one PSF CSV
# --------------------------------------------------


def parse_psf_csv(file_path: Path) -> pd.DataFrame:
    """
    Parse FWHMX, FWHMY and FWHMZ measurements from
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
        "X": ("maxx", "fwhmx"),
        "Y": ("maxy", "fwhmy"),
        "Z": ("maxz", "fwhmz"),
    }

    section_data = {}

    theoretical_data = {}

    # ----------------------------------------------
    # Parse each section
    # ----------------------------------------------

    for axis, (section_name, value_column) in sections.items():

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
            theoretical_data[axis] = {}
            continue

        header_columns = [
            column.strip().lower() for column in lines[header_index].split(",")
        ]

        value_index = next(
            (
                index
                for index, column in enumerate(header_columns)
                if column.startswith(value_column)
            ),
            None,
        )

        if value_index is None:

            section_data[axis] = {}
            theoretical_data[axis] = {}
            continue

        values = {}

        theoretical_values = {}

        for line in lines[header_index + 1 :]:

            # Stop when the next channel section starts
            if line.lower().startswith("ch,"):
                break

            if not line:
                continue

            if line.upper().startswith("FWHM"):
                continue

            parts = line.split(",")

            if len(parts) <= value_index:
                continue

            try:

                channel = int(parts[0])

                is_theoretical = any("theoretical" in part.lower() for part in parts)

                target_values = theoretical_values if is_theoretical else values

                # Avoid duplicate entries
                if channel in target_values:
                    continue

                raw_value = parts[value_index].strip()

                if raw_value == "-----":

                    value = np.nan

                else:

                    value = float(raw_value)

                    if value == 0:
                        value = np.nan

                target_values[channel] = value

            except (
                ValueError,
                TypeError,
            ):

                continue

        section_data[axis] = values
        theoretical_data[axis] = theoretical_values

    # ----------------------------------------------
    # Determine all channels
    # ----------------------------------------------

    all_channels = sorted(
        set(
            list(section_data["X"].keys())
            + list(section_data["Y"].keys())
            + list(section_data["Z"].keys())
            + list(theoretical_data["X"].keys())
            + list(theoretical_data["Y"].keys())
            + list(theoretical_data["Z"].keys())
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

        theoretical_x = theoretical_data["X"].get(
            channel,
            np.nan,
        )

        theoretical_y = theoretical_data["Y"].get(
            channel,
            np.nan,
        )

        theoretical_z = theoretical_data["Z"].get(
            channel,
            np.nan,
        )

        if np.isnan(x) and np.isnan(y):

            avg_xy = np.nan

        else:

            avg_xy = np.nanmean([x, y])

        if np.isnan(theoretical_x) and np.isnan(theoretical_y):

            avg_theoretical_xy = np.nan

        else:

            avg_theoretical_xy = np.nanmean([theoretical_x, theoretical_y])

        records.append(
            {
                "Date": date_obj,
                # Same channel numbering behavior
                # as the original notebook
                "Channel": (f"CH{channel + 1}"),
                "FWHMX": x,
                "FWHMY": y,
                "AvgFWHMXY": avg_xy,
                "FWHMZ": z,
                "TheoreticalFWHMX": theoretical_x,
                "TheoreticalFWHMY": theoretical_y,
                "AvgTheoreticalFWHMXY": avg_theoretical_xy,
                "TheoreticalFWHMZ": theoretical_z,
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


def get_theoretical_reference(
    channel_data: pd.DataFrame,
    value_column: str,
    target_month: str | None,
) -> tuple[float, str] | None:
    """
    Select a theoretical FWHM reference for one channel.

    Only use the theoretical value from the configured target month. Returning
    no reference is safer than silently substituting a different month's value.
    """

    if target_month is None:
        return None

    reference_data = channel_data.loc[
        channel_data["Date"].notna() & channel_data[value_column].notna()
    ].copy()

    if reference_data.empty:
        return None

    reference_data["ReferenceMonth"] = reference_data["Date"].dt.strftime("%Y-%m")
    reference_rows = reference_data.loc[
        reference_data["ReferenceMonth"] == target_month
    ]

    if reference_rows.empty:
        return None

    reference_value = float(reference_rows.iloc[-1][value_column])

    return reference_value, target_month


def get_reference_line_dates(
    dataframe: pd.DataFrame,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return padded axis endpoints so references span the full plot width."""

    dates = dataframe["Date"].dropna()
    padding = pd.Timedelta(days=15)
    start_date = dates.min() - padding
    end_date = dates.max() + padding

    return start_date, end_date


def plot_psf_xy(
    dataframe: pd.DataFrame,
    objective: str,
    output_folder: Path,
    microscope: str,
    target_month: str | None,
) -> Path | None:
    """
    Create an interactive Plotly lateral PSF plot.
    """

    if dataframe.empty:
        return None

    channel_colors = get_channel_colors(microscope)

    figure = go.Figure()

    plotted = False

    reference_start, reference_end = get_reference_line_dates(dataframe)

    for channel in sorted(dataframe["Channel"].unique()):

        channel_data = dataframe[dataframe["Channel"] == channel].copy()

        channel_data = channel_data.sort_values("Date")

        measured_data = channel_data[channel_data["AvgFWHMXY"].notna()]

        if not measured_data.empty:

            xy_nanometers = measured_data["AvgFWHMXY"] * MICROMETERS_TO_NANOMETERS

            figure.add_trace(
                go.Scatter(
                    x=measured_data["Date"],
                    y=xy_nanometers,
                    mode="lines+markers",
                    name=channel,
                    legendgroup=channel,
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
                        "Measured XY: %{y:.0f} nm"
                        "<extra></extra>"
                    ),
                )
            )

            plotted = True

        theoretical_reference = get_theoretical_reference(
            channel_data,
            "AvgTheoreticalFWHMXY",
            target_month,
        )

        if theoretical_reference is not None:

            theoretical_value, reference_month = theoretical_reference

            theoretical_xy_nanometers = theoretical_value * MICROMETERS_TO_NANOMETERS

            figure.add_trace(
                go.Scatter(
                    x=[reference_start, reference_end],
                    y=[theoretical_xy_nanometers, theoretical_xy_nanometers],
                    mode="lines",
                    name=f"{channel} theoretical ({reference_month})",
                    legendgroup=channel,
                    line=dict(
                        color=channel_colors.get(channel),
                        width=2,
                        dash="dash",
                    ),
                    opacity=0.75,
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "Theoretical XY: %{y:.0f} nm"
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
        range=[reference_start, reference_end],
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
    target_month: str | None,
) -> Path | None:
    """
    Create an interactive Plotly axial PSF plot.
    """

    if dataframe.empty:
        return None

    channel_colors = get_channel_colors(microscope)

    figure = go.Figure()

    plotted = False

    reference_start, reference_end = get_reference_line_dates(dataframe)

    for channel in sorted(dataframe["Channel"].unique()):

        channel_data = dataframe[dataframe["Channel"] == channel].copy()

        channel_data = channel_data.sort_values("Date")

        measured_data = channel_data[channel_data["FWHMZ"].notna()]

        if not measured_data.empty:

            z_nanometers = measured_data["FWHMZ"] * MICROMETERS_TO_NANOMETERS

            figure.add_trace(
                go.Scatter(
                    x=measured_data["Date"],
                    y=z_nanometers,
                    mode="lines+markers",
                    name=channel,
                    legendgroup=channel,
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
                        "Measured Z: %{y:.0f} nm"
                        "<extra></extra>"
                    ),
                )
            )

            plotted = True

        theoretical_reference = get_theoretical_reference(
            channel_data,
            "TheoreticalFWHMZ",
            target_month,
        )

        if theoretical_reference is not None:

            theoretical_value, reference_month = theoretical_reference

            theoretical_z_nanometers = theoretical_value * MICROMETERS_TO_NANOMETERS

            figure.add_trace(
                go.Scatter(
                    x=[reference_start, reference_end],
                    y=[theoretical_z_nanometers, theoretical_z_nanometers],
                    mode="lines",
                    name=f"{channel} theoretical ({reference_month})",
                    legendgroup=channel,
                    line=dict(
                        color=channel_colors.get(channel),
                        width=2,
                        dash="dash",
                    ),
                    opacity=0.75,
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "Theoretical Z: %{y:.0f} nm"
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
        range=[reference_start, reference_end],
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

    target_month = get_target_month(microscope)

    print(
        "Theoretical reference month:",
        target_month or "not configured; theoretical lines will be omitted",
    )

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

        if target_month is not None:
            target_rows = df_obj[df_obj["Date_str"] == target_month]

            if target_rows.empty:
                print(
                    f"No {target_month} PSF report for objective "
                    f"{objective.upper()}; theoretical lines omitted."
                )
            elif (
                not target_rows[["AvgTheoreticalFWHMXY", "TheoreticalFWHMZ"]]
                .notna()
                .any()
                .any()
            ):
                print(
                    f"The {target_month} PSF report for objective "
                    f"{objective.upper()} has no theoretical values; "
                    "theoretical lines omitted."
                )

        # ------------------------------------------
        # XY plot
        # ------------------------------------------

        xy_plot = plot_psf_xy(
            df_obj,
            objective,
            plot_folder,
            microscope,
            target_month,
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
            target_month,
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
