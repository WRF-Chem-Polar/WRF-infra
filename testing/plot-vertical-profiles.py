# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Plot vertical profiles at specific locations for WRF run(s)."""

import argparse
from itertools import product
from collections import namedtuple
import datetime
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from wrfinfra import generic
import wrfpp

# Types and functions

Location = namedtuple("Location", "name lon lat")


def parse_location(location):
    """Parse location (typically obtained from command-line arguments).

    Parameters
    ----------
    location: str
        Location specified as "name:longitude:latitude".

    Returns
    -------
    Location
        The given location parsed as a named tuple.

    """
    split = location.split(":")
    return Location(split[0].strip(), float(split[1]), float(split[2]))


def new_page():
    """Create a new A4 page in current document.

    Returns
    -------
    matplotlib.Figure
        Handle to the figure object that represents the new page.

    """
    cm2in = 0.393701
    return plt.figure(figsize=(21 * cm2in, 29.7 * cm2in))


def add_title_page(pdf, runs):
    """Add title page to current document.

    Parameters
    ----------
    pdf: handle to PDF backend.
        The handle to the PDF backend.
    runs: [dict]
        The information about the runs.

    """
    ax = new_page().add_axes([0, 0, 1, 1])
    ax.text(0.5, 0.8, "Vertical profiles", ha="center", va="center")
    y = 0.6
    for i, run in enumerate(runs):
        ax.text(0.1, y, f"Run {i + 1}: {run['ds'].encoding['source']}")
        y -= 0.1
    plt.axis("off")
    pdf.savefig()
    plt.close()


# Command-line arguments

parser = argparse.ArgumentParser(
    description="Plot vertical profiles at specific locations for WRF run(s).",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--variables",
    help="Comma-separated list of variables to plot",
    default="o3,air_temperature",
)
parser.add_argument(
    "--locations",
    help=(
        "Comma-separated list of locations to plot. A location is a "
        "triplet of name:lon:lat."
    ),
    default="North Pole:0:90",
)
parser.add_argument(
    "--start",
    help=(
        "Start date (YYYY-mm-dd) of the averaging period. "
        "If None, then use the entire simulation."
    ),
    default=None,
)
parser.add_argument(
    "--end",
    help=(
        "End date (YYYY-mm-dd) of the averaging period. "
        "If None, then use the entire simulation."
    ),
    default=None,
)
parser.add_argument(
    "--wrfouts",
    help=(
        "Comma-separated list of paths to the wrfout files. "
        "There must be one single file per simulation. Use ncrcat to first "
        "concatenate multiple files from a single simulation is nedded."
    ),
)
parser.add_argument(
    "--output",
    help="Path to output file. It must have the .pdf extension.",
    default="vertical-profiles.pdf",
)
args = parser.parse_args()

# Pre-process command-line arguments and run quality controls

variables = [var.strip() for var in args.variables.split(",")]
locations = [parse_location(loc) for loc in args.locations.split(",")]
if args.start is not None:
    args.start = datetime.datetime.strptime(args.start, "%Y-%m-%d")
if args.end is not None:
    args.end = datetime.datetime.strptime(args.end, "%Y-%m-%d")
if not args.output.endswith(".pdf"):
    msg = "Parameter --output must have the .pdf extension."
    raise ValueError(msg)

# Hard-coded graphical parameters

colors = ("r", "b", "k", "y", "m")
linestyles = ("-", "--", ":")
markers = ("o", "^", "v", "*", "+", "s")

# Other hard-coded parameters

variable_z_axis = "altitude_agl_c"

# Open and prepare datasets

runs = []
for i_run, path in enumerate(args.wrfouts.split(",")):
    run = {"ds": xr.open_dataset(generic.process_path(path.strip())).wrf}
    times = list(run["ds"]["XTIME"].values)
    dt = run["ds"].dt

    # Process start date
    if args.start is not None:
        run["start"] = args.start
    elif i_run == 0:
        run["start"] = times[0]
    elif times[0] != runs[0]["start"]:
        msg = "Inconsistent start dates across runs."
        raise RuntimeError(msg)
    else:
        run["start"] = runs[0]["start"]

    # Process end date
    if args.end is not None:
        run["end"] = args.end
    elif i_run == 0:
        run["end"] = times[-1] + dt
    elif times[-1] + dt != runs[0]["end"]:
        msg = "Inconsistent end dates across runs."
        raise RuntimeError(msg)
    else:
        run["end"] = runs[0]["end"]

    # Get time indices for period of interest
    run["time_idx"] = range(
        times.index(run["start"]), times.index(run["end"] - dt) + 1
    )

    runs.append(run)

# Create the PDF with the plots

with PdfPages(args.output) as pdf:
    add_title_page(pdf, runs)

    for variable, location in product(variables, locations):
        print(f"Plotting {variable} at {location.name}...")

        lon, lat = location.lon, location.lat
        fig = new_page()
        ax = fig.add_axes([0.2, 0.2, 0.7, 0.6])

        for i_run, run in enumerate(runs):
            print(f"    Processing run {i_run + 1}...")

            # Prepare dataset and arrays
            ds = run["ds"].value_around_point(lon, lat).wrf
            array_x = getattr(ds, variable)
            array_y = getattr(ds, variable_z_axis)

            # Plot the profiles
            x = array_x.isel(Time=run["time_idx"]).mean(axis=0)
            y = array_y.isel(Time=run["time_idx"]).mean(axis=0)
            ax.plot(
                x,
                y,
                markers[i_run % len(markers)]
                + linestyles[i_run % len(linestyles)],
                color=colors[i_run % len(colors)],
                markersize=3,
                label=f"Run {i_run + 1}",
            )

            # Format the plot
            ax.set_ylim(y.min(), y.max())
            ax.legend()
            ax.set_xlabel(f"{variable} ({ds.units_mpl(variable)})")
            ax.set_ylabel(f"{array_y.name} ({ds.units_mpl(variable_z_axis)})")
            lon_formatted = f"{abs(lon)}{'E' if lon > 0 else 'W'}"
            lat_formatted = f"{abs(lat)}{'N' if lat > 0 else 'S'}"
            loclonlat = f"{location.name} ({lon_formatted}, {lat_formatted})"
            ax.set_title(f"Vertical profile of {variable} at {loclonlat}")

        # Finalize the page
        pdf.savefig()
        plt.close()

# Close connections to wrfout files

for run in runs:
    run["ds"].close()
